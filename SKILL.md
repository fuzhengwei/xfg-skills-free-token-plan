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

**方式一：从注册表添加**（渠道名在注册表中存在时）

```
用户：添加 agnes 渠道，key 是 sk-xxx
→ 自动从注册表匹配渠道信息
→ 创建渠道 + auto-model 映射
→ 列出可用模型
```

**方式二：自定义参数添加**（用户提供 key/base_url/模型名，不依赖注册表）

```
用户：把 sk-xxx https://apihub.agnes-ai.com agnes-2.0-flash 配置到渠道里
→ 调用 add_custom_channel(name, channel_type, api_key, base_url, models_str)
→ 自动创建 auto-model 映射（如 auto-model → agnes-2.0-flash）
→ 返回渠道信息 + 可用模型
```

⚠️ **关键约束**：无论哪种方式添加渠道，**必须自动创建 auto-model 映射**，确保用户可以用 `auto-*` 模型名访问。

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
→ 健康渠道：按响应速度自动排优先级
  - ≤2s  → 优先级 10（极速）
  - ≤5s  → 优先级 5（快速）
  - ≤10s → 优先级 1（正常）
  - >10s → 优先级 0（慢速）
  - 同档位同优先级 → One API 自动负载均衡
→ 异常渠道：连续失败达阈值(默认2次) → 自动禁用
→ 之前被自动禁用的渠道恢复后 → 重新参与优先级排序
→ 手动禁用的渠道 → 跳过，不修改
→ 报告状态 + 优先级分布 + 操作结果
```

**自动优先级排序**：每次检测后根据响应速度自动排优先级，好用的自动排到前面，同档位的渠道共享优先级，One API 自动负载均衡。

**自动恢复机制**：渠道被自动禁用后，下次检查通过时自动恢复启用并参与优先级排序。

**连续失败阈值**：避免偶发超时误判，默认连续失败 2 次才禁用。

**检查历史持久化**：`data/health_history.json` 记录每个渠道的失败次数、禁用时间，重启后仍可恢复。

### auto-model 统一模型

每个渠道添加时自动将真实模型映射为固定名称 `auto-model`：
- 渠道有 `agnes-2.0-flash` → 映射 `auto-model → agnes-2.0-flash`
- 渠道有 `deepseek-chat` → 映射 `auto-model → deepseek-chat`

用户在 AI 工具中统一使用 `auto-model` 作为模型名，换渠道只需改映射，不用改工具配置。

多渠道同模型时，One API 自动负载均衡到可用渠道。

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
python3 scripts/health_checker.py check-all               # 检测 + 自动排优先级
python3 scripts/health_checker.py check-all --no-auto-fix     # 仅检测，不改优先级
python3 scripts/health_checker.py check-all --failures 3       # 连续失败3次才禁用
python3 scripts/health_checker.py history                     # 查看检查历史
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
4. **健康检查由用户手动触发**（检测渠道），每次检测自动排优先级
5. **One API 默认 root 密码 123456**，生产环境务必修改
6. **优先级自动排序**：检测时按响应速度分4档（极速/快速/正常/慢速），同档同优先级负载均衡
7. **检查历史持久化**：`data/health_history.json` 记录失败次数，重启后仍可恢复
8. **连续失败阈值**：默认2次，避免偶发超时误判，可通过 `--failures` 调整
9. **手动禁用(状态2)的渠道不会被检测或修改**，仅自动禁用(状态3)的渠道参与恢复
6. **渠道注册表是社区共享的**，提交 PR 即可添加新渠道
7. **MySQL 需要开放端口**供 One API 连接，注意防火墙规则

## 参考文档

- `references/architecture.md` — 完整架构设计
- `references/channel-registry.md` — 渠道注册表说明
- `references/oneapi-api-reference.md` — One API 接口参考
- `references/auto-model.md` — auto-model 映射详解
