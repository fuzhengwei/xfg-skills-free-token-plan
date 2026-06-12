#!/usr/bin/env python3
"""
auto_model.py — auto-model 映射管理
=====================================
为 One API 渠道的模型自动生成 auto-* 前缀映射，
实现统一入口路由，用户无需关心底层渠道。
"""

import argparse
import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from oneapi_client import (
    list_channels, get_channel, update_channel, get_available_models,
    list_models, load_config
)


def list_auto_models():
    """
    列出所有 auto-model 映射
    
    Returns:
        dict: 所有渠道的 auto-model 映射关系
    """
    channels_result = list_channels(page=0, page_size=100)
    if not channels_result.get("success"):
        return channels_result

    channels = channels_result.get("data", []) or []
    mappings = []

    for ch in channels:
        models_str = ch.get("models", "")
        if not models_str:
            continue

        models = [m.strip() for m in models_str.split(",") if m.strip()]
        auto_models = [m for m in models if m.startswith("auto-")]
        regular_models = [m for m in models if not m.startswith("auto-")]

        # 解析 model_mapping
        model_mapping = {}
        if ch.get("model_mapping"):
            try:
                model_mapping = json.loads(ch["model_mapping"])
            except json.JSONDecodeError:
                pass

        auto_mapping = {k: v for k, v in model_mapping.items() if k.startswith("auto-")}

        if auto_models or auto_mapping:
            mappings.append({
                "channel_id": ch.get("id"),
                "channel_name": ch.get("name", ""),
                "channel_type": ch.get("type", 0),
                "channel_status": ch.get("status", 0),
                "regular_models": regular_models,
                "auto_models": auto_models,
                "auto_mapping": auto_mapping
            })

    return {
        "success": True,
        "data": mappings,
        "total": len(mappings),
        "message": f"共 {len(mappings)} 个渠道配置了 auto-model 映射"
    }


def get_available_auto_models():
    """
    获取所有当前可用的 auto-model 列表（从 /v1/models 接口）
    
    Returns:
        dict: 可用的 auto-model 列表
    """
    result = list_models()
    if not result.get("success"):
        return result

    all_models = result.get("data", [])
    auto_models = [m for m in all_models if m.get("id", "").startswith("auto-")]
    regular_models = [m for m in all_models if not m.get("id", "").startswith("auto-")]

    return {
        "success": True,
        "data": {
            "auto_models": [{"id": m["id"], "owned_by": m.get("owned_by", "")} for m in auto_models],
            "regular_models": [{"id": m["id"], "owned_by": m.get("owned_by", "")} for m in regular_models],
            "auto_count": len(auto_models),
            "regular_count": len(regular_models)
        },
        "message": f"可用模型: {len(auto_models)} 个 auto-model, {len(regular_models)} 个普通模型"
    }


def sync_channel_auto_models(channel_id):
    """
    为指定渠道同步 auto-model 映射
    
    Args:
        channel_id: 渠道 ID
    
    Returns:
        dict: 同步结果
    """
    from channel_manager import sync_auto_models
    return sync_auto_models(channel_id)


def sync_all_auto_models():
    """
    为所有渠道同步 auto-model 映射
    
    Returns:
        dict: 同步结果
    """
    channels_result = list_channels(page=0, page_size=100)
    if not channels_result.get("success"):
        return channels_result

    channels = channels_result.get("data", []) or []
    results = []
    success_count = 0
    fail_count = 0

    for ch in channels:
        ch_id = ch.get("id")
        if not ch_id:
            continue

        sync_result = sync_channel_auto_models(ch_id)
        if sync_result.get("success"):
            success_count += 1
        else:
            fail_count += 1

        results.append({
            "channel_id": ch_id,
            "channel_name": ch.get("name", ""),
            "success": sync_result.get("success", False),
            "message": sync_result.get("message", "")
        })

    return {
        "success": True,
        "data": {
            "total": len(results),
            "success": success_count,
            "failed": fail_count,
            "channels": results
        },
        "message": f"auto-model 同步完成: {success_count} 成功, {fail_count} 失败"
    }


def explain_auto_model():
    """
    解释 auto-model 机制
    
    Returns:
        dict: auto-model 使用说明
    """
    return {
        "success": True,
        "data": {
            "concept": "auto-model 是为每个原始模型自动生成的路由别名",
            "format": "auto-{原始模型名}",
            "examples": [
                {"original": "gpt-4o", "auto": "auto-gpt-4o"},
                {"original": "deepseek-chat", "auto": "auto-deepseek-chat"},
                {"original": "claude-3-5-sonnet-20241022", "auto": "auto-claude-3-5-sonnet-20241022"}
            ],
            "benefit": "使用 auto-model 时，One API 会自动路由到提供该模型的可用渠道，无需关心具体是哪个渠道",
            "usage": "在 API 请求中将 model 字段设为 auto-model 名称即可",
            "fallback": "如果 auto-model 对应的所有渠道都不可用，One API 会返回错误，此时可尝试其他 auto-model"
        }
    }


def main():
    parser = argparse.ArgumentParser(description="auto-model 映射管理")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="列出所有 auto-model 映射")
    sub.add_parser("available", help="获取可用 auto-model 列表")
    sub.add_parser("explain", help="解释 auto-model 机制")

    p_sync = sub.add_parser("sync", help="同步 auto-model 映射")
    p_sync.add_argument("--id", type=int, default=None, help="渠道 ID（空=同步所有）")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    result = {}
    if args.command == "list":
        result = list_auto_models()
    elif args.command == "available":
        result = get_available_auto_models()
    elif args.command == "explain":
        result = explain_auto_model()
    elif args.command == "sync":
        if args.id:
            result = sync_channel_auto_models(args.id)
        else:
            result = sync_all_auto_models()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
