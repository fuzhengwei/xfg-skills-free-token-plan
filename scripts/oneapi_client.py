#!/usr/bin/env python3
"""
oneapi_client.py — One API HTTP 客户端
========================================
封装 One API 的所有 HTTP 接口调用，提供统一的错误处理和认证管理。
"""

import argparse
import json
import sys
import os
import time
import urllib.request
import urllib.error
import urllib.parse

# ── 配置路径 ──────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data")
CONFIG_PATH = os.path.join(DATA_DIR, "service_config.json")

# ── 默认值 ────────────────────────────────────────────────
DEFAULT_TIMEOUT = 30  # 秒
MAX_RETRIES = 2


def load_config():
    """加载服务连接配置"""
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_config(config):
    """保存服务连接配置"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_base_url():
    """获取 One API 基础 URL"""
    config = load_config()
    if config and config.get("url"):
        return config["url"].rstrip("/")
    return None


def get_auth_header():
    """获取认证头（优先 access_token，否则 session cookie）"""
    config = load_config()
    if not config:
        return {}, ""
    token = config.get("access_token")
    if token:
        return {"Authorization": token}, ""
    # 回退到 session cookie
    cookie = config.get("session_cookie", "")
    return {}, cookie


def get_bearer_header():
    """获取 Bearer 认证头（用于 /v1/* 接口）"""
    config = load_config()
    if not config:
        return {}, ""
    # 使用 access_token 或 session token
    token = config.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}"}, ""
    cookie = config.get("session_cookie", "")
    return {}, cookie


def _request(method, path, data=None, headers=None, timeout=DEFAULT_TIMEOUT, retries=MAX_RETRIES):
    """
    统一 HTTP 请求封装

    Args:
        method: GET/POST/PUT/DELETE
        path: API 路径（如 /api/channel/）
        data: 请求体（dict，自动转 JSON）
        headers: 额外请求头
        timeout: 超时秒数
        retries: 重试次数

    Returns:
        dict: 解析后的 JSON 响应

    Raises:
        Exception: 请求失败
    """
    base_url = get_base_url()
    if not base_url:
        return {"success": False, "message": "未配置 One API 服务，请先运行 service_manager.py save"}

    url = f"{base_url}{path}"

    req_headers = {"Content-Type": "application/json"}
    auth_headers, cookie = get_auth_header()
    req_headers.update(auth_headers)
    if cookie:
        req_headers["Cookie"] = cookie
    if headers:
        req_headers.update(headers)

    body = None
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")

    last_error = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                return resp_data
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
            except Exception:
                pass
            last_error = f"HTTP {e.code}: {error_body}"
            if e.code in (401, 403):
                # 认证失败，不重试
                return {"success": False, "message": f"认证失败: {last_error}"}
        except urllib.error.URLError as e:
            last_error = f"连接失败: {e.reason}"
        except Exception as e:
            last_error = f"请求异常: {str(e)}"

        if attempt < retries:
            time.sleep(1 * (attempt + 1))

    return {"success": False, "message": f"请求失败（重试{retries}次）: {last_error}"}


# ── 认证接口 ──────────────────────────────────────────────

def login(username, password):
    """登录 One API，保存 session/cookie 信息"""
    base_url = get_base_url()
    if not base_url:
        return {"success": False, "message": "未配置服务地址"}

    url = f"{base_url}/api/user/login"
    body = json.dumps({"username": username, "password": password}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            # 提取 session cookie
            cookies = resp.headers.get_all("Set-Cookie") or []
            session_cookie = ""
            for c in cookies:
                if "session" in c.lower():
                    session_cookie = c.split(";")[0]
                    break

            resp_data = json.loads(resp.read().decode("utf-8"))
            if resp_data.get("success"):
                # 保存登录信息
                config = load_config() or {}
                config["session_cookie"] = session_cookie
                if resp_data.get("data"):
                    config["user_id"] = resp_data["data"].get("id")
                    config["role"] = resp_data["data"].get("role")
                save_config(config)
            return resp_data
    except Exception as e:
        return {"success": False, "message": f"登录失败: {str(e)}"}


def get_access_token():
    """获取/刷新 AccessToken"""
    result = _request("GET", "/api/user/token")
    if result.get("success") and result.get("data"):
        config = load_config() or {}
        config["access_token"] = result["data"]
        save_config(config)
        return result
    return result


# ── 渠道接口 ──────────────────────────────────────────────

def list_channels(page=0, page_size=20):
    """列出渠道"""
    return _request("GET", f"/api/channel/?p={page}&page_size={page_size}")


def search_channels(keyword):
    """搜索渠道"""
    return _request("GET", f"/api/channel/search?keyword={urllib.parse.quote(keyword)}")


def get_channel(channel_id):
    """获取指定渠道"""
    return _request("GET", f"/api/channel/{channel_id}")


def add_channel(channel_data):
    """添加渠道"""
    return _request("POST", "/api/channel/", data=channel_data)


def update_channel(channel_data):
    """更新渠道"""
    return _request("PUT", "/api/channel/", data=channel_data)


def delete_channel(channel_id):
    """删除渠道"""
    return _request("DELETE", f"/api/channel/{channel_id}")


def test_channel(channel_id, model=None):
    """测试渠道"""
    path = f"/api/channel/test/{channel_id}"
    if model:
        path += f"?model={urllib.parse.quote(model)}"
    return _request("GET", path, timeout=60)


def test_all_channels(scope="all"):
    """测试所有渠道"""
    return _request("GET", f"/api/channel/test?scope={scope}", timeout=120)


def list_channel_models():
    """列出所有渠道类型及对应模型"""
    return _request("GET", "/api/channel/models")


def update_channel_balance(channel_id=None):
    """更新渠道余额"""
    if channel_id:
        return _request("GET", f"/api/channel/update_balance/{channel_id}")
    return _request("GET", "/api/channel/update_balance")


# ── 令牌接口 ──────────────────────────────────────────────

def list_tokens(page=0, page_size=20):
    """列出令牌"""
    return _request("GET", f"/api/token/?p={page}&page_size={page_size}")


def search_tokens(keyword):
    """搜索令牌"""
    return _request("GET", f"/api/token/search?keyword={urllib.parse.quote(keyword)}")


def get_token(token_id):
    """获取指定令牌"""
    return _request("GET", f"/api/token/{token_id}")


def add_token(token_data):
    """创建令牌"""
    return _request("POST", "/api/token/", data=token_data)


def update_token(token_data):
    """更新令牌"""
    return _request("PUT", "/api/token/", data=token_data)


def delete_token(token_id):
    """删除令牌"""
    return _request("DELETE", f"/api/token/{token_id}")


# ── 模型接口 ──────────────────────────────────────────────

def list_models():
    """列出可用模型（OpenAI 兼容格式）"""
    return _request("GET", "/v1/models")


def get_available_models():
    """获取用户可用模型"""
    return _request("GET", "/api/user/available_models")


# ── 计费接口 ──────────────────────────────────────────────

def get_subscription():
    """获取订阅/额度信息"""
    return _request("GET", "/dashboard/billing/subscription")


def get_usage(start_date=None, end_date=None):
    """获取用量"""
    path = "/dashboard/billing/usage"
    params = []
    if start_date:
        params.append(f"start_date={start_date}")
    if end_date:
        params.append(f"end_date={end_date}")
    if params:
        path += "?" + "&".join(params)
    return _request("GET", path)


# ── 日志接口 ──────────────────────────────────────────────

def get_logs(page=0, log_type=0, start_timestamp=0, end_timestamp=0, model_name="", token_name="", channel=0):
    """获取日志"""
    params = [f"p={page}", f"type={log_type}", f"start_timestamp={start_timestamp}", f"end_timestamp={end_timestamp}"]
    if model_name:
        params.append(f"model_name={urllib.parse.quote(model_name)}")
    if token_name:
        params.append(f"token_name={urllib.parse.quote(token_name)}")
    if channel:
        params.append(f"channel={channel}")
    return _request("GET", "/api/log/?" + "&".join(params))


def get_log_stat(log_type=2, start_timestamp=0, end_timestamp=0):
    """日志统计"""
    return _request("GET", f"/api/log/stat?type={log_type}&start_timestamp={start_timestamp}&end_timestamp={end_timestamp}")


# ── 系统接口 ──────────────────────────────────────────────

def get_status():
    """获取系统状态（无需认证）"""
    # 不使用 _request，因为可能没有配置
    config = load_config()
    if not config or not config.get("url"):
        # 尝试用传入的 URL
        return {"success": False, "message": "未配置服务地址"}
    url = f"{config['url'].rstrip('/')}/api/status"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


def get_options():
    """获取系统配置"""
    return _request("GET", "/api/option/")


def update_option(key, value):
    """更新系统配置"""
    return _request("PUT", "/api/option/", data={"key": key, "value": value})


# ── 用户接口 ──────────────────────────────────────────────

def get_self():
    """获取当前用户信息"""
    return _request("GET", "/api/user/self")


def get_user_dashboard():
    """获取用户仪表盘数据"""
    return _request("GET", "/api/user/dashboard")


# ── CLI 入口 ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="One API HTTP 客户端")
    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="获取系统状态")

    # login
    p_login = sub.add_parser("login", help="登录")
    p_login.add_argument("--username", required=True)
    p_login.add_argument("--password", required=True)

    # list-channels
    p_lc = sub.add_parser("list-channels", help="列出渠道")
    p_lc.add_argument("--page", type=int, default=0)

    # test-channel
    p_tc = sub.add_parser("test-channel", help="测试渠道")
    p_tc.add_argument("--id", type=int, required=True)
    p_tc.add_argument("--model", default=None)

    # list-tokens
    p_lt = sub.add_parser("list-tokens", help="列出令牌")
    p_lt.add_argument("--page", type=int, default=0)

    # list-models
    sub.add_parser("list-models", help="列出可用模型")

    # subscription
    sub.add_parser("subscription", help="获取额度信息")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    result = {}
    if args.command == "status":
        result = get_status()
    elif args.command == "login":
        result = login(args.username, args.password)
    elif args.command == "list-channels":
        result = list_channels(args.page)
    elif args.command == "test-channel":
        result = test_channel(args.id, args.model)
    elif args.command == "list-tokens":
        result = list_tokens(args.page)
    elif args.command == "list-models":
        result = list_models()
    elif args.command == "subscription":
        result = get_subscription()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
