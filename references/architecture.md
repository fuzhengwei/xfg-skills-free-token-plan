# xfg-skills-free-token-plan — 架构设计

## 一、项目定位

Free Token Plan — 基于 One API 的 AI 模型 API 自动化管理技能。
让用户（及智能体）无需手动操作 One API 面板，通过对话即可：
- 配置 One API 服务连接
- 管理渠道（添加/检测/负载均衡）
- 创建/分发 API Key
- 自动健康检查

## 二、分层架构

```
┌──────────────────────────────────────────────┐
│              SKILL.md (入口层)                │
│         触发识别 + 意图路由                    │
├──────────────────────────────────────────────┤
│          references/ (文档层)                  │
│  architecture.md | channel-registry.md       │
│  oneapi-api-reference.md | auto-model.md     │
├──────────────────────────────────────────────┤
│          scripts/ (执行层)                     │
│  oneapi_client.py    — One API HTTP 客户端    │
│  service_manager.py  — 服务连接管理           │
│  channel_manager.py  — 渠道管理 + 注册表      │
│  token_manager.py    — API Key 管理           │
│  health_checker.py   — 健康检查 + 定时任务    │
│  auto_model.py       — auto-model 映射逻辑    │
│  setup_helper.py     — 部署引导脚本           │
├──────────────────────────────────────────────┤
│          data/ (数据层)                        │
│  channels.csv        — 渠道注册表(随Skill发布) │
│  service_config.json — 本地服务连接配置       │
├──────────────────────────────────────────────┤
│          assets/ (模板层)                      │
│  docker-compose-template.yml                 │
│  mysql-docker-template.yml                   │
└──────────────────────────────────────────────┘
```

## 三、核心模块设计

### 3.1 service_manager.py — 服务连接管理

职责：管理 One API 服务实例的连接信息（URL/账户/密码/session）

**核心功能**：
- `detect()` — 检测本地是否已有可用的 One API 配置
- `save_config(url, username, password)` — 保存服务连接配置
- `load_config()` — 加载已保存的配置
- `login()` — 登录获取 session / access_token
- `check_connection()` — 验证连接是否可用
- `get_token()` — 获取有效的认证 token（自动刷新）

**配置文件** `data/service_config.json`：
```json
{
  "url": "http://81.70.245.73:4000",
  "username": "root",
  "password": "12345678",
  "access_token": "xxx",
  "token_expires": 0,
  "user_id": 1,
  "role": 100
}
```

**流程**：
1. Skill 激活时调用 `detect()`
2. 无配置 → 提示用户添加（提供自部署脚本）
3. 有配置 → `check_connection()` 验证
4. 失效 → 提示重新配置
5. 成功 → `login()` 获取 token，后续操作使用此 token

### 3.2 oneapi_client.py — HTTP 客户端

职责：封装 One API 的所有 HTTP 接口调用

**设计原则**：
- 统一的错误处理和重试
- 自动注入认证头
- 响应统一解析

**核心方法**（按接口分组）：

| 分组 | 方法 | 说明 |
|------|------|------|
| 认证 | `login(username, password)` | 登录 |
| 认证 | `get_access_token()` | 获取 AccessToken |
| 渠道 | `list_channels(page)` | 列出渠道 |
| 渠道 | `add_channel(data)` | 添加渠道 |
| 渠道 | `update_channel(data)` | 更新渠道 |
| 渠道 | `delete_channel(id)` | 删除渠道 |
| 渠道 | `test_channel(id, model)` | 测试渠道 |
| 渠道 | `test_all_channels()` | 测试所有渠道 |
| 渠道 | `list_channel_models()` | 列出渠道类型模型 |
| 令牌 | `list_tokens(page)` | 列出令牌 |
| 令牌 | `add_token(data)` | 创建令牌 |
| 令牌 | `update_token(data)` | 更新令牌 |
| 令牌 | `delete_token(id)` | 删除令牌 |
| 模型 | `list_models()` | 列出可用模型 |
| 模型 | `get_available_models()` | 用户可用模型 |
| 计费 | `get_subscription()` | 获取额度信息 |
| 计费 | `get_usage()` | 获取用量 |
| 日志 | `get_logs(params)` | 获取日志 |
| 日志 | `get_log_stat(params)` | 日志统计 |
| 系统 | `get_status()` | 系统状态 |
| 系统 | `get_options()` | 系统配置 |
| 系统 | `update_option(key, value)` | 更新配置 |

### 3.3 channel_manager.py — 渠道管理 + 注册表

职责：
1. 维护 `data/channels.csv` 渠道注册表（随 Skill 发布，社区可贡献）
2. 基于注册表引导用户添加渠道到 One API
3. auto-model 映射：为每个渠道的每个模型额外映射一个 `auto-{model}` 模型

**渠道注册表** `data/channels.csv`：
```csv
name,type,base_url,models,description,api_key_url,doc_url
agnes,1,https://api.agnes-ai.com,gpt-4o,gpt-4o-mini,Agnes AI 平台,https://platform.agnes-ai.com/settings/apiKeys,
deepseek,37,https://api.deepseek.com,deepseek-chat,deepseek-reasoner,DeepSeek 官方,https://platform.deepseek.com/api_keys,
siliconflow,41,https://api.siliconflow.cn,Qwen/Qwen2.5-72B-Instruct,硅基流动,https://cloud.siliconflow.cn/account/ak,
```

**核心功能**：
- `list_registry()` — 列出注册表中所有可用渠道
- `add_to_oneapi(channel_name, api_key)` — 将注册表中的渠道添加到 One API
- `sync_auto_models(channel_id)` — 为渠道的每个模型添加 auto-model 映射
- `search_registry(keyword)` — 搜索注册表
- `add_to_registry(entry)` — 添加新渠道到注册表（供社区贡献）

**auto-model 映射逻辑**：
当用户使用 `auto-gpt-4o` 时，One API 的 model_mapping 会将其映射到实际的 `gpt-4o`。
这样用户只需知道 `auto-*` 前缀模型，One API 负责路由到可用渠道。

### 3.4 token_manager.py — API Key 管理

职责：创建、查询、分发 API Key

**核心功能**：
- `create_token(name, quota, expired_time, models, unlimited)` — 创建令牌
- `list_tokens(status)` — 列出令牌
- `get_valid_token()` — 获取一个有效令牌
- `revoke_token(id)` — 撤销令牌
- `distribute_key()` — 生成完整的连接信息（地址+模型+key）

**distribute_key() 返回格式**：
```json
{
  "base_url": "http://81.70.245.73:4000",
  "api_key": "sk-xxxx",
  "models": ["auto-gpt-4o", "auto-deepseek-chat", ...],
  "expired_time": -1,
  "remain_quota": 500000,
  "unlimited_quota": true
}
```

**触发词**：给我来个key、apikey、给我点粮食、来点额度、给我个令牌

### 3.5 health_checker.py — 健康检查

职责：定期检测渠道和令牌状态

**核心功能**：
- `check_channel_health(channel_id)` — 检测单个渠道
- `check_all_channels()` — 检测所有渠道
- `check_token_status(token_id)` — 检测令牌状态
- `get_channel_stats()` — 渠道统计（成功率、响应时间）
- `schedule_check(interval_minutes)` — 注册定时检查（cron）

**检查逻辑**：
1. 调用 `/api/channel/test/:id` 测试渠道
2. 检查令牌 `status` + `remain_quota` + `expired_time`
3. 失败渠道：降低优先级或禁用
4. 结果写入日志

**与 cron 集成**：
- 使用 OpenClaw cron 定时触发健康检查
- 默认每 6 小时一次
- 可自定义间隔

### 3.6 auto_model.py — auto-model 映射

职责：为每个模型生成 `auto-{model}` 映射，实现统一入口

**映射规则**：
- 原始模型：`gpt-4o`, `deepseek-chat`
- 映射模型：`auto-gpt-4o`, `auto-deepseek-chat`
- model_mapping JSON：`{"auto-gpt-4o": "gpt-4o", "auto-deepseek-chat": "deepseek-chat"}`

**实现方式**：
在添加渠道时，自动将 `auto-*` 模型加入 `models` 字段，并在 `model_mapping` 中添加映射关系。
这样用户请求 `auto-gpt-4o` 时，One API 会路由到有 `gpt-4o` 的渠道。

### 3.7 setup_helper.py — 部署引导

职责：引导用户部署 One API 服务

**提供两种方案**：

**方案一：自部署（推荐）**
1. 提供 MySQL Docker 部署脚本
2. 提供 One API Docker 部署脚本
3. 验证部署结果

**方案二：使用已有服务**
1. 输入服务地址
2. 输入账户密码
3. 验证连接

## 四、数据流

### 4.1 首次使用流程
```
用户激活 Skill
  → service_manager.detect()
  → 无配置 → 提示选择（自部署/已有服务）
  → 自部署 → setup_helper 引导
  → 已有服务 → 输入地址+账户密码
  → service_manager.save_config() + login()
  → 成功 → 进入主功能
```

### 4.2 添加渠道流程
```
用户：添加 agnes 渠道
  → channel_manager.search_registry("agnes")
  → 展示注册表中的 agnes 信息
  → 用户提供 api_key
  → channel_manager.add_to_oneapi("agnes", api_key)
  → auto_model.sync_auto_models(channel_id)
  → 渠道创建完成 + auto-model 映射完成
```

### 4.3 分发 Key 流程
```
用户：给我来个 key
  → token_manager.list_tokens(status=1)
  → 有有效令牌 → 展示，询问是否使用或创建新的
  → 无有效令牌 / 用户要求新建
  → token_manager.create_token(...)
  → token_manager.distribute_key()
  → 返回完整的连接信息
```

### 4.4 健康检查流程
```
cron 触发 / 用户手动触发
  → health_checker.check_all_channels()
  → 遍历渠道，调用 /api/channel/test/:id
  → 失败渠道：更新优先级/禁用
  → 生成报告
  → 异常时通知用户
```

## 五、Skill 触发词设计

| 触发词 | 路由到 | 说明 |
|--------|--------|------|
| 配置one-api/添加服务/连接服务 | service_manager | 服务连接管理 |
| 部署one-api/自部署 | setup_helper | 部署引导 |
| 添加渠道/渠道列表/有哪些渠道 | channel_manager | 渠道管理 |
| 给我key/apikey/来点粮食/给个令牌 | token_manager | Key 分发 |
| 检测渠道/健康检查/渠道状态 | health_checker | 健康检查 |
| 可用模型/模型列表 | auto_model | 模型查询 |

## 六、扩展性设计

1. **多实例支持**：service_config.json 支持数组，管理多个 One API 实例
2. **渠道注册表社区化**：channels.csv 随 Skill 提交到 GitHub，PR 即可贡献新渠道
3. **auto-model 统一入口**：所有模型通过 `auto-*` 前缀统一访问，用户无需关心底层渠道
4. **健康检查可配置**：检查间隔、通知方式、自动修复策略均可配置
5. **插件化渠道类型**：注册表新增渠道只需添加 CSV 行，无需改代码
