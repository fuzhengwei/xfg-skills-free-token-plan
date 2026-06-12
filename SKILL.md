---
name: xfg-skills-free-token-plan
description: |
  Free Token Plan — 基于 One API 的 AI 模型 API 自动化管理技能。
  触发词：给我来个key、apikey、给我点粮食、来点额度、给我个令牌、
  配置one-api、添加服务、连接服务、部署one-api、自部署、
  添加渠道、渠道列表、有哪些渠道、可用渠道、
  检测渠道、健康检查、渠道状态、
  可用模型、模型列表、auto-model、
  free-token-plan、token plan、免费token。
  当用户需要 API Key、管理 AI 模型渠道、查询可用模型、部署 One API 网关时触发。
license: Apache-2.0
metadata:
  author: xfg-studio
  version: "1.0.0"
  category: ai-gateway
  homepage: https://github.com/fuzhengwei/xfg-skills-free-token-plan
---

# Free Token Plan — AI 模型 API 自动化管理

基于 One API 的 AI 模型 API 统一网关管理，自动创建/分发 API Key，管理渠道，健康检查。

## 功能概述

1. **服务连接**：检测/配置 One API 服务，支持自部署引导
2. **渠道管理**：维护渠道注册表，一键添加渠道 + auto-model 映射
3. **Key 分发**：自动创建 API Key，返回完整连接信息（地址+模型+Key）
4. **健康检查**：定时检测渠道可用性，自动降级/通知

## 快速开始

### 首次使用

Skill 激活时自动检测 One API 配置：
- **无配置** → 引导配置（自部署 or 连接已有服务）
- **有配置但失效** → 提示重新配置
- **配置有效** → 直接使用

### 自部署 One API

```bash
# 1. 部署 MySQL
docker run --name oneapi-mysql -d --restart always \
  -p 13306:3306 \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -e MYSQL_DATABASE=oneapi \
  -v /home/ubuntu/data/mysql:/var/lib/mysql \
  registry.cn-hangzhou.aliyuncs.com/xfg-studio/mysql:8.0

# 2. 部署 One API
docker run --name one-api -d --restart always \
  -p 4000:3000 \
  -e SQL_DSN="root:123456@tcp(你的服务器IP:13306)/oneapi" \
  -e TZ=Asia/Shanghai \
  -v /home/ubuntu/data/one-api:/data \
  registry.cn-hangzhou.aliyuncs.com/xfg-studio/one-api:v0.6.10
```

部署后在 Web 面板 `http://你的IP:4000` 用 root/123456 登录。

### 连接已有服务

告诉 AI："配置 one-api，地址 http://xxx:4000，账户 root，密码 xxx"

## 核心功能

### 添加渠道

```
用户：添加 agnes 渠道，key 是 sk-xxx
→ 自动从注册表匹配渠道信息
→ 创建渠道 + auto-model 映射
→ 列出可用模型
```

查看可用渠道：`有哪些渠道可以用`

### 获取 API Key

```
用户：给我来个 key
→ 列出现有有效令牌 or 创建新令牌
→ 返回：地址 + API Key + 可用模型
```

触发词：给我来个key、apikey、给我点粮食、来点额度、给我个令牌

### 健康检查

```
用户：检测渠道
→ 测试所有渠道可用性
→ 报告状态 + 自动处理异常渠道
```

### auto-model 统一模型

每个渠道的每个模型自动映射为 `auto-{model}`：
- `gpt-4o` → `auto-gpt-4o`
- `deepseek-chat` → `auto-deepseek-chat`

使用 `auto-*` 模型时，One API 自动路由到可用渠道，无需关心底层。

## 模块路由

| 意图 | 执行脚本 |
|------|---------|
| 服务配置/连接 | `scripts/service_manager.py` |
| 渠道管理 | `scripts/channel_manager.py` |
| Key 分发 | `scripts/token_manager.py` |
| 健康检查 | `scripts/health_checker.py` |
| 部署引导 | `scripts/setup_helper.py` |
| auto-model | `scripts/auto_model.py` |

所有脚本通过 `scripts/oneapi_client.py` 与 One API 交互。

## 执行方式

```bash
# 所有脚本统一执行方式
python3 scripts/<module>.py <command> [options]

# 示例
python3 scripts/service_manager.py detect
python3 scripts/service_manager.py save --url http://81.70.245.73:4000 --username root --password 12345678
python3 scripts/channel_manager.py list-registry
python3 scripts/channel_manager.py add --name agnes --key sk-xxx
python3 scripts/token_manager.py create --name my-key --unlimited
python3 scripts/token_manager.py distribute
python3 scripts/health_checker.py check-all
python3 scripts/auto_model.py list
```

## 数据文件

| 文件 | 说明 |
|------|------|
| `data/service_config.json` | One API 服务连接配置（本地） |
| `data/channels.csv` | 渠道注册表（随 Skill 发布，社区可贡献） |

## Gotchas

1. **service_config.json 含密码**，不要在日志/对话中泄露
2. **API Key 创建后仅返回一次**，必须及时保存
3. **auto-model 映射在添加渠道时自动创建**，手动修改渠道后需重新同步
4. **健康检查依赖 cron**，首次使用需注册定时任务
5. **One API 默认 root 密码 123456**，生产环境务必修改
6. **渠道注册表是社区共享的**，提交 PR 即可添加新渠道
7. **MySQL 需要开放端口**供 One API 连接，注意防火墙规则

## 参考文档

- `references/architecture.md` — 完整架构设计
- `references/channel-registry.md` — 渠道注册表说明
- `references/oneapi-api-reference.md` — One API 接口参考
- `references/auto-model.md` — auto-model 映射详解
