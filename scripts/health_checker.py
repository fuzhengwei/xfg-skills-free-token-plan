#!/usr/bin/env python3
"""
health_checker.py — 渠道健康检查
==================================
定期检测渠道和令牌状态，自动降级异常渠道，生成报告。
"""

import argparse
import json
import sys
import os
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from oneapi_client import (
    list_channels, test_channel, update_channel, get_channel,
    list_tokens, get_subscription, load_config
)


# ── 状态常量 ──────────────────────────────────────────────
CHANNEL_STATUS = {0: "未知", 1: "启用", 2: "手动禁用", 3: "自动禁用"}
TOKEN_STATUS = {1: "已启用", 2: "已禁用", 3: "已过期", 4: "已耗尽"}


def check_channel_health(channel_id, model=None):
    """
    检测单个渠道健康状态
    
    Args:
        channel_id: 渠道 ID
        model: 测试使用的模型（可选）
    
    Returns:
        dict: 健康检查结果
    """
    # 获取渠道信息
    ch_result = get_channel(channel_id)
    if not ch_result.get("success"):
        return {"success": False, "channel_id": channel_id, "message": "渠道不存在"}

    channel = ch_result.get("data", {})

    # 测试渠道
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


def check_all_channels(auto_fix=True, disable_threshold_seconds=10):
    """
    检测所有渠道健康状态
    
    Args:
        auto_fix: 是否自动修复（禁用失败渠道）
        disable_threshold_seconds: 响应时间超过此值自动降级
    
    Returns:
        dict: 所有渠道的健康报告
    """
    # 获取所有渠道
    channels_result = list_channels(page=0, page_size=100)
    if not channels_result.get("success"):
        return channels_result

    channels = channels_result.get("data", []) or []
    results = []
    healthy_count = 0
    unhealthy_count = 0
    disabled_count = 0

    for ch in channels:
        ch_id = ch.get("id")
        if not ch_id:
            continue

        health = check_channel_health(ch_id)

        if health.get("healthy"):
            healthy_count += 1
            # 检查响应时间
            if health.get("response_time", 0) > disable_threshold_seconds and auto_fix:
                # 响应过慢，降低优先级
                _downgrade_channel(ch, health)
                health["action"] = "priority_downgraded"
        else:
            unhealthy_count += 1
            if auto_fix and ch.get("status") == 1:
                # 自动禁用
                _disable_channel(ch)
                health["action"] = "auto_disabled"
                disabled_count += 1

        results.append(health)

    return {
        "success": True,
        "data": {
            "total": len(results),
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "auto_disabled": disabled_count,
            "channels": results
        },
        "message": f"健康检查完成: {healthy_count} 正常, {unhealthy_count} 异常" +
                   (f", {disabled_count} 已自动禁用" if disabled_count > 0 else "")
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

    # 检查所有令牌
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


def _disable_channel(channel):
    """自动禁用渠道"""
    update_data = {
        "id": channel.get("id"),
        "status": 3  # 自动禁用
    }
    update_channel(update_data)


def _downgrade_channel(channel, health_info):
    """降低渠道优先级"""
    current_priority = channel.get("priority", 0)
    update_data = {
        "id": channel.get("id"),
        "priority": max(current_priority - 1, -10)
    }
    update_channel(update_data)


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
    p_ca.add_argument("--threshold", type=float, default=10.0, help="响应时间阈值(秒)")

    # check-tokens
    p_ct = sub.add_parser("check-tokens", help="检测令牌状态")
    p_ct.add_argument("--id", type=int, default=None, help="令牌 ID")

    # check-quota
    sub.add_parser("check-quota", help="检查额度")

    # stats
    sub.add_parser("stats", help="渠道统计")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    result = {}
    if args.command == "check-channel":
        result = check_channel_health(args.id, args.model)
    elif args.command == "check-all":
        result = check_all_channels(auto_fix=not args.no_auto_fix, disable_threshold_seconds=args.threshold)
    elif args.command == "check-tokens":
        result = check_token_status(args.id)
    elif args.command == "check-quota":
        result = check_quota()
    elif args.command == "stats":
        result = get_channel_stats()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
