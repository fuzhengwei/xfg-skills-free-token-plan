#!/usr/bin/env python3
"""
health_checker.py — 渠道健康检查 + 自动优先级排序
==================================================
用户手动触发，检测所有渠道状态，自动排优先级：
- 健康渠道：按响应速度分档，快的优先级高，同档同优先级（负载均衡）
- 异常渠道：自动禁用
- 之前被自动禁用的渠道恢复后：重新参与优先级排序

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

# ── 优先级分档阈值（秒）──────────────────────────────────
# 响应时间 <= 2s  → 优先级 10（极速）
# 响应时间 <= 5s  → 优先级 5 （快速）
# 响应时间 <= 10s → 优先级 1 （正常）
# 响应时间 > 10s  → 优先级 0 （慢速）
PRIORITY_TIERS = [
    (2, 10),    # 极速
    (5, 5),     # 快速
    (10, 1),    # 正常
]

DEFAULT_FAILURE_THRESHOLD = 2  # 连续失败 N 次才禁用


def _now_iso():
    """当前时间 ISO 格式（东八区）"""
    tz = timezone(timedelta(hours=8))
    return datetime.now(tz).isoformat()


def _calc_priority(response_time):
    """
    根据响应时间计算优先级
    
    同档位内的渠道优先级相同 → One API 自动负载均衡
    
    Args:
        response_time: 响应时间（秒）
    
    Returns:
        int: 优先级
    """
    for threshold, priority in PRIORITY_TIERS:
        if response_time <= threshold:
            return priority
    return 0  # 慢速


def _tier_label(priority):
    """优先级对应的档位标签"""
    labels = {10: "极速", 5: "快速", 1: "正常", 0: "慢速"}
    return labels.get(priority, f"P{priority}")


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
            "original_priority": None,
            "consecutive_failures": 0,
            "disabled_at": None,
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


def check_all_channels(auto_fix=True, failure_threshold=DEFAULT_FAILURE_THRESHOLD):
    """
    检测所有渠道 + 自动排优先级

    流程:
    1. 测试所有渠道
    2. 健康渠道：按响应速度自动排优先级（同档同优先级 → 负载均衡）
    3. 异常渠道：连续失败达阈值 → 自动禁用
    4. 之前自动禁用的渠道恢复后：重新参与优先级排序
    5. 手动禁用(状态2)的渠道：跳过，不动

    Args:
        auto_fix: 是否自动修复（排优先级 + 禁用异常渠道）
        failure_threshold: 连续失败多少次才自动禁用

    Returns:
        dict: 健康报告
    """
    channels_result = list_channels(page=0, page_size=100)
    if not channels_result.get("success"):
        return channels_result

    channels = channels_result.get("data", []) or []
    history = _load_history()

    # ── 第一轮：测试所有渠道 ─────────────────────────────
    health_results = []
    healthy_channels = []  # (channel_info, health_result)
    unhealthy_count = 0
    recovered_count = 0
    auto_disabled_count = 0
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
                "status_text": "手动禁用"
            })
            continue

        health = check_channel_health(ch_id)
        ch_history = _get_channel_history(history, ch_id)
        ch_history["last_check"] = _now_iso()

        if health.get("healthy"):
            ch_history["consecutive_failures"] = 0
            ch_history["last_healthy"] = True

            # 之前被自动禁用 → 标记恢复
            if ch.get("status") == 3 and ch_history.get("disabled_at"):
                recovered_count += 1
                ch_history["disabled_at"] = None
                health["recovered"] = True

            healthy_channels.append((ch, health))
        else:
            unhealthy_count += 1
            ch_history["consecutive_failures"] = ch_history.get("consecutive_failures", 0) + 1
            ch_history["last_healthy"] = False

            if auto_fix and ch.get("status") == 1:
                failures = ch_history["consecutive_failures"]
                if failures >= failure_threshold:
                    ch_history["original_priority"] = ch.get("priority", 0)
                    _disable_channel(ch)
                    ch_history["disabled_at"] = _now_iso()
                    auto_disabled_count += 1
                    health["action"] = f"auto_disabled (连续失败{failures}次)"
                else:
                    health["action"] = f"failure_recorded ({failures}/{failure_threshold})"

        health_results.append(health)

    # ── 第二轮：健康渠道自动排优先级 ──────────────────────
    priority_updates = []
    if auto_fix and healthy_channels:
        for ch, health in healthy_channels:
            response_time = health.get("response_time", 999)
            new_priority = _calc_priority(response_time)
            old_priority = ch.get("priority", 0)

            # 需要更新：恢复的渠道 或 优先级变化的渠道
            need_update = health.get("recovered", False) or old_priority != new_priority

            if need_update:
                update_data = {
                    "id": ch.get("id"),
                    "status": 1,  # 确保启用
                    "priority": new_priority
                }
                update_channel(update_data)
                health["old_priority"] = old_priority
                health["new_priority"] = new_priority
                health["priority_tier"] = _tier_label(new_priority)
                health["action"] = "recovered + priority_set" if health.get("recovered") else "priority_adjusted"
                priority_updates.append(health)
            else:
                health["priority_tier"] = _tier_label(new_priority)

    # ── 更新历史 ─────────────────────────────────────────
    history["last_full_check"] = _now_iso()
    history["check_count"] = history.get("check_count", 0) + 1
    _save_history(history)

    # ── 构建报告 ─────────────────────────────────────────
    # 按优先级分组展示
    priority_groups = {}
    for ch, health in healthy_channels:
        p = health.get("new_priority", health.get("priority", 0))
        tier = health.get("priority_tier", _tier_label(p))
        if tier not in priority_groups:
            priority_groups[tier] = []
        priority_groups[tier].append({
            "id": ch.get("id"),
            "name": ch.get("name", ""),
            "response_time": health.get("response_time", 0),
            "priority": p
        })

    parts = [f"{len(healthy_channels)} 正常", f"{unhealthy_count} 异常"]
    if auto_disabled_count > 0:
        parts.append(f"{auto_disabled_count} 已自动禁用")
    if recovered_count > 0:
        parts.append(f"{recovered_count} 已自动恢复")
    if skipped_manual > 0:
        parts.append(f"{skipped_manual} 手动禁用(跳过)")

    return {
        "success": True,
        "data": {
            "total": len(health_results),
            "healthy": len(healthy_channels),
            "unhealthy": unhealthy_count,
            "auto_disabled": auto_disabled_count,
            "recovered": recovered_count,
            "failure_threshold": failure_threshold,
            "priority_groups": priority_groups,
            "priority_updates": priority_updates,
            "channels": health_results
        },
        "message": f"渠道检测完成: " + ", ".join(parts) +
                   (f"\n优先级已自动排序，同档位渠道负载均衡" if priority_updates else "")
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
    by_type = {}
    total_used_quota = 0

    for ch in channels:
        status = ch.get("status", 0)
        if status in by_status:
            by_status[status] += 1

        ch_type = ch.get("type", 0)
        by_type[ch_type] = by_type.get(ch_type, 0) + 1

        total_used_quota += ch.get("used_quota", 0)

    return {
        "success": True,
        "data": {
            "total": len(channels),
            "enabled": by_status.get(1, 0),
            "manually_disabled": by_status.get(2, 0),
            "auto_disabled": by_status.get(3, 0),
            "by_type": by_type,
            "total_used_quota": total_used_quota
        }
    }


def get_health_history():
    """获取检查历史摘要"""
    history = _load_history()
    channels = history.get("channels", {})

    auto_disabled = []
    for ch_id, ch_data in channels.items():
        if ch_data.get("disabled_at"):
            auto_disabled.append({
                "channel_id": int(ch_id),
                "original_priority": ch_data.get("original_priority", 0),
                "disabled_at": ch_data.get("disabled_at"),
                "consecutive_failures": ch_data.get("consecutive_failures", 0)
            })

    return {
        "success": True,
        "data": {
            "last_full_check": history.get("last_full_check"),
            "total_checks": history.get("check_count", 0),
            "auto_disabled_channels": auto_disabled
        },
        "message": f"历史: {history.get('check_count', 0)} 次检查, "
                   f"{len(auto_disabled)} 个渠道待恢复"
    }


def clear_history():
    """清除检查历史"""
    if os.path.exists(HISTORY_PATH):
        os.remove(HISTORY_PATH)
    return {"success": True, "message": "检查历史已清除"}


# ── 内部操作函数 ──────────────────────────────────────────

def _disable_channel(channel):
    """自动禁用渠道（状态=3）"""
    update_data = {
        "id": channel.get("id"),
        "status": 3
    }
    update_channel(update_data)


# ── CLI 入口 ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="渠道健康检查 + 自动优先级排序")
    sub = parser.add_subparsers(dest="command")

    # check-channel
    p_cc = sub.add_parser("check-channel", help="检测单个渠道")
    p_cc.add_argument("--id", type=int, required=True)
    p_cc.add_argument("--model", default=None)

    # check-all
    p_ca = sub.add_parser("check-all", help="检测所有渠道 + 自动排优先级")
    p_ca.add_argument("--no-auto-fix", action="store_true", help="不自动修复（仅报告）")
    p_ca.add_argument("--failures", type=int, default=DEFAULT_FAILURE_THRESHOLD,
                       help="连续失败多少次才自动禁用(默认2)")

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
        result = check_all_channels(
            auto_fix=not args.no_auto_fix,
            failure_threshold=args.failures
        )
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
