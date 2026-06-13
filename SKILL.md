---
name: xfg-skills-free-token-plan
description: |
  Free Token Plan — 基于 One API 的 AI 模型 API 自动化管理技能。
  触发词：给我来个key、apikey、给我点粮食、来点额度、给我个令牌、
  配置one-api、添加服务、连接服务、部署one-api、自部署、
  添加渠道、渠道列表、有哪些渠道、可用渠道、
  检测渠道、测试渠道、验证渠道、健康检查、渠道状态、
  可用模型、模型列表、auto-model、
  free-token-plan、token plan、免费token。
  帮助、help、能做什么、你会什么、有什么功能、使用说明、怎么用。
  当用户需要 API Key、管理 AI 模型渠道、查询可用模型、部署 One API 网关时触发。
  当用户输入 help/帮助/能做什么 时，输出帮助说明。
license: Apache-2.0
metadata:
  author: xfg-studio
  version: "1.0.0"
  category: ai-gateway
  homepage: https://github.com/fuzhengwei/xfg-skills-free-token-plan
---

# Free Token Plan — AI 模型 API 自动化管理

基于 One API 的 AI 模型 API 统一网关管理，自动创建/分发 API Key，管理渠道，健康检查。

## 帮助说明

当用户输入 **help / 帮助 / 能做什么 / 你会什么 / 怎么用** 时，输出以下内容：

---

**🛠 Free Token Plan — 你可以让我做这些事：**

**1️⃣ 获取 API Key**
> 「给我来个 key」「apikey」「来点额度」「给我个令牌」
> 自动创建或复用 API Key，返回地址 + Key + 可用模型，直接可用。

**2️⃣ 添加渠道**
> 「添加 agnes 渠道，key 是 sk-xxx」
> 「把 sk-xxx https://api.xxx.com model-name 配置到渠道里」
> 一键添加模型渠道，自动创建 auto-model 映射，换渠道不用改配置。

**3️⃣ 查看渠道**
> 「有哪些渠道」「渠道列表」
> 查看所有已配置渠道及其状态。

**4️⃣ 验证渠道**
> 「检查渠道」「测试渠道」「验证渠道」
> 测试所有渠道可用性，不可用的自动降级（优先级→1），下次验证可用后自动恢复（优先级→10）。所有渠道统一优先级10，负载均衡。

**5️⃣ 查看可用模型**
> 「可用模型」「模型列表」
> 列出当前可用的所有模型名称。

**6️⃣ 配置服务**
> 「配置 one-api」「连接服务」
> 设置 One API 服务地址和账户，或引导自部署。

**💡 小贴士：** 所有渠道自动映射 `auto-model`，你在 AI 工具里统一用 `auto-model` 作为模型名，换渠道只改映射，不用改工具配置。

---

## 功能概述

1. **服务连接**：检测/配置 One API 服务，支持自部署引导
2. **渠道管理**：维护渠道注册表，一键添加渠道 + auto-model 映射
3. **Key 分发**：自动创建 API Key，返回完整连接信息（地址+模型+Key）
4. **渠道验证**：手动触发验证渠道可用性，不可用自动降级，验证可用后自动恢复

## 快速开始

### 首次使用

Skill 激活时自动检测 One API 配置：
- **无配置** → 引导配置（自部署 or 连接已有服务）
- **有配置但失效** → 提示重新配置
- **配置有效** → 直接使用

### 自部署 One API

```bash
# 使用 docker-compose 一键部署（推荐）
# 将下方内容保存为 docker-compose.yml 后运行: docker-compose up -d
version: '3'
services:
  mysql:
    image: registry.cn-hangzhou.aliyuncs.com/xfg-studio/mysql:8.0
    container_name: oneapi-mysql
    restart: always
    ports:
      - "13306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: 12345678
      MYSQL_DATABASE: oneapi
    volumes:
      - /home/ubuntu/data/mysql:/var/lib/mysql
    networks:
      - oneapi-net

  one-api:
    image: registry.cn-hangzhou.aliyuncs.com/xfg-studio/one-api:v0.6.11
    container_name: one-api
    restart: always
    ports:
      - "4000:3000"
    environment:
      SQL_DSN: "root:12345678@tcp(mysql:3306)/oneapi"
      TZ: Asia/Shanghai
    volumes:
      - /home/ubuntu/data/one-api:/data
    depends_on:
      - mysql
    networks:
      - oneapi-net

networks:
  oneapi-net:
    driver: bridge
```

部署后在 Web 面板 `http://你的IP:4000` 用 root/12345678 登录。

> **提示**: 同一 docker-compose 下的容器通过 `mysql:3306` 内网通信，无需配置服务器 IP。`13306` 端口映射仅用于外部调试。

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

### 渠道验证

```
用户：检查渠道 / 测试渠道 / 验证渠道
→ 测试所有渠道可用性
→ 可用渠道：优先级 10（统一负载均衡）
→ 不可用渠道：降级为优先级 1（保留，不删除）
→ 之前降级的渠道验证可用后：恢复优先级 10
→ 手动禁用的渠道 → 跳过，不修改
→ 报告状态 + 降级/恢复操作
```

**统一负载均衡**：所有渠道默认优先级 10，One API 自动在同优先级渠道间负载均衡。

**降级机制**：渠道验证不可用时，优先级降为 1，不再参与负载均衡，但渠道仍然保留。

**自动恢复**：之前降级的渠道，下次验证可用后，优先级自动恢复为 10，重新参与负载均衡。

**手动禁用(状态2)的渠道**：跳过，不修改。

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
python3 scripts/health_checker.py check-all               # 验证 + 自动降级/恢复
python3 scripts/health_checker.py check-all --no-auto-fix     # 仅验证，不降级/恢复
python3 scripts/health_checker.py history                     # 查看验证历史
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
4. **渠道验证由用户手动触发**（检查渠道/测试渠道/验证渠道），不可用自动降级，可用自动恢复
5. **One API 默认 root 密码 12345678**，生产环境务必修改
6. **统一优先级10负载均衡**：所有渠道默认优先级10，不可用降级为1，验证可用后恢复为10
7. **检查历史持久化**：`data/health_history.json` 记录降级状态，重启后仍可恢复
8. **手动禁用(状态2)的渠道不会被检测或修改**，仅降级的渠道参与恢复
9. **渠道注册表是社区共享的**，提交 PR 即可添加新渠道
10. **MySQL 需要开放端口**供 One API 连接，注意防火墙规则

## 参考文档

- `references/architecture.md` — 完整架构设计
- `references/channel-registry.md` — 渠道注册表说明
- `references/oneapi-api-reference.md` — One API 接口参考
- `references/auto-model.md` — auto-model 映射详解
