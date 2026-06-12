#!/usr/bin/env python3
"""
service_manager.py — One API 服务连接管理
==========================================
管理 One API 服务实例的连接信息，负责检测、保存、登录、验证。
"""

import argparse
import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from oneapi_client import load_config, save_config, login, get_status, get_access_token, get_self, CONFIG_PATH


def detect():
    """
    检测本地是否已有可用的 One API 配置
    
    Returns:
        dict: {"configured": bool, "valid": bool, "config": dict|null, "message": str}
    """
    config = load_config()
    if not config:
        return {
            "configured": False,
            "valid": False,
            "config": None,
            "message": "未检测到 One API 配置。请运行 save 命令添加服务，或使用 setup-helper 部署新服务。"
        }

    # 有配置，验证连接
    check = check_connection()
    return {
        "configured": True,
        "valid": check["success"],
        "config": {
            "url": config.get("url"),
            "username": config.get("username"),
            "user_id": config.get("user_id"),
            "role": config.get("role")
        },
        "message": check.get("message", "连接正常" if check["success"] else "连接失败")
    }


def save(url, username, password):
    """
    保存服务连接配置并登录
    
    Args:
        url: One API 服务地址
        username: 用户名
        password: 密码
    
    Returns:
        dict: 操作结果
    """
    # 先保存 URL，以便后续请求使用
    config = {
        "url": url.rstrip("/"),
        "username": username,
        "password": password,
        "access_token": "",
        "user_id": 0,
        "role": 0
    }
    save_config(config)

    # 验证连接
    status = get_status()
    if not status.get("success"):
        # 清除无效配置
        if os.path.exists(CONFIG_PATH):
            os.remove(CONFIG_PATH)
        return {"success": False, "message": f"无法连接到 {url}: {status.get('message', '未知错误')}"}

    # 登录
    login_result = login(username, password)
    if not login_result.get("success"):
        return {"success": False, "message": f"登录失败: {login_result.get('message', '未知错误')}"}

    # 获取 access_token
    token_result = get_access_token()
    if not token_result.get("success"):
        # 登录成功但获取 token 失败，仍可使用 session
        return {
            "success": True,
            "message": f"服务配置保存成功，登录成功（AccessToken 获取失败，将使用 Session）",
            "data": {
                "url": url,
                "username": username,
                "user_id": login_result.get("data", {}).get("id"),
                "role": login_result.get("data", {}).get("role")
            }
        }

    return {
        "success": True,
        "message": "服务配置保存成功，登录成功",
        "data": {
            "url": url,
            "username": username,
            "user_id": login_result.get("data", {}).get("id"),
            "role": login_result.get("data", {}).get("role")
        }
    }


def check_connection():
    """
    验证当前配置的连接是否可用
    
    Returns:
        dict: {"success": bool, "message": str, "data": dict|null}
    """
    config = load_config()
    if not config:
        return {"success": False, "message": "未配置 One API 服务"}

    # 1. 检查服务是否可达
    status = get_status()
    if not status.get("success"):
        return {"success": False, "message": f"服务不可达: {status.get('message')}"}

    # 2. 尝试登录/验证认证
    # 先尝试用 access_token
    if config.get("access_token"):
        user_info = get_self()
        if user_info.get("success"):
            return {
                "success": True,
                "message": "连接正常",
                "data": {
                    "url": config["url"],
                    "username": config.get("username"),
                    "user_id": user_info.get("data", {}).get("id"),
                    "role": user_info.get("data", {}).get("role")
                }
            }

    # access_token 失效，尝试重新登录
    if config.get("username") and config.get("password"):
        login_result = login(config["username"], config["password"])
        if login_result.get("success"):
            # 重新获取 access_token
            get_access_token()
            return {
                "success": True,
                "message": "连接恢复（已重新登录）",
                "data": {
                    "url": config["url"],
                    "username": config["username"],
                    "user_id": login_result.get("data", {}).get("id"),
                    "role": login_result.get("data", {}).get("role")
                }
            }
        return {"success": False, "message": f"登录失败: {login_result.get('message')}"}

    return {"success": False, "message": "无有效认证信息，请重新配置"}


def show_config():
    """显示当前配置（隐藏敏感信息）"""
    config = load_config()
    if not config:
        return {"success": False, "message": "未配置 One API 服务"}

    safe_config = {
        "url": config.get("url"),
        "username": config.get("username"),
        "user_id": config.get("user_id"),
        "role": config.get("role"),
        "has_password": bool(config.get("password")),
        "has_access_token": bool(config.get("access_token"))
    }
    return {"success": True, "data": safe_config}


def reset():
    """重置配置"""
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
        return {"success": True, "message": "配置已重置"}
    return {"success": True, "message": "无配置需要重置"}


def main():
    parser = argparse.ArgumentParser(description="One API 服务连接管理")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("detect", help="检测 One API 配置")

    p_save = sub.add_parser("save", help="保存服务连接配置")
    p_save.add_argument("--url", required=True, help="One API 地址")
    p_save.add_argument("--username", required=True, help="用户名")
    p_save.add_argument("--password", required=True, help="密码")

    sub.add_parser("check", help="验证连接")
    sub.add_parser("show", help="显示配置")
    sub.add_parser("reset", help="重置配置")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "detect":
        result = detect()
    elif args.command == "save":
        result = save(args.url, args.username, args.password)
    elif args.command == "check":
        result = check_connection()
    elif args.command == "show":
        result = show_config()
    elif args.command == "reset":
        result = reset()
    else:
        result = {"success": False, "message": f"未知命令: {args.command}"}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
