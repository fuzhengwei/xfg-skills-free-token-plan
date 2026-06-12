#!/usr/bin/env python3
"""
token_manager.py — API Key / 令牌管理
=======================================
创建、查询、分发 API Key，支持额度限制和有效期设置。
"""

import argparse
import json
import sys
import os
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from oneapi_client import (
    add_token, list_tokens, get_token, update_token, delete_token,
    get_available_models, load_config, get_base_url
)


# ── 令牌状态常量 ──────────────────────────────────────────
TOKEN_STATUS = {
    1: "已启用",
    2: "已禁用",
    3: "已过期",
    4: "已耗尽"
}


def _get_all_model_scope():
    """
    获取当前所有可用模型范围（原始模型 + auto-model）
    
    确保令牌能访问 auto-model 固定名称，同时保留原始模型名。
    
    Returns:
        str: 逗号分隔的模型列表
    """
    models_result = get_available_models()
    if not models_result.get("success"):
        return ""

    available = models_result.get("data", []) or []
    if not available:
        return ""

    # 去重，auto-model 排前面
    model_set = set(available)
    sorted_models = sorted(model_set, key=lambda m: (0 if m == "auto-model" else 1, m))
    return ",".join(sorted_models)


def create_token(name="auto-generated", remain_quota=0, unlimited_quota=True,
                 expired_time=-1, models="", subnet=""):
    """
    创建 API 令牌
    
    Args:
        name: 令牌名称
        remain_quota: 剩余额度（0=不限制，需配合 unlimited_quota=True）
        unlimited_quota: 是否无限额度
        expired_time: 过期时间（-1=永不过期, 0=已过期, >0=Unix时间戳）
        models: 限制可用模型（空=自动获取全部含 auto-model，逗号分隔）
        subnet: 限制IP网段（空=不限制）
    
    Returns:
        dict: 包含 key 的操作结果
    """
    # 如果用户未指定 models，自动获取所有可用模型（包含 auto-model）
    if not models:
        models = _get_all_model_scope()

    token_data = {
        "name": name,
        "remain_quota": remain_quota,
        "unlimited_quota": unlimited_quota,
        "expired_time": expired_time,
        "models": models,
        "subnet": subnet
    }

    result = add_token(token_data)

    if result.get("success"):
        key = result.get("data", {}).get("key", "")
        result["message"] = f"令牌创建成功！Key: {key}"
        result["data"]["warning"] = "⚠️ API Key 仅此一次返回，请妥善保存！"

    return result


def list_all_tokens(status=None, page=0, page_size=100):
    """
    列出令牌
    
    Args:
        status: 过滤状态（1=启用, 2=禁用, 3=过期, 4=耗尽）
        page: 页码
        page_size: 每页数量
    
    Returns:
        dict: 令牌列表
    """
    result = list_tokens(page, page_size)
    if not result.get("success"):
        return result

    tokens = result.get("data", []) or []
    if status is not None:
        tokens = [t for t in tokens if t.get("status") == status]

    # 丰富状态描述
    for t in tokens:
        t["status_text"] = TOKEN_STATUS.get(t.get("status", 0), "未知")
        if t.get("expired_time", -1) == -1:
            t["expired_text"] = "永不过期"
        elif t.get("expired_time", 0) == 0:
            t["expired_text"] = "已过期"
        else:
            t["expired_text"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t["expired_time"]))

        if t.get("unlimited_quota"):
            t["quota_text"] = "无限额度"
        else:
            quota = t.get("remain_quota", 0)
            t["quota_text"] = f"剩余 {quota} 额度"

    result["data"] = tokens
    result["total"] = len(tokens)
    return result


def get_valid_tokens():
    """获取所有有效令牌（已启用 + 未过期 + 有额度）"""
    result = list_all_tokens(status=1)
    if not result.get("success"):
        return result

    tokens = result.get("data", [])
    now = int(time.time())

    valid = []
    for t in tokens:
        # 检查过期
        exp = t.get("expired_time", -1)
        if exp != -1 and exp < now:
            continue
        # 检查额度
        if not t.get("unlimited_quota") and t.get("remain_quota", 0) <= 0:
            continue
        valid.append(t)

    return {"success": True, "data": valid, "total": len(valid)}


def distribute_key(create_if_none=True, name="free-token-plan", unlimited_quota=True,
                   expired_time=-1, models=""):
    """
    分发 API Key — 核心功能
    
    优先返回已有有效令牌，否则创建新的。
    
    Args:
        create_if_none: 无有效令牌时是否自动创建
        name: 新建令牌的名称
        unlimited_quota: 新建令牌是否无限额度
        expired_time: 新建令牌过期时间
        models: 限制可用模型
    
    Returns:
        dict: 完整的连接信息（地址+模型+Key）
    """
    base_url = get_base_url()
    if not base_url:
        return {"success": False, "message": "未配置 One API 服务，请先配置"}

    # 1. 查找已有有效令牌
    valid_result = get_valid_tokens()
    existing_tokens = valid_result.get("data", [])

    if existing_tokens:
        # 使用第一个有效令牌
        token = existing_tokens[0]
        return _format_distribute(base_url, token, "existing")

    # 2. 没有有效令牌
    if not create_if_none:
        return {
            "success": True,
            "message": "当前无有效令牌",
            "data": {
                "has_valid_token": False,
                "base_url": base_url
            }
        }

    # 3. 创建新令牌（自动包含所有 auto-model）
    auto_models_scope = _get_all_model_scope()

    create_result = create_token(
        name=name,
        unlimited_quota=unlimited_quota,
        expired_time=expired_time,
        models=models or auto_models_scope  # 用户指定优先，否则自动获取全部含 auto-model
    )

    if not create_result.get("success"):
        return create_result

    new_token = create_result.get("data", {})
    return _format_distribute(base_url, new_token, "created")


def _format_distribute(base_url, token, source):
    """格式化分发的连接信息"""
    # 获取可用模型
    models_result = get_available_models()
    available_models = []
    if models_result.get("success"):
        available_models = models_result.get("data", []) or []

    # 区分 auto 模型和普通模型
    auto_models = [m for m in available_models if m == "auto-model" or m.startswith("auto-")]
    regular_models = [m for m in available_models if m not in auto_models]

    token_key = token.get("key", "")
    if not token_key and source == "created":
        token_key = "(创建成功，但 Key 未返回，请从 list 命令查看)"

    # 生成 curl 验证命令
    test_model = "auto-model" if "auto-model" in auto_models else (regular_models[0] if regular_models else "auto-model")
    body = json.dumps({"model": test_model, "messages": [{"role": "user", "content": "hello"}], "max_tokens": 20}, ensure_ascii=False)
    curl_example = f"curl {base_url}/v1/chat/completions \\\n  -H 'Authorization: Bearer {token_key}' \\\n  -H 'Content-Type: application/json' \\\n  -d '{body}'" 

    return {
        "success": True,
        "message": "🔑 API Key 分发成功" + ("（使用已有令牌）" if source == "existing" else "（已创建新令牌）"),
        "data": {
            "has_valid_token": True,
            "source": source,
            "base_url": base_url,
            "api_key": token_key,
            "token_id": token.get("id"),
            "token_name": token.get("name", ""),
            "expired_time": token.get("expired_time", -1),
            "unlimited_quota": token.get("unlimited_quota", True),
            "remain_quota": token.get("remain_quota", 0),
            "available_models": available_models,
            "auto_models": auto_models,
            "regular_models": regular_models,
            "curl_example": curl_example,
            "usage_hint": f"将 api_key 填入你的 AI 工具，base_url 设为 {base_url}，模型名用 {test_model}"
        }
    }


def revoke_token(token_id):
    """撤销/禁用令牌"""
    result = update_token({"id": token_id, "status": 2})
    if result.get("success"):
        result["message"] = f"令牌 {token_id} 已禁用"
    return result


def main():
    parser = argparse.ArgumentParser(description="API Key / 令牌管理")
    sub = parser.add_subparsers(dest="command")

    # create
    p_create = sub.add_parser("create", help="创建令牌")
    p_create.add_argument("--name", default="free-token-plan")
    p_create.add_argument("--quota", type=int, default=0, help="额度（0=无限，需配合 --unlimited）")
    p_create.add_argument("--unlimited", action="store_true", default=True, help="无限额度")
    p_create.add_argument("--expired-time", type=int, default=-1, help="过期时间（-1=永不过期）")
    p_create.add_argument("--models", default="", help="限制可用模型")

    # list
    p_list = sub.add_parser("list", help="列出令牌")
    p_list.add_argument("--status", type=int, default=None, help="过滤状态")
    p_list.add_argument("--page", type=int, default=0)

    # distribute
    p_dist = sub.add_parser("distribute", help="分发 API Key")
    p_dist.add_argument("--name", default="free-token-plan")
    p_dist.add_argument("--unlimited", action="store_true", default=True)
    p_dist.add_argument("--expired-time", type=int, default=-1)
    p_dist.add_argument("--models", default="")
    p_dist.add_argument("--no-create", action="store_true", help="无有效令牌时不自动创建")

    # revoke
    p_revoke = sub.add_parser("revoke", help="禁用令牌")
    p_revoke.add_argument("--id", type=int, required=True)

    # delete
    p_del = sub.add_parser("delete", help="删除令牌")
    p_del.add_argument("--id", type=int, required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    result = {}
    if args.command == "create":
        result = create_token(args.name, args.quota, args.unlimited, args.expired_time, args.models)
    elif args.command == "list":
        result = list_all_tokens(args.status, args.page)
    elif args.command == "distribute":
        result = distribute_key(
            create_if_none=not args.no_create,
            name=args.name,
            unlimited_quota=args.unlimited,
            expired_time=args.expired_time,
            models=args.models
        )
    elif args.command == "revoke":
        result = revoke_token(args.id)
    elif args.command == "delete":
        result = delete_token(args.id)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
