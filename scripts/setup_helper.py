#!/usr/bin/env python3
"""
setup_helper.py — One API 部署引导
====================================
引导用户部署 One API 服务，提供 Docker 部署脚本和验证。
"""

import argparse
import json
import sys
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")


def get_deploy_scripts(server_ip="YOUR_SERVER_IP", mysql_password="123456",
                       mysql_port=13306, oneapi_port=4000):
    """
    生成部署脚本
    
    Args:
        server_ip: 服务器 IP
        mysql_password: MySQL root 密码
        mysql_port: MySQL 端口
        oneapi_port: One API 端口
    
    Returns:
        dict: 部署脚本和说明
    """
    mysql_script = f"""# 第一步：部署 MySQL 数据库
docker run --name oneapi-mysql -d --restart always \\
  -p {mysql_port}:3306 \\
  -e MYSQL_ROOT_PASSWORD={mysql_password} \\
  -e MYSQL_DATABASE=oneapi \\
  -v /home/ubuntu/data/mysql:/var/lib/mysql \\
  registry.cn-hangzhou.aliyuncs.com/xfg-studio/mysql:8.0

# 验证 MySQL 启动
docker logs oneapi-mysql

# ⚠️ 注意：需要在云服务器安全组/防火墙中开放 {mysql_port} 端口
# ⚠️ MySQL 默认只允许本地连接，需要配置远程访问权限
# 进入 MySQL 容器配置远程访问：
docker exec -it oneapi-mysql mysql -uroot -p{mysql_password} -e "GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION; FLUSH PRIVILEGES;"
"""

    oneapi_script = f"""# 第二步：部署 One API
docker run --name one-api -d --restart always \\
  -p {oneapi_port}:3000 \\
  -e SQL_DSN="root:{mysql_password}@tcp({server_ip}:{mysql_port})/oneapi" \\
  -e TZ=Asia/Shanghai \\
  -v /home/ubuntu/data/one-api:/data \\
  registry.cn-hangzhou.aliyuncs.com/xfg-studio/one-api:v0.6.10

# 验证 One API 启动
docker logs one-api

# ⚠️ 注意：需要在云服务器安全组/防火墙中开放 {oneapi_port} 端口
"""

    verify_script = f"""# 第三步：验证部署
# 检查服务状态
curl http://{server_ip}:{oneapi_port}/api/status

# 访问 Web 面板
# 浏览器打开: http://{server_ip}:{oneapi_port}
# 默认账户: root / 123456

# ⚠️ 登录后请立即修改默认密码！
"""

    return {
        "success": True,
        "data": {
            "server_ip": server_ip,
            "mysql_port": mysql_port,
            "oneapi_port": oneapi_port,
            "mysql_script": mysql_script.strip(),
            "oneapi_script": oneapi_script.strip(),
            "verify_script": verify_script.strip(),
            "security_notes": [
                f"开放云服务器安全组的 {mysql_port} 和 {oneapi_port} 端口",
                "登录 One API 后立即修改 root 默认密码",
                "MySQL 密码建议使用强密码",
                "生产环境建议配置 HTTPS"
            ]
        },
        "message": "部署脚本生成成功"
    }


def get_docker_compose(server_ip="YOUR_SERVER_IP", mysql_password="123456",
                       mysql_port=13306, oneapi_port=4000):
    """
    生成 docker-compose.yml
    
    Returns:
        dict: docker-compose 配置
    """
    compose = f"""version: '3'
services:
  mysql:
    image: registry.cn-hangzhou.aliyuncs.com/xfg-studio/mysql:8.0
    container_name: oneapi-mysql
    restart: always
    ports:
      - "{mysql_port}:3306"
    environment:
      MYSQL_ROOT_PASSWORD: {mysql_password}
      MYSQL_DATABASE: oneapi
    volumes:
      - /home/ubuntu/data/mysql:/var/lib/mysql

  one-api:
    image: registry.cn-hangzhou.aliyuncs.com/xfg-studio/one-api:v0.6.10
    container_name: one-api
    restart: always
    ports:
      - "{oneapi_port}:3000"
    environment:
      SQL_DSN: "root:{mysql_password}@tcp({server_ip}:{mysql_port})/oneapi"
      TZ: Asia/Shanghai
    volumes:
      - /home/ubuntu/data/one-api:/data
    depends_on:
      - mysql
"""
    return {
        "success": True,
        "data": {"docker_compose_yml": compose.strip()},
        "message": "docker-compose.yml 生成成功"
    }


def get_setup_guide():
    """获取完整部署指南"""
    return {
        "success": True,
        "data": {
            "title": "One API 部署指南",
            "prerequisites": [
                "一台云服务器（推荐 2核4G 以上）",
                "已安装 Docker 和 Docker Compose",
                "服务器安全组已开放所需端口"
            ],
            "options": [
                {
                    "name": "方案一：Docker Compose 一键部署（推荐）",
                    "steps": [
                        "1. 在服务器上创建 docker-compose.yml",
                        "2. 运行 docker-compose up -d",
                        "3. 等待服务启动（约30秒）",
                        "4. 访问 http://你的IP:4000",
                        "5. 用 root/123456 登录",
                        "6. 修改默认密码"
                    ]
                },
                {
                    "name": "方案二：分步 Docker 部署",
                    "steps": [
                        "1. 先部署 MySQL",
                        "2. 配置 MySQL 远程访问",
                        "3. 部署 One API",
                        "4. 验证并登录"
                    ]
                },
                {
                    "name": "方案三：连接已有服务",
                    "steps": [
                        "1. 提供已有的 One API 地址",
                        "2. 提供账户和密码",
                        "3. 验证连接"
                    ]
                }
            ],
            "next_steps": [
                "部署完成后，运行 service_manager.py save 配置连接",
                "运行 channel_manager.py add 添加渠道",
                "运行 token_manager.py distribute 获取 API Key"
            ]
        },
        "message": "部署指南获取成功"
    }


def main():
    parser = argparse.ArgumentParser(description="One API 部署引导")
    sub = parser.add_subparsers(dest="command")

    # deploy-scripts
    p_ds = sub.add_parser("deploy-scripts", help="生成部署脚本")
    p_ds.add_argument("--server-ip", default="YOUR_SERVER_IP")
    p_ds.add_argument("--mysql-password", default="123456")
    p_ds.add_argument("--mysql-port", type=int, default=13306)
    p_ds.add_argument("--oneapi-port", type=int, default=4000)

    # docker-compose
    p_dc = sub.add_parser("docker-compose", help="生成 docker-compose.yml")
    p_dc.add_argument("--server-ip", default="YOUR_SERVER_IP")
    p_dc.add_argument("--mysql-password", default="123456")
    p_dc.add_argument("--mysql-port", type=int, default=13306)
    p_dc.add_argument("--oneapi-port", type=int, default=4000)

    # guide
    sub.add_parser("guide", help="获取完整部署指南")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    result = {}
    if args.command == "deploy-scripts":
        result = get_deploy_scripts(args.server_ip, args.mysql_password, args.mysql_port, args.oneapi_port)
    elif args.command == "docker-compose":
        result = get_docker_compose(args.server_ip, args.mysql_password, args.mysql_port, args.oneapi_port)
    elif args.command == "guide":
        result = get_setup_guide()

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
