#!/usr/bin/env python3
"""
channel_manager.py — 渠道管理 + 注册表
=======================================
维护渠道注册表 (data/channels.csv)，基于注册表引导用户添加渠道到 One API，
并自动为每个模型添加 auto-model 映射。
"""

import argparse
import csv
import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, "data")
CHANNELS_CSV = os.path.join(DATA_DIR, "channels.csv")

sys.path.insert(0, SCRIPT_DIR)
from oneapi_client import (
    add_channel, list_channels, get_channel, test_channel,
    delete_channel, search_channels, load_config
)


# ── 渠道类型常量 ──────────────────────────────────────────
CHANNEL_TYPES = {
    "openai": 1, "azure": 3, "custom": 8, "openaisb": 11, "api2gpt": 12,
    "anthropic": 13, "baidu": 14, "zhipu": 15, "ali": 16, "xunfei": 17,
    "aiproxy": 18, "tencent": 19, "gemini": 20, "ollama": 21, "cohere": 22,
    "cloudflare": 23, "deepl": 24, "vertexai": 25, "proxy": 26, "closeai": 27,
    "aigc2d": 28, "coze": 29, "replicate": 30, "moonshot": 31, "baichuan": 33,
    "minimax": 34, "mistral": 35, "groq": 36, "deepseek": 37, "togetherai": 38,
    "doubao": 39, "novita": 40, "siliconflow": 41, "xai": 42, "openrouter": 43,
    "baiduv2": 44, "xunfeiv2": 45, "alibailian": 46, "openaicompatible": 47,
    "geminiopenaicompatible": 48, "dummy": 999
}


def load_registry():
    """加载渠道注册表"""
    if not os.path.exists(CHANNELS_CSV):
        return []
    channels = []
    with open(CHANNELS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            channels.append(row)
    return channels


def save_registry(channels):
    """保存渠道注册表"""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not channels:
        return
    fieldnames = ["name", "type", "base_url", "models", "description", "api_key_url", "doc_url"]
    with open(CHANNELS_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for ch in channels:
            row = {k: ch.get(k, "") for k in fieldnames}
            writer.writerow(row)


def list_registry(keyword=None):
    """列出注册表中的渠道"""
    channels = load_registry()
    if keyword:
        keyword_lower = keyword.lower()
        channels = [
            ch for ch in channels
            if keyword_lower in ch.get("name", "").lower()
            or keyword_lower in ch.get("description", "").lower()
            or keyword_lower in ch.get("models", "").lower()
        ]
    return {"success": True, "data": channels, "total": len(channels)}


def add_to_registry(name, channel_type, base_url, models, description="", api_key_url="", doc_url=""):
    """添加渠道到注册表"""
    channels = load_registry()

    # 检查是否已存在
    for ch in channels:
        if ch.get("name", "").lower() == name.lower():
            return {"success": False, "message": f"渠道 '{name}' 已存在于注册表中"}

    # 解析渠道类型
    if isinstance(channel_type, str):
        type_id = CHANNEL_TYPES.get(channel_type.lower())
        if type_id is None:
            try:
                type_id = int(channel_type)
            except ValueError:
                return {"success": False, "message": f"未知渠道类型: {channel_type}"}
    else:
        type_id = channel_type

    entry = {
        "name": name,
        "type": str(type_id),
        "base_url": base_url,
        "models": models,
        "description": description,
        "api_key_url": api_key_url,
        "doc_url": doc_url
    }
    channels.append(entry)
    save_registry(channels)

    return {"success": True, "message": f"渠道 '{name}' 已添加到注册表"}


def _build_auto_model_mapping(models_list):
    """
    为模型列表自动构建 auto-model 映射
    
    将每个原始模型映射为固定名称 "auto-model"，
    这样用户在 AI 工具中统一使用 "auto-model" 作为模型名，
    One API 通过 model_mapping 路由到渠道的真实模型。
    换渠道只需改映射，不用改工具配置。
    
    例如：渠道有 agnes-2.0-flash → 映射 auto-model → agnes-2.0-flash
    
    Args:
        models_list: 原始模型名称列表
    
    Returns:
        tuple: (all_models_str, model_mapping_dict, auto_models_list)
    """
    seen = set()
    all_models = []
    model_mapping = {}
    auto_models = []

    for model in models_list:
        # 去重
        if model in seen:
            continue
        seen.add(model)
        all_models.append(model)

        # 跳过 auto-model 自身，避免递归
        if model == "auto-model":
            continue

    # 将第一个模型映射为 auto-model（主模型）
    # 所有模型也各自映射为 auto-model（优先级：后添加的覆盖，即最后一个模型生效）
    if models_list:
        if "auto-model" not in seen:
            all_models.append("auto-model")
        # 每个模型都映射到 auto-model，最后添加的优先级最高
        for model in models_list:
            if model != "auto-model":
                model_mapping["auto-model"] = model
        auto_models = ["auto-model"]

    return ",".join(all_models), model_mapping, auto_models


def add_to_oneapi(channel_name, api_key, priority=0, group="default"):
    """
    将注册表中的渠道添加到 One API，自动添加 auto-model 映射
    
    Args:
        channel_name: 注册表中的渠道名称
        api_key: API 密钥
        priority: 优先级
        group: 分组
    
    Returns:
        dict: 操作结果
    """
    # 1. 从注册表查找
    channels = load_registry()
    registry_entry = None
    for ch in channels:
        if ch.get("name", "").lower() == channel_name.lower():
            registry_entry = ch
            break

    if not registry_entry:
        available = ", ".join(ch.get("name", "") for ch in channels)
        return {
            "success": False,
            "message": f"注册表中未找到渠道 '{channel_name}'。可用渠道: {available}"
        }

    # 2. 解析原始模型
    models = [m.strip() for m in registry_entry.get("models", "").split(",") if m.strip()]

    # 3. 自动构建 auto-model 映射
    all_models_str, model_mapping, auto_models = _build_auto_model_mapping(models)

    # 4. 构建渠道数据
    channel_data = {
        "type": int(registry_entry.get("type", 1)),
        "key": api_key,
        "name": registry_entry.get("name", channel_name),
        "base_url": registry_entry.get("base_url", ""),
        "models": all_models_str,
        "group": group,
        "model_mapping": json.dumps(model_mapping) if model_mapping else "",
        "priority": priority,
        "weight": 1,
        "config": "{}",
        "system_prompt": ""
    }

    # 5. 调用 One API 添加渠道
    result = add_channel(channel_data)

    if result.get("success"):
        result["message"] = f"渠道 '{channel_name}' 已添加到 One API，包含 {len(models)} 个模型 + {len(auto_models)} 个 auto-model 映射"
        result["data"] = {
            "channel_name": channel_name,
            "models": models,
            "auto_models": auto_models,
            "model_mapping": model_mapping
        }

    return result


def add_custom_channel(name, channel_type, api_key, base_url, models_str, priority=0, group="default"):
    """
    直接添加自定义渠道到 One API（不依赖注册表），自动添加 auto-model 映射
    
    Args:
        name: 渠道名称
        channel_type: 渠道类型（名称或数字ID）
        api_key: API 密钥
        base_url: API 基础地址
        models_str: 模型列表（逗号分隔）
        priority: 优先级
        group: 分组
    
    Returns:
        dict: 操作结果
    """
    # 1. 解析渠道类型
    if isinstance(channel_type, str):
        type_id = CHANNEL_TYPES.get(channel_type.lower())
        if type_id is None:
            try:
                type_id = int(channel_type)
            except ValueError:
                return {"success": False, "message": f"未知渠道类型: {channel_type}"}
    else:
        type_id = channel_type

    # 2. 解析原始模型
    models = [m.strip() for m in models_str.split(",") if m.strip()]

    # 3. 自动构建 auto-model 映射
    all_models_str, model_mapping, auto_models = _build_auto_model_mapping(models)

    # 4. 构建渠道数据
    channel_data = {
        "type": type_id,
        "key": api_key,
        "name": name,
        "base_url": base_url.rstrip("/") if base_url else "",
        "models": all_models_str,
        "group": group,
        "model_mapping": json.dumps(model_mapping) if model_mapping else "",
        "priority": priority,
        "weight": 1,
        "config": "{}",
        "system_prompt": ""
    }

    # 5. 调用 One API 添加渠道
    result = add_channel(channel_data)

    if result.get("success"):
        result["message"] = f"渠道 '{name}' 已添加到 One API，包含 {len(models)} 个模型 + {len(auto_models)} 个 auto-model 映射"
        result["data"] = {
            "channel_name": name,
            "models": models,
            "auto_models": auto_models,
            "model_mapping": model_mapping
        }

    return result


def list_oneapi_channels(page=0):
    """列出 One API 中已配置的渠道"""
    return list_channels(page)


def test_oneapi_channel(channel_id, model=None):
    """测试 One API 中的渠道"""
    return test_channel(channel_id, model)


def remove_oneapi_channel(channel_id):
    """从 One API 中删除渠道"""
    return delete_channel(channel_id)


def sync_auto_models(channel_id):
    """
    为指定渠道的模型重新同步 auto-model 映射
    
    Args:
        channel_id: One API 渠道 ID
    
    Returns:
        dict: 操作结果
    """
    # 获取渠道详情
    ch_result = get_channel(channel_id)
    if not ch_result.get("success"):
        return ch_result

    channel = ch_result.get("data", {})
    if not channel:
        return {"success": False, "message": f"未找到渠道 ID={channel_id}"}

    current_models = [m.strip() for m in channel.get("models", "").split(",") if m.strip()]

    # 分离原始模型和 auto-model
    original_models = [m for m in current_models if not m.startswith("auto-")]
    auto_models = [m for m in current_models if m.startswith("auto-")]

    # 重建 auto-model 映射
    expected_auto = set()
    model_mapping = {}

    # 解析现有 model_mapping
    existing_mapping = {}
    if channel.get("model_mapping"):
        try:
            existing_mapping = json.loads(channel["model_mapping"])
        except json.JSONDecodeError:
            pass

    for model in original_models:
        auto_model = f"auto-{model}"
        expected_auto.add(auto_model)
        model_mapping[auto_model] = model

    # 合并：保留现有的非 auto 映射
    for k, v in existing_mapping.items():
        if not k.startswith("auto-"):
            model_mapping[k] = v

    # 更新 models 列表
    new_models = original_models + [f"auto-{m}" for m in original_models]

    # 更新渠道
    update_data = {
        "id": channel_id,
        "type": channel.get("type", 1),
        "key": channel.get("key", ""),
        "name": channel.get("name", ""),
        "base_url": channel.get("base_url", ""),
        "models": ",".join(new_models),
        "group": channel.get("group", "default"),
        "model_mapping": json.dumps(model_mapping),
        "priority": channel.get("priority", 0),
        "weight": channel.get("weight", 1),
        "config": channel.get("config", "{}"),
        "system_prompt": channel.get("system_prompt", "")
    }

    from oneapi_client import update_channel
    result = update_channel(update_data)

    if result.get("success"):
        result["message"] = f"渠道 {channel_id} 的 auto-model 映射已同步，共 {len(original_models)} 个模型"
        result["data"] = {
            "models": original_models,
            "auto_models": [f"auto-{m}" for m in original_models],
            "model_mapping": model_mapping
        }

    return result


def main():
    parser = argparse.ArgumentParser(description="渠道管理 + 注册表")
    sub = parser.add_subparsers(dest="command")

    # list-registry
    p_lr = sub.add_parser("list-registry", help="列出渠道注册表")
    p_lr.add_argument("--keyword", default=None, help="搜索关键词")

    # add-to-registry
    p_ar = sub.add_parser("add-to-registry", help="添加渠道到注册表")
    p_ar.add_argument("--name", required=True)
    p_ar.add_argument("--type", required=True, help="渠道类型名称或ID")
    p_ar.add_argument("--base-url", required=True)
    p_ar.add_argument("--models", required=True, help="逗号分隔的模型列表")
    p_ar.add_argument("--description", default="")
    p_ar.add_argument("--api-key-url", default="")
    p_ar.add_argument("--doc-url", default="")

    # add (to One API via registry)
    p_add = sub.add_parser("add", help="将注册表中的渠道添加到 One API")
    p_add.add_argument("--name", required=True, help="注册表中的渠道名称")
    p_add.add_argument("--key", required=True, help="API 密钥")
    p_add.add_argument("--priority", type=int, default=0)
    p_add.add_argument("--group", default="default")

    # add-custom (directly to One API)
    p_ac = sub.add_parser("add-custom", help="直接添加自定义渠道到 One API")
    p_ac.add_argument("--name", required=True, help="渠道名称")
    p_ac.add_argument("--type", required=True, help="渠道类型名称或ID")
    p_ac.add_argument("--key", required=True, help="API 密钥")
    p_ac.add_argument("--base-url", required=True, help="API 基础地址")
    p_ac.add_argument("--models", required=True, help="模型列表（逗号分隔）")
    p_ac.add_argument("--priority", type=int, default=0)
    p_ac.add_argument("--group", default="default")

    # list (One API channels)
    p_list = sub.add_parser("list", help="列出 One API 中的渠道")
    p_list.add_argument("--page", type=int, default=0)

    # test
    p_test = sub.add_parser("test", help="测试 One API 渠道")
    p_test.add_argument("--id", type=int, required=True)
    p_test.add_argument("--model", default=None)

    # sync-auto-models
    p_sync = sub.add_parser("sync-auto-models", help="同步渠道的 auto-model 映射")
    p_sync.add_argument("--id", type=int, required=True, help="渠道 ID")

    # remove
    p_rm = sub.add_parser("remove", help="从 One API 删除渠道")
    p_rm.add_argument("--id", type=int, required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    result = {}
    if args.command == "list-registry":
        result = list_registry(args.keyword)
    elif args.command == "add-to-registry":
        result = add_to_registry(
            args.name, args.type, args.base_url, args.models,
            args.description, args.api_key_url, args.doc_url
        )
    elif args.command == "add":
        result = add_to_oneapi(args.name, args.key, args.priority, args.group)
    elif args.command == "add-custom":
        result = add_custom_channel(
            args.name, args.type, args.key, args.base_url,
            args.models, args.priority, args.group
        )
    elif args.command == "list":
        result = list_oneapi_channels(args.page)
    elif args.command == "test":
        result = test_oneapi_channel(args.id, args.model)
    elif args.command == "sync-auto-models":
        result = sync_auto_models(args.id)
    elif args.command == "remove":
        result = remove_oneapi_channel(args.id)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
