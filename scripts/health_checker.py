#!/usr/bin/env python3
"""
health_checker.py — 渠道健康检查 + 定时检测
==============================================
定期检测渠道和令牌状态，自动降级异常渠道，恢复后自动还原。
支持连续失败阈值、检查历史持久化、定时任务注册。

检查历史文件: data/health_history.json
结构:
{
  "channels": {
    "<channel_id>": {
      "original_priority": 0,       # 自动禁用前的原始优先级
      "consecutive_failures": 0,    # 连续失败次数
      "disabled_at": null,          # 自动禁用时间 (ISO)
      "last_check": "2026-...",     # 最后检查时间
      "last_healthy": true          # 最后检查是否健康
    }
  },
  "last_full_check": "2026-...",    # 上次全量检查时间
  "check_count": 0                  # 总检查次数
}
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

# ── 默认阈值 ──────────────────────────────────────────────
DEFAULT_FAILURE_THRESHOLD = 2     # 连续失败 N 次才禁用
DEFAULT_SLOW_THRESHOLD = 10.0     # 响应时间阈值（秒）
DEFAULT_CHECK_INTERVAL = 30       # 定时检查间隔（分钟）


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
    """获取渠道历史记录，不存在则创建默认"""
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
        "priority": channel.get("priority", 0)
    }


def check_all_channels(auto_fix=True, slow_threshold=DEFAULT_SLOW_THRESHOLD,
                       failure_threshold=DEFAULT_FAILURE_THRESHOLD):
    """
    检测所有渠道健康状态，自动处理异常和恢复

    逻辑:
    - 健康 + 之前自动禁用 → 恢复启用 + 还原优先级
    - 健康 + 响应慢 → 降低优先级
    - 不健康 + 连续失败达阈值 → 自动禁用（记录原始优先级）
    - 不健康 + 连续失败未达阈值 → 仅记录，不操作

    Args:
        auto_fix: 是否自动修复
        slow_threshold: 响应时间阈值（秒）
        failure_threshold: 连续失败多少次才自动禁用

    Returns:
        dict: 所有渠道的健康报告
    """
    channels_result = list_channels(page=0, page_size=100)
    if not channels_result.get("success"):
        return channels_result

    channels = channels_result.get("data", []) or []
    history = _load_history()
    results = []

    healthy_count = 0
    unhealthy_count = 0
    auto_disabled_count = 0
    recovered_count = 0
    downgraded_count = 0

    for ch in channels:
        ch_id = ch.get("id")
        if not ch_id:
            continue

        health = check_channel_health(ch_id)
        ch_history = _get_channel_history(history, ch_id)
        ch_history["last_check"] = _now_iso()

        if health.get("healthy"):
            healthy_count += 1
            ch_history["consecutive_failures"] = 0
            ch_history["last_healthy"] = True

            # ── 恢复逻辑：之前被自动禁用，现在健康了 → 恢复 ──
            if auto_fix and ch.get("status") == 3 and ch_history.get("disabled_at"):
                _recover_channel(ch, ch_history)
                health["action"] = "recovered"
                health["recovered_priority"] = ch_history.get("original_priority", 0)
                recovered_count += 1

            # ── 响应慢 → 降低优先级 ──
            elif auto_fix and health.get("response_time", 0) > slow_threshold:
                # 首次降级时记录原始优先级
                if ch_history.get("original_priority") is None:
                    ch_history["original_priority"] = ch.get("priority", 0)
                _downgrade_channel(ch)
                health["action"] = "priority_downgraded"
                downgraded_count += 1

        else:
            unhealthy_count += 1
            ch_history["consecutive_failures"] = ch_history.get("consecutive_failures", 0) + 1
            ch_history["last_healthy"] = False

            if auto_fix and ch.get("status") == 1:
                failures = ch_history["consecutive_failures"]
                if failures >= failure_threshold:
                    # 记录原始优先级并禁用
                    ch_history["original_priority"] = ch.get("priority", 0)
                    _disable_channel(ch)
                    ch_history["disabled_at"] = _now_iso()
                    health["action"] = f"auto_disabled (连续失败{failures}次)"
                    auto_disabled_count += 1
                else:
                    health["action"] = f"failure_recorded ({failures}/{failure_threshold})"

            # 对已经被自动禁用的渠道，检查是否恢复
            elif auto_fix and ch.get("status") == 3 and not ch_history.get("disabled_at"):
                # 状态3但没有记录，说明是外部禁用的，跳过
                pass

        results.append(health)

    # 更新全局历史
    history["last_full_check"] = _now_iso()
    history["check_count"] = history.get("check_count", 0) + 1
    _save_history(history)

    # 构建消息
    parts = [f"{healthy_count} 正常", f"{unhealthy_count} 异常"]
    if auto_disabled_count > 0:
        parts.append(f"{auto_disabled_count} 已自动禁用")
    if recovered_count > 0:
        parts.append(f"{recovered_count} 已自动恢复")
    if downgraded_count > 0:
        parts.append(f"{downgraded_count} 已降级")

    return {
        "success": True,
        "data": {
            "total": len(results),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "auto_disabled": auto_disabled_count,
            "recovered": recovered_count,
            "downgraded": downgraded_count,
            "failure_threshold": failure_threshold,
            "slow_threshold": slow_threshold,
            "channels": results
        },
        "message": f"健康检查完成: " + ", ".join(parts)
    }


def check_token_status(token_id=None):
    """
    检测令牌状态

    Args:
        token_id: 令牌 ID（空=检查所有）

    Returns:
        dict: 令牌状态报告
    """
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

    summary = {
        "last_full_check": history.get("last_full_check"),
        "total_checks": history.get("check_count", 0),
        "channels_tracked": len(channels),
        "auto_disabled_channels": [],
        "details": {}
    }

    for ch_id, ch_data in channels.items():
        summary["details"][ch_id] = ch_data
        if ch_data.get("disabled_at"):
            summary["auto_disabled_channels"].append({
                "channel_id": int(ch_id),
                "original_priority": ch_data.get("original_priority", 0),
                "disabled_at": ch_data.get("disabled_at"),
                "consecutive_failures": ch_data.get("consecutive_failures", 0)
            })

    return {
        "success": True,
        "data": summary,
        "message": f"历史记录: {summary['total_checks']} 次检查, "
                   f"{len(summary['auto_disabled_channels'])} 个渠道待恢复"
    }


def clear_history():
    """清除检查历史"""
    if os.path.exists(HISTORY_PATH):
        os.remove(HISTORY_PATH)
    return {"success": True, "message": "检查历史已清除"}


def schedule_info(interval_minutes=DEFAULT_CHECK_INTERVAL):
    """
    输出定时检测配置信息（供 AI 读取后注册 cron）

    Args:
        interval_minutes: 检查间隔（分钟）

    Returns:
        dict: 定时任务配置信息
    """
    return {
        "success": True,
        "data": {
            "interval_minutes": interval_minutes,
            "command": f"python3 {os.path.join(SCRIPT_DIR, 'health_checker.py')} check-all",
            "cron_expr": f"*/{interval_minutes} * * * *",
            "description": f"每 {interval_minutes} 分钟自动检测渠道健康状态，异常渠道自动禁用，恢复后自动启用",
            "note": "AI 应使用 cron 工具注册定时任务，sessionTarget=isolated, payload.kind=agentTurn"
        },
        "message": f"建议每 {interval_minutes} 分钟执行一次健康检查"
    }


# ── 内部操作函数 ──────────────────────────────────────────

def _disable_channel(channel):
    """自动禁用渠道（状态=3）"""
    update_data = {
        "id": channel.get("id"),
        "status": 3
    }
    update_channel(update_data)


def _downgrade_channel(channel):
    """降低渠道优先级"""
    current_priority = channel.get("priority", 0)
    update_data = {
        "id": channel.get("id"),
        "priority": max(current_priority - 1, -10)
    }
    update_channel(update_data)


def _recover_channel(channel, ch_history):
    """恢复渠道：重新启用 + 还原优先级"""
    original_priority = ch_history.get("original_priority", 0)
    update_data = {
        "id": channel.get("id"),
        "status": 1,  # 启用
        "priority": original_priority
    }
    update_channel(update_data)
    # 清除禁用记录
    ch_history["disabled_at"] = None
    ch_history["original_priority"] = None


# ── CLI 入口 ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="渠道健康检查")
    sub = parser.add_subparsers(dest="command")

    # check-channel
    p_cc = sub.add_parser("check-channel", help="检测单个渠道")
    p_cc.add_argument("--id", type=int, required=True)
    p_cc.add_argument("--model", default=None)

    # check-all
    p_ca = sub.add_parser("check-all", help="检测所有渠道")
    p_ca.add_argument("--no-auto-fix", action="store_true", help="不自动修复")
    p_ca.add_argument("--threshold", type=float, default=DEFAULT_SLOW_THRESHOLD,
                       help="响应慢阈值(秒)")
    p_ca.add_argument("--failures", type=int, default=DEFAULT_FAILURE_THRESHOLD,
                       help="连续失败多少次才自动禁用")

    # check-tokens
    p_ct = sub.add_parser("check-tokens", help="检测令牌状态")
    p_ct.add_argument("--id", type=int, default=None, help="令牌 ID")

    # check-quota
    sub.add_parser("check-quota", help="检查额度")

    # stats
    sub.add_parser("stats", help="渠道统计")

    # history
    sub.add_parser("history", help="查看检查历史")

    # clear-history
    sub.add_parser("clear-history", help="清除检查历史")

    # schedule
    p_sched = sub.add_parser("schedule", help="定时检测配置信息")
    p_sched.add_argument("--interval", type=int, default=DEFAULT_CHECK_INTERVAL,
                          help="检查间隔(分钟)")

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
            slow_threshold=args.threshold,
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
    elif args.command == "schedule":
        result = schedule_info(args.interval)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
