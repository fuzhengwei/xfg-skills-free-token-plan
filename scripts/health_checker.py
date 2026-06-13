#!/usr/bin/env python3
"""
health_checker.py — 渠道验证 + 自动降级/恢复
=============================================
用户手动触发（检查渠道/测试渠道/验证渠道），检测所有渠道状态：
- 所有渠道默认优先级 10（统一负载均衡）
- 不可用渠道 → 降级为优先级 1（降级，不删除）
- 下次验证可用后 → 恢复优先级 10
- 手动禁用(状态2)的渠道 → 跳过，不修改

检查历史文件: data/health_history.json
"""

import argparse
import json
import sys
import os
import time
from datetime import datetime, timezone, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
HISTORY_PATH = os.path.join(DATA_DIR, "health_history.json")
sys.path.insert(0, SCRIPT_DIR)

from oneapi_client import (
    list_channels, test_channel, update_channel, get_channel,
    list_tokens, get_subscription, load_config
)


# ── 状态常量 ──────────────────────────────────────────────
CHANNEL_STATUS = {0: "未知", 1: "启用", 2: "手动禁用", 3: "自动禁用"}
TOKEN_STATUS = {1: "已启用", 2: "已禁用", 3: "已过期", 4: "已耗尽"}

# ── 优先级常量 ────────────────────────────────────────────
PRIORITY_NORMAL = 10    # 正常优先级（统一负载均衡）
PRIORITY_DEGRADED = 1   # 降级优先级（不可用渠道）


def _now_iso():
    """当前时间 ISO 格式（东八区）"""
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat()


def _load_history():
    """加载检查历史"""
    if not os.path.exists(HISTORY_PATH):
        return {"channels": {}, "last_full_check": None, "check_count": 0}
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"channels": {}, "last_full_check": None, "check_count": 0}


def _save_history(history):
    """保存检查历史"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def _get_channel_history(history, channel_id):
    """获取渠道历史记录"""
    ch_key = str(channel_id)
    if ch_key not in history["channels"]:
        history["channels"][ch_key] = {
            "consecutive_failures": 0,
            "degraded_at": None,
            "last_check": None,
            "last_healthy": None
        }
    return history["channels"][ch_key]


def check_channel_health(channel_id, model=None):
    """
    检测单个渠道健康状态

    Args:
        channel_id: 渠道 ID
        model: 测试使用的模型（可选）

    Returns:
        dict: 健康检查结果
    """
    ch_result = get_channel(channel_id)
    if not ch_result.get("success"):
        return {"success": False, "channel_id": channel_id, "message": "渠道不存在"}

    channel = ch_result.get("data", {})
    test_result = test_channel(channel_id, model)

    healthy = test_result.get("success", False)
    response_time = test_result.get("time", 0)

    return {
        "success": True,
        "channel_id": channel_id,
        "channel_name": channel.get("name", ""),
        "channel_type": channel.get("type", 0),
        "status": channel.get("status", 0),
        "status_text": CHANNEL_STATUS.get(channel.get("status", 0), "未知"),
        "healthy": healthy,
        "response_time": round(response_time, 3),
        "message": test_result.get("message", ""),
        "model_tested": test_result.get("modelName", ""),
        "priority": channel.get("priority", 0),
        "models": channel.get("models", ""),
        "group": channel.get("group", "default")
    }


def check_all_channels(auto_fix=True):
    """
    验证所有渠道 + 自动降级/恢复

    逻辑:
    - 所有渠道默认优先级 10（统一负载均衡）
    - 不可用渠道 → 降级为优先级 1（仍保留，低优先级）
    - 下次验证可用后 → 恢复优先级 10
    - 手动禁用(状态2)的渠道 → 跳过，不修改

    Args:
        auto_fix: 是否自动修复（降级/恢复优先级）

    Returns:
        dict: 验证报告
    """
    channels_result = list_channels(page=0, page_size=100)
    if not channels_result.get("success"):
        return channels_result

    channels = channels_result.get("data", []) or []
    history = _load_history()

    # ── 测试所有渠道 ─────────────────────────────────────
    health_results = []
    healthy_channels = []
    unhealthy_channels = []
    degraded_count = 0
    recovered_count = 0
    skipped_manual = 0

    for ch in channels:
        ch_id = ch.get("id")
        if not ch_id:
            continue

        # 手动禁用的渠道跳过
        if ch.get("status") == 2:
            skipped_manual += 1
            ch_history = _get_channel_history(history, ch_id)
            ch_history["last_check"] = _now_iso()
            health_results.append({
                "channel_id": ch_id,
                "channel_name": ch.get("name", ""),
                "healthy": None,
                "action": "skipped (手动禁用)",
                "status": 2,
                "status_text": "手动禁用",
                "priority": ch.get("priority", 0)
            })
            continue

        health = check_channel_health(ch_id)
        ch_history = _get_channel_history(history, ch_id)
        ch_history["last_check"] = _now_iso()

        if health.get("healthy"):
            ch_history["consecutive_failures"] = 0
            ch_history["last_healthy"] = True
            healthy_channels.append((ch, health))
        else:
            ch_history["consecutive_failures"] = ch_history.get("consecutive_failures", 0) + 1
            ch_history["last_healthy"] = False
            unhealthy_channels.append((ch, health))

        health_results.append(health)

    # ── 自动修复：降级/恢复 ──────────────────────────────
    actions = []

    if auto_fix:
        # 不可用渠道 → 降级为优先级 1
        for ch, health in unhealthy_channels:
            current_priority = ch.get("priority", 0)
            if current_priority != PRIORITY_DEGRADED:
                update_data = {
                    "id": ch.get("id"),
                    "priority": PRIORITY_DEGRADED
                }
                update_channel(update_data)
                ch_history = _get_channel_history(history, ch.get("id"))
                ch_history["degraded_at"] = _now_iso()
                degraded_count += 1
                health["old_priority"] = current_priority
                health["new_priority"] = PRIORITY_DEGRADED
                health["action"] = "degraded"
                actions.append(f"🔻 {ch.get('name', '')}: 优先级 {current_priority} → {PRIORITY_DEGRADED}（降级）")
            else:
                health["action"] = "already_degraded"

        # 可用渠道 → 恢复优先级 10
        for ch, health in healthy_channels:
            current_priority = ch.get("priority", 0)
            ch_history = _get_channel_history(history, ch.get("id"))

            # 之前被降级的渠道，现在恢复了
            was_degraded = ch_history.get("degraded_at") or current_priority != PRIORITY_NORMAL

            if current_priority != PRIORITY_NORMAL:
                update_data = {
                    "id": ch.get("id"),
                    "status": 1,  # 确保启用
                    "priority": PRIORITY_NORMAL
                }
                update_channel(update_data)
                ch_history["degraded_at"] = None
                recovered_count += 1
                health["old_priority"] = current_priority
                health["new_priority"] = PRIORITY_NORMAL
                health["action"] = "recovered"
                health["recovered"] = True
                actions.append(f"🔺 {ch.get('name', '')}: 优先级 {current_priority} → {PRIORITY_NORMAL}（恢复）")
            else:
                health["action"] = "healthy"
                ch_history["degraded_at"] = None

    # ── 更新历史 ─────────────────────────────────────────
    history["last_full_check"] = _now_iso()
    history["check_count"] = history.get("check_count", 0) + 1
    _save_history(history)

    # ── 构建报告 ─────────────────────────────────────────
    parts = [f"✅ {len(healthy_channels)} 正常（优先级{PRIORITY_NORMAL}）", f"❌ {len(unhealthy_channels)} 不可用"]
    if degraded_count > 0:
        parts.append(f"🔻 {degraded_count} 已降级（优先级→{PRIORITY_DEGRADED}）")
    if recovered_count > 0:
        parts.append(f"🔺 {recovered_count} 已恢复（优先级→{PRIORITY_NORMAL}）")
    if skipped_manual > 0:
        parts.append(f"⏭ {skipped_manual} 手动禁用(跳过)")

    return {
        "success": True,
        "data": {
            "total": len(health_results),
            "healthy": len(healthy_channels),
            "unhealthy": len(unhealthy_channels),
            "degraded": degraded_count,
            "recovered": recovered_count,
            "priority_normal": PRIORITY_NORMAL,
            "priority_degraded": PRIORITY_DEGRADED,
            "actions": actions,
            "channels": health_results
        },
        "message": "渠道验证完成: " + ", ".join(parts) +
                   ("\n\n" + "\n".join(actions) if actions else "")
    }


def check_token_status(token_id=None):
    """检测令牌状态"""
    if token_id:
        from oneapi_client import get_token as get_one_token
        result = get_one_token(token_id)
        if result.get("success"):
            token = result.get("data", {})
            token["status_text"] = TOKEN_STATUS.get(token.get("status", 0), "未知")
        return result

    tokens_result = list_tokens(page=0, page_size=100)
    if not tokens_result.get("success"):
        return tokens_result

    tokens = tokens_result.get("data", []) or []
    now = int(time.time())

    report = []
    for t in tokens:
        status = t.get("status", 0)
        exp = t.get("expired_time", -1)
        unlimited = t.get("unlimited_quota", False)
        remain = t.get("remain_quota", 0)

        issues = []
        if status == 2:
            issues.append("已禁用")
        elif status == 3:
            issues.append("已过期")
        elif status == 4:
            issues.append("已耗尽")
        elif exp != -1 and exp < now:
            issues.append("已过期（时间）")
        elif not unlimited and remain <= 0:
            issues.append("额度已耗尽")

        t["status_text"] = TOKEN_STATUS.get(status, "未知")
        t["issues"] = issues
        t["is_valid"] = len(issues) == 0
        report.append(t)

    valid_count = sum(1 for t in report if t["is_valid"])
    invalid_count = len(report) - valid_count

    return {
        "success": True,
        "data": {
            "total": len(report),
            "valid": valid_count,
            "invalid": invalid_count,
            "tokens": report
        },
        "message": f"令牌检查完成: {valid_count} 有效, {invalid_count} 无效"
    }


def check_quota():
    """检查用户额度"""
    return get_subscription()


def get_channel_stats():
    """获取渠道统计摘要"""
    channels_result = list_channels(page=0, page_size=100)
    if not channels_result.get("success"):
        return channels_result

    channels = channels_result.get("data", []) or []

    by_status = {1: 0, 2: 0, 3: 0}
    by_priority = {}
    total_used_quota = 0

    for ch in channels:
        status = ch.get("status", 0)
        if status in by_status:
            by_status[status] += 1

        priority = ch.get("priority", 0)
        by_priority[priority] = by_priority.get(priority, 0) + 1

        total_used_quota += ch.get("used_quota", 0)

    return {
        "success": True,
        "data": {
            "total": len(channels),
            "enabled": by_status.get(1, 0),
            "manually_disabled": by_status.get(2, 0),
            "auto_disabled": by_status.get(3, 0),
            "by_priority": by_priority,
            "total_used_quota": total_used_quota
        }
    }


def get_health_history():
    """获取检查历史摘要"""
    history = _load_history()
    channels = history.get("channels", {})

    degraded_channels = []
    for ch_id, ch_data in channels.items():
        if ch_data.get("degraded_at"):
            degraded_channels.append({
                "channel_id": int(ch_id),
                "degraded_at": ch_data.get("degraded_at"),
                "consecutive_failures": ch_data.get("consecutive_failures", 0)
            })

    return {
        "success": True,
        "data": {
            "last_full_check": history.get("last_full_check"),
            "total_checks": history.get("check_count", 0),
            "degraded_channels": degraded_channels
        },
        "message": f"历史: {history.get('check_count', 0)} 次检查, "
                   f"{len(degraded_channels)} 个渠道待恢复"
    }


def clear_history():
    """清除检查历史"""
    if os.path.exists(HISTORY_PATH):
        os.remove(HISTORY_PATH)
    return {"success": True, "message": "检查历史已清除"}


# ── CLI 入口 ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="渠道验证 + 自动降级/恢复")
    sub = parser.add_subparsers(dest="command")

    # check-channel
    p_cc = sub.add_parser("check-channel", help="检测单个渠道")
    p_cc.add_argument("--id", type=int, required=True)
    p_cc.add_argument("--model", default=None)

    # check-all
    p_ca = sub.add_parser("check-all", help="验证所有渠道 + 自动降级/恢复")
    p_ca.add_argument("--no-auto-fix", action="store_true", help="仅报告，不自动降级/恢复")

    # check-tokens
    p_ct = sub.add_parser("check-tokens", help="检测令牌状态")
    p_ct.add_argument("--id", type=int, default=None)

    # check-quota
    sub.add_parser("check-quota", help="检查额度")

    # stats
    sub.add_parser("stats", help="渠道统计")

    # history
    sub.add_parser("history", help="查看检查历史")

    # clear-history
    sub.add_parser("clear-history", help="清除检查历史")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    result = {}
    if args.command == "check-channel":
        result = check_channel_health(args.id, args.model)
    elif args.command == "check-all":
        result = check_all_channels(auto_fix=not args.no_auto_fix)
    elif args.command == "check-tokens":
        result = check_token_status(args.id)
    elif args.command == "check-quota":
        result = check_quota()
    elif args.command == "stats":
        result = get_channel_stats()
    elif args.command == "history":
        result = get_health_history()
    elif args.command == "clear-history":
        result = clear_history()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
