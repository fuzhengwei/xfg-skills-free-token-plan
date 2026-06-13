# One API — HTTP 接口全览

> 源码: `/Users/fuzhengwei/DevOps/skills/xfg-skills-free-token-plan/one-api/`
> 默认端口: 3000 | 基础URL: `http://localhost:3000`

---

## 一、公共信息接口（无需认证）

| 方法 | 路径 | 说明 | 控制器 |
|------|------|------|--------|
| GET | `/api/status` | 系统状态（版本、OAuth配置、系统名称等） | `GetStatus` |
| GET | `/api/notice` | 系统公告 | `GetNotice` |
| GET | `/api/about` | 关于页内容 | `GetAbout` |
| GET | `/api/home_page_content` | 首页内容 | `GetHomePageContent` |

### GET /api/status 响应示例
```json
{
  "success": true,
  "message": "",
  "data": {
    "version": "v0.x.x",
    "start_time": 1700000000,
    "email_verification": false,
    "github_oauth": true,
    "github_client_id": "xxx",
    "lark_client_id": "",
    "system_name": "One API",
    "logo": "",
    "footer_html": "",
    "wechat_qrcode": "",
    "wechat_login": false,
    "server_address": "http://localhost:3000",
    "turnstile_check": false,
    "turnstile_site_key": "",
    "top_up_link": "",
    "chat_link": "",
    "quota_per_unit": 500000,
    "display_in_currency": true,
    "oidc": false,
    "oidc_client_id": "",
    "oidc_well_known": "",
    "oidc_authorization_endpoint": "",
    "oidc_token_endpoint": "",
    "oidc_userinfo_endpoint": ""
  }
}
```

---

## 二、认证接口

| 方法 | 路径 | 说明 | 认证 | 控制器 |
|------|------|------|------|--------|
| POST | `/api/user/register` | 用户注册 | CriticalRateLimit + TurnstileCheck | `Register` |
| POST | `/api/user/login` | 用户登录 | CriticalRateLimit | `Login` |
| GET | `/api/user/logout` | 用户登出 | — | `Logout` |
| GET | `/api/oauth/github` | GitHub OAuth | CriticalRateLimit | `GitHubOAuth` |
| GET | `/api/oauth/oidc` | OIDC OAuth | CriticalRateLimit | `OidcAuth` |
| GET | `/api/oauth/lark` | 飞书 OAuth | CriticalRateLimit | `LarkOAuth` |
| GET | `/api/oauth/state` | 生成OAuth状态码 | CriticalRateLimit | `GenerateOAuthCode` |
| GET | `/api/oauth/wechat` | 微信扫码登录 | CriticalRateLimit | `WeChatAuth` |
| GET | `/api/oauth/wechat/bind` | 微信绑定 | CriticalRateLimit + UserAuth | `WeChatBind` |
| GET | `/api/oauth/email/bind` | 邮箱绑定 | CriticalRateLimit + UserAuth | `EmailBind` |
| GET | `/api/verification` | 发送邮箱验证码 | CriticalRateLimit + TurnstileCheck | `SendEmailVerification` |
| GET | `/api/reset_password` | 发送密码重置邮件 | CriticalRateLimit + TurnstileCheck | `SendPasswordResetEmail` |
| POST | `/api/user/reset` | 重置密码 | CriticalRateLimit | `ResetPassword` |

### POST /api/user/login
**请求体**:
```json
{ "username": "root", "password": "12345678" }
```
**响应**:
```json
{ "success": true, "message": "", "data": { "id": 1, "username": "root", "display_name": "Root", "role": 100, "status": 1 } }
```

### POST /api/user/register
**请求体**:
```json
{ "username": "newuser", "password": "password123", "email": "user@example.com", "verification_code": "123456", "aff_code": "ABCD" }
```

### GET /api/verification?email=xxx
发送6位数字验证码到邮箱。

### GET /api/reset_password?email=xxx
发送密码重置链接到邮箱。

### POST /api/user/reset
```json
{ "email": "user@example.com", "token": "reset-token-from-email" }
```
响应中 `data` 为新生成的密码。

### GET /api/oauth/email/bind?email=xxx&code=123456
绑定邮箱，需邮箱验证码。

---

## 三、用户管理接口

### 3.1 自助接口（UserAuth — 普通用户可访问）

| 方法 | 路径 | 说明 | 控制器 |
|------|------|------|--------|
| GET | `/api/user/dashboard` | 用户仪表盘数据（7天用量按日/模型统计） | `GetUserDashboard` |
| GET | `/api/user/self` | 获取当前用户信息 | `GetSelf` |
| PUT | `/api/user/self` | 更新当前用户信息 | `UpdateSelf` |
| DELETE | `/api/user/self` | 删除当前用户 | `DeleteSelf` |
| GET | `/api/user/token` | 生成/获取 Access Token | `GenerateAccessToken` |
| GET | `/api/user/aff` | 获取邀请码 | `GetAffCode` |
| POST | `/api/user/topup` | 兑换码充值 | `TopUp` |
| GET | `/api/user/available_models` | 获取当前用户可用模型列表 | `GetUserAvailableModels` |

### PUT /api/user/self
```json
{ "username": "newname", "password": "newpass", "display_name": "New Display" }
```

### POST /api/user/topup
```json
{ "key": " redemption-code" }
```
响应 `data` 为充值的额度值。

### 3.2 管理接口（AdminAuth — 管理员可访问）

| 方法 | 路径 | 说明 | 控制器 |
|------|------|------|--------|
| GET | `/api/user/?p=0` | 获取所有用户（分页） | `GetAllUsers` |
| GET | `/api/user/search?keyword=xxx` | 搜索用户 | `SearchUsers` |
| GET | `/api/user/:id` | 获取指定用户 | `GetUser` |
| POST | `/api/user/` | 创建用户 | `CreateUser` |
| PUT | `/api/user/` | 更新用户 | `UpdateUser` |
| DELETE | `/api/user/:id` | 删除用户 | `DeleteUser` |
| POST | `/api/user/manage` | 管理用户（禁用/启用/删除/提升/降级） | `ManageUser` |
| POST | `/api/topup` | 管理员直接充值 | `AdminTopUp` |

### GET /api/user/?p=0&order=quota
- `p`: 页码（0开始）
- `order`: 排序字段（如 quota, used_quota, request_count）

### POST /api/user/ — 创建用户
```json
{ "username": "newuser", "password": "pass123", "display_name": "New User" }
```

### PUT /api/user/ — 更新用户
```json
{ "id": 2, "username": "updated", "display_name": "Updated", "role": 1, "status": 1, "quota": 500000, "group": "default" }
```

### POST /api/user/manage — 管理操作
```json
{ "username": "targetuser", "action": "disable" }
```
`action` 可选值: `disable` | `enable` | `delete` | `promote` | `demote`

### POST /api/topup — 管理员充值
```json
{ "user_id": 2, "quota": 500000, "remark": "手动充值" }
```

---

## 四、渠道管理接口（AdminAuth）

| 方法 | 路径 | 说明 | 控制器 |
|------|------|------|--------|
| GET | `/api/channel/?p=0` | 获取所有渠道（分页） | `GetAllChannels` |
| GET | `/api/channel/search?keyword=xxx` | 搜索渠道 | `SearchChannels` |
| GET | `/api/channel/models` | 列出所有渠道类型及对应模型 | `ListAllModels` |
| GET | `/api/channel/:id` | 获取指定渠道 | `GetChannel` |
| GET | `/api/channel/test` | 测试所有渠道 | `TestChannels` |
| GET | `/api/channel/test/:id` | 测试指定渠道 | `TestChannel` |
| GET | `/api/channel/test/:id?model=xxx` | 测试指定渠道（指定模型） | `TestChannel` |
| GET | `/api/channel/update_balance` | 更新所有渠道余额（OpenAI/Custom类型） | `UpdateAllChannelsBalance` |
| GET | `/api/channel/update_balance/:id` | 更新指定渠道余额 | `UpdateChannelBalance` |
| POST | `/api/channel/` | 添加渠道 | `AddChannel` |
| PUT | `/api/channel/` | 更新渠道 | `UpdateChannel` |
| DELETE | `/api/channel/:id` | 删除渠道 | `DeleteChannel` |
| DELETE | `/api/channel/disabled` | 删除所有已禁用渠道 | `DeleteDisabledChannel` |

### POST /api/channel/ — 添加渠道
```json
{
  "type": 1,
  "key": "sk-xxxxx\nsk-yyyyy",
  "name": "OpenAI Channel",
  "base_url": "https://api.openai.com",
  "models": "gpt-4,gpt-4o,gpt-3.5-turbo",
  "group": "default",
  "model_mapping": "{\"gpt-4\": \"gpt-4-0613\"}",
  "priority": 0,
  "weight": 1,
  "config": "{}",
  "system_prompt": ""
}
```
> `key` 支持换行分隔，一行一个 key，自动拆分为多个渠道

### GET /api/channel/test/:id?model=xxx
**参数**:
- `model`: 指定测试模型（可选，默认取渠道第一个可用模型）

**成功响应**:
```json
{ "success": true, "message": "Hello!", "time": 1.234, "modelName": "gpt-3.5-turbo" }
```
**失败响应**:
```json
{ "success": false, "message": "error description", "time": 0, "modelName": "gpt-3.5-turbo" }
```

### GET /api/channel/test?scope=all
**参数**:
- `scope`: 测试范围 — `all`（默认）| `disabled` | `enabled`

异步执行，立即返回。测试结果通过邮件/消息推送通知。测试逻辑：
1. 对每个渠道发送 `POST /v1/chat/completions` 测试请求
2. 响应时间超过 `ChannelDisableThreshold` 秒 → 自动禁用
3. 返回 OpenAI 错误码（401/403/429等）→ 自动禁用
4. 已禁用渠道测试成功 → 自动重新启用

### GET /api/channel/models
列出所有渠道类型→模型映射（**无额外认证**，仅需 AdminAuth）
**响应**:
```json
{ "success": true, "message": "", "data": { "1": ["gpt-4", "gpt-3.5-turbo", ...], "13": ["claude-3-opus", ...] } }
```
key 为渠道类型ID，value 为该类型支持的模型名列表。

---

## 五、令牌管理接口（UserAuth）

| 方法 | 路径 | 说明 | 控制器 |
|------|------|------|--------|
| GET | `/api/token/?p=0&order=used_quota` | 获取当前用户所有令牌 | `GetAllTokens` |
| GET | `/api/token/search?keyword=xxx` | 搜索令牌 | `SearchTokens` |
| GET | `/api/token/:id` | 获取指定令牌 | `GetToken` |
| POST | `/api/token/` | 创建令牌 | `AddToken` |
| PUT | `/api/token/?status_only=1` | 更新令牌 | `UpdateToken` |
| DELETE | `/api/token/:id` | 删除令牌 | `DeleteToken` |

### POST /api/token/ — 创建令牌
```json
{
  "name": "my-token",
  "remain_quota": 500000,
  "unlimited_quota": false,
  "expired_time": -1,
  "models": "gpt-4,gpt-3.5-turbo",
  "subnet": "192.168.1.0/24"
}
```
**响应** 中 `data.key` 为生成的令牌 key（格式 `sk-XXXX`），**仅此一次返回**。

> `expired_time`: -1=永不过期, 0=已过期, >0=Unix时间戳
> `unlimited_quota`: true=无限额度
> `models`: 空=不限制, 逗号分隔模型名=限制可用模型
> `subnet`: 空=不限制, CIDR格式=限制IP网段

### PUT /api/token/ — 更新令牌
```json
{ "id": 1, "name": "updated-name", "status": 1, "remain_quota": 1000000, "expired_time": -1, "unlimited_quota": false, "models": "", "subnet": "" }
```
- `status_only` 参数: 非空时仅更新 status 字段

**令牌状态**: 1=已启用, 2=已禁用, 3=已过期, 4=已耗尽

---

## 六、日志接口

| 方法 | 路径 | 说明 | 认证 | 控制器 |
|------|------|------|------|--------|
| GET | `/api/log/?p=0&type=2&start_timestamp=0&end_timestamp=0&model_name=&username=&token_name=&channel=0` | 获取所有日志 | AdminAuth | `GetAllLogs` |
| GET | `/api/log/search?keyword=xxx` | 搜索所有日志 | AdminAuth | `SearchAllLogs` |
| GET | `/api/log/stat?type=2&start_timestamp=0&end_timestamp=0` | 日志统计（总消耗额度） | AdminAuth | `GetLogsStat` |
| DELETE | `/api/log/?target_timestamp=1700000000` | 删除历史日志（早于指定时间） | AdminAuth | `DeleteHistoryLogs` |
| GET | `/api/log/self?p=0&type=2&start_timestamp=0&end_timestamp=0&model_name=&token_name=` | 获取当前用户日志 | UserAuth | `GetUserLogs` |
| GET | `/api/log/self/search?keyword=xxx` | 搜索当前用户日志 | UserAuth | `SearchUserLogs` |
| GET | `/api/log/self/stat?type=2&start_timestamp=0&end_timestamp=0` | 当前用户日志统计 | UserAuth | `GetLogsSelfStat` |

### 日志查询参数
| 参数 | 类型 | 说明 |
|------|------|------|
| `p` | int | 页码（0开始） |
| `type` | int | 日志类型（1=充值, 2=消耗, 3=管理） |
| `start_timestamp` | int64 | 起始时间Unix时间戳 |
| `end_timestamp` | int64 | 结束时间Unix时间戳 |
| `model_name` | string | 模型名过滤 |
| `username` | string | 用户名过滤 |
| `token_name` | string | 令牌名过滤 |
| `channel` | int | 渠道ID过滤 |
| `keyword` | string | 关键词搜索 |

### 日志统计响应
```json
{ "success": true, "message": "", "data": { "quota": 12345 } }
```

---

## 七、兑换码接口（AdminAuth）

| 方法 | 路径 | 说明 | 控制器 |
|------|------|------|--------|
| GET | `/api/redemption/?p=0` | 获取所有兑换码 | `GetAllRedemptions` |
| GET | `/api/redemption/search?keyword=xxx` | 搜索兑换码 | `SearchRedemptions` |
| GET | `/api/redemption/:id` | 获取指定兑换码 | `GetRedemption` |
| POST | `/api/redemption/` | 创建兑换码 | `AddRedemption` |
| PUT | `/api/redemption/?status_only=1` | 更新兑换码 | `UpdateRedemption` |
| DELETE | `/api/redemption/:id` | 删除兑换码 | `DeleteRedemption` |

### POST /api/redemption/ — 创建兑换码
```json
{ "name": "活动兑换码", "quota": 500000, "count": 10 }
```
- `count`: 批量生成个数（1-100）
- 响应 `data` 为生成的 key 数组

---

## 八、系统配置接口（RootAuth — 仅超级管理员）

| 方法 | 路径 | 说明 | 控制器 |
|------|------|------|--------|
| GET | `/api/option/` | 获取所有配置项 | `GetOptions` |
| PUT | `/api/option/` | 更新配置项 | `UpdateOption` |

### PUT /api/option/
```json
{ "key": "Theme", "value": "berry" }
```
**常见配置项**:
| Key | 说明 |
|-----|------|
| `Theme` | 主题（default/berry/air） |
| `SystemName` | 系统名称 |
| `Logo` | Logo URL |
| `Footer` | 页脚HTML |
| `Notice` | 系统公告 |
| `About` | 关于页内容 |
| `HomePageContent` | 首页内容 |
| `ServerAddress` | 服务器地址 |
| `TopUpLink` | 充值链接 |
| `ChatLink` | 聊天链接 |
| `QuotaPerUnit` | 每单位额度（默认500000=$1） |
| `DisplayInCurrencyEnabled` | 是否以货币显示额度 |
| `DisplayTokenStatEnabled` | 是否显示令牌统计 |
| `RegisterEnabled` | 是否开放注册 |
| `PasswordLoginEnabled` | 是否允许密码登录 |
| `PasswordRegisterEnabled` | 是否允许密码注册 |
| `EmailVerificationEnabled` | 是否启用邮箱验证 |
| `GitHubOAuthEnabled` | 是否启用GitHub OAuth |
| `WeChatAuthEnabled` | 是否启用微信登录 |
| `TurnstileCheckEnabled` | 是否启用Turnstile验证 |
| `EmailDomainRestrictionEnabled` | 是否启用邮箱域名白名单 |
| `AutomaticDisableChannelEnabled` | 是否自动禁用失败渠道 |
| `ChannelDisableThreshold` | 渠道自动禁用阈值（秒） |
| `RetryTimes` | 重试次数 |

> Token/Secret 后缀的配置项（如 `GitHubClientSecret`）GET时不出现在响应中

---

## 九、分组接口（AdminAuth）

| 方法 | 路径 | 说明 | 控制器 |
|------|------|------|--------|
| GET | `/api/group/` | 获取所有分组名称 | `GetGroups` |

响应为分组名数组：`["default", "vip", "premium"]`

---

## 十、模型接口

| 方法 | 路径 | 说明 | 认证 | 控制器 |
|------|------|------|------|--------|
| GET | `/api/models` | 管理面板：所有渠道类型→模型映射 | UserAuth | `DashboardListModels` |
| GET | `/v1/models` | OpenAI兼容：当前令牌可用模型列表 | TokenAuth | `ListModels` |
| GET | `/v1/models/:model` | OpenAI兼容：获取指定模型信息 | TokenAuth | `RetrieveModel` |

### GET /v1/models 响应
```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4",
      "object": "model",
      "created": 1626777600,
      "owned_by": "OpenAI",
      "permission": [...],
      "root": "gpt-4",
      "parent": null
    }
  ]
}
```

---

## 十一、Dashboard 计费接口（TokenAuth）

| 方法 | 路径 | 说明 | 控制器 |
|------|------|------|--------|
| GET | `/dashboard/billing/subscription` | 获取订阅信息（额度/过期时间） | `GetSubscription` |
| GET | `/v1/dashboard/billing/subscription` | 同上（v1前缀兼容） | `GetSubscription` |
| GET | `/dashboard/billing/usage` | 获取用量信息 | `GetUsage` |
| GET | `/v1/dashboard/billing/usage` | 同上（v1前缀兼容） | `GetUsage` |

### GET /dashboard/billing/subscription 响应
```json
{
  "object": "billing_subscription",
  "has_payment_method": true,
  "soft_limit_usd": 100.0,
  "hard_limit_usd": 100.0,
  "system_hard_limit_usd": 100.0,
  "access_until": 1700000000
}
```

### GET /dashboard/billing/usage 响应
```json
{ "object": "list", "total_usage": 5000.0 }
```
> `total_usage` 单位: 0.01 USD

---

## 十二、中继转发接口（TokenAuth + Distribute）⭐核心

| 方法 | 路径 | 说明 | RelayMode | 控制器 |
|------|------|------|-----------|--------|
| POST | `/v1/chat/completions` | **Chat 补全（核心）** | ChatCompletions | `Relay` |
| POST | `/v1/completions` | Text 补全 | Completions | `Relay` |
| POST | `/v1/embeddings` | 文本嵌入 | Embeddings | `Relay` |
| POST | `/v1/images/generations` | 图片生成 | ImagesGenerations | `Relay` |
| POST | `/v1/audio/transcriptions` | 音频转文字（Whisper） | AudioTranscriptions | `Relay` |
| POST | `/v1/audio/translations` | 音频翻译 | AudioTranslations | `Relay` |
| POST | `/v1/audio/speech` | 文字转语音（TTS） | AudioSpeech | `Relay` |
| POST | `/v1/moderations` | 内容审核 | Moderations | `Relay` |
| POST | `/v1/edits` | 文本编辑 | Edits | `Relay` |
| POST | `/v1/engines/:model/embeddings` | 旧版嵌入 | Embeddings | `Relay` |
| ANY | `/v1/oneapi/proxy/:channelid/*target` | 指定渠道代理 | Proxy | `Relay` |

### 未实现的路由（RelayNotImplemented）
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/images/edits` | 图片编辑 |
| POST | `/v1/images/variations` | 图片变体 |
| GET | `/v1/files` | 列出文件 |
| POST | `/v1/files` | 上传文件 |
| DELETE | `/v1/files/:id` | 删除文件 |
| GET | `/v1/files/:id` | 获取文件信息 |
| GET | `/v1/files/:id/content` | 获取文件内容 |
| POST | `/v1/fine_tuning/jobs` | 创建微调任务 |
| GET | `/v1/fine_tuning/jobs` | 列出微调任务 |
| GET | `/v1/fine_tuning/jobs/:id` | 获取微调任务详情 |
| POST | `/v1/fine_tuning/jobs/:id/cancel` | 取消微调任务 |
| GET | `/v1/fine_tuning/jobs/:id/events` | 微调任务事件 |
| DELETE | `/v1/models/:model` | 删除微调模型 |
| POST | `/v1/assistants` | 创建助手 |
| GET | `/v1/assistants/:id` | 获取助手 |
| POST | `/v1/assistants/:id` | 修改助手 |
| DELETE | `/v1/assistants/:id` | 删除助手 |
| GET | `/v1/assistants` | 列出助手 |
| POST | `/v1/assistants/:id/files` | 助手上传文件 |
| GET | `/v1/assistants/:id/files/:fileId` | 获取助手文件 |
| DELETE | `/v1/assistants/:id/files/:fileId` | 删除助手文件 |
| GET | `/v1/assistants/:id/files` | 列出助手文件 |
| POST | `/v1/threads` | 创建线程 |
| GET | `/v1/threads/:id` | 获取线程 |
| POST | `/v1/threads/:id` | 修改线程 |
| DELETE | `/v1/threads/:id` | 删除线程 |
| POST | `/v1/threads/:id/messages` | 创建消息 |
| GET | `/v1/threads/:id/messages/:messageId` | 获取消息 |
| POST | `/v1/threads/:id/messages/:messageId` | 修改消息 |
| GET | `/v1/threads/:id/messages/:messageId/files/:filesId` | 获取消息文件 |
| GET | `/v1/threads/:id/messages/:messageId/files` | 列出消息文件 |
| POST | `/v1/threads/:id/runs` | 创建运行 |
| GET | `/v1/threads/:id/runs/:runsId` | 获取运行 |
| POST | `/v1/threads/:id/runs/:runsId` | 修改运行 |
| GET | `/v1/threads/:id/runs` | 列出运行 |
| POST | `/v1/threads/:id/runs/:runsId/submit_tool_outputs` | 提交工具输出 |
| POST | `/v1/threads/:id/runs/:runsId/cancel` | 取消运行 |
| GET | `/v1/threads/:id/runs/:runsId/steps/:stepId` | 获取运行步骤 |
| GET | `/v1/threads/:id/runs/:runsId/steps` | 列出运行步骤 |

### 认证方式
中继接口使用 `Authorization: Bearer sk-XXXX` 请求头。
- 令牌格式: `sk-XXXX`（前缀 sk- 可省略）
- 指定渠道: `sk-XXXX-channelId`（仅管理员可用）
- Distribute 中间件自动根据 user group + model 匹配渠道

### POST /v1/chat/completions — 核心请求示例
```json
{
  "model": "gpt-4",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "temperature": 0.7,
  "max_tokens": 1024
}
```
**流式响应**: `"stream": true` 时返回 SSE 格式 `data: {...}\n\n`

### 代理路由 /v1/oneapi/proxy/:channelid/*target
- `:channelid`: 指定渠道ID
- `*target`: 上游API路径
- 用于直接透传到指定渠道的上游API（绕过模型匹配）

---

## 十三、认证方式汇总

| 认证类型 | 适用接口 | 请求头 | 说明 |
|----------|----------|--------|------|
| **无认证** | `/api/status`, `/api/notice`, `/api/about` 等 | — | 公共信息 |
| **Session** | `/api/user/*` 管理接口 | Cookie | 登录后自动设置 |
| **AccessToken** | `/api/*` 管理接口 | `Authorization: <access_token>` | 用户生成的长时效Token，等同于Session登录 |
| **TokenAuth** | `/v1/*` 中继接口 | `Authorization: Bearer sk-XXXX` | 令牌key，用于API调用 |
| **UserAuth** | 用户级管理 | Session 或 AccessToken | 角色 ≥ Common(1) |
| **AdminAuth** | 管理员级管理 | Session 或 AccessToken | 角色 ≥ Admin(10) |
| **RootAuth** | 超级管理员 | Session 或 AccessToken | 角色 = Root(100) |

### 角色等级
| 值 | 角色 | 说明 |
|----|------|------|
| 0 | Guest | 访客 |
| 1 | Common | 普通用户 |
| 10 | Admin | 管理员 |
| 100 | Root | 超级管理员 |

### 渠道状态
| 值 | 状态 | 说明 |
|----|------|------|
| 0 | Unknown | 未知 |
| 1 | Enabled | 已启用 |
| 2 | ManuallyDisabled | 手动禁用 |
| 3 | AutoDisabled | 自动禁用 |

### 令牌状态
| 值 | 状态 | 说明 |
|----|------|------|
| 1 | Enabled | 已启用 |
| 2 | Disabled | 已禁用 |
| 3 | Expired | 已过期 |
| 4 | Exhausted | 已耗尽 |

---

## 十四、统一响应格式

### 成功响应
```json
{ "success": true, "message": "", "data": <具体数据> }
```

### 失败响应
```json
{ "success": false, "message": "错误原因描述" }
```

### 中继错误响应（OpenAI 兼容）
```json
{
  "error": {
    "message": "error description",
    "type": "invalid_request_error",
    "param": "model",
    "code": "model_not_found"
  }
}
```

---

## 十五、渠道类型常量对照表

| 值 | 渠道类型 | 厂商 |
|----|----------|------|
| 1 | OpenAI | OpenAI |
| 3 | Azure | Microsoft Azure |
| 8 | Custom | 自定义 |
| 11 | OpenAISB | OpenAI-SB |
| 12 | API2GPT | API2GPT |
| 13 | Anthropic | Anthropic |
| 14 | Baidu | 百度文心 |
| 15 | Zhipu | 智谱AI |
| 16 | Ali | 阿里通义 |
| 17 | Xunfei | 讯飞星火 |
| 18 | AIProxy | AIProxy |
| 19 | Tencent | 腾讯混元 |
| 20 | Gemini | Google Gemini |
| 21 | Ollama | Ollama |
| 22 | Cohere | Cohere |
| 23 | Cloudflare | Cloudflare AI |
| 24 | DeepL | DeepL |
| 25 | VertexAI | Google Vertex AI |
| 26 | Proxy | 代理 |
| 27 | CloseAI | CloseAI |
| 28 | AIGC2D | AIGC2D |
| 29 | Coze | 扣子 |
| 30 | Replicate | Replicate |
| 31 | Moonshot | Moonshot |
| 33 | Baichuan | 百川 |
| 34 | Minimax | MiniMax |
| 35 | Mistral | Mistral AI |
| 36 | Groq | Groq |
| 37 | DeepSeek | DeepSeek |
| 38 | TogetherAI | Together AI |
| 39 | Doubao | 字节豆包 |
| 40 | Novita | Novita AI |
| 41 | SiliconFlow | SiliconFlow |
| 42 | XAI | xAI (Grok) |
| 43 | OpenRouter | OpenRouter |
| 44 | BaiduV2 | 百度文心V2 |
| 45 | XunfeiV2 | 讯飞星火V2 |
| 46 | AliBailian | 阿里百炼 |
| 47 | OpenAICompatible | OpenAI兼容 |
| 48 | GeminiOpenAICompatible | Gemini OpenAI兼容 |
| 999 | Dummy | 测试用 |

---

## 十六、Skill 开发重点接口

后续实现 Skill 调用 One API 时，最常用的接口：

### 1. 中继调用（最核心）
```
POST /v1/chat/completions  —  LLM对话
POST /v1/embeddings        —  文本嵌入
POST /v1/images/generations — 图片生成
POST /v1/audio/speech      —  TTS
POST /v1/audio/transcriptions — STT
```

### 2. 令牌管理
```
POST /api/token/   — 创建令牌
GET  /api/token/   — 列出令牌
PUT  /api/token/   — 更新令牌额度/状态
```

### 3. 渠道管理
```
GET  /api/channel/        — 列出渠道
POST /api/channel/        — 添加渠道
GET  /api/channel/test/:id — 测试渠道
```

### 4. 用量查询
```
GET /dashboard/billing/subscription — 额度/过期
GET /dashboard/billing/usage        — 已用额度
GET /api/log/self/stat              — 日志统计
```

### 5. 模型发现
```
GET /v1/models              — 可用模型列表
GET /api/user/available_models — 用户可用模型
```

---

## 十七、OAuth 登录流程详解

所有 OAuth 流程遵循相同模式：
1. 前端调用 `GET /api/oauth/state` 获取 `state` 码
2. 重定向用户到 OAuth 提供方授权页，携带 `state`
3. OAuth 提供方回调到 One API，携带 `code` 和 `state`
4. One API 验证 `state`，用 `code` 换取用户信息
5. 若已登录 → 绑定第三方账号；若未登录 → 自动注册或登录

### GitHub OAuth
```
GET /api/oauth/github?code=xxx&state=xxx
```
- 用 code 换取 GitHub access_token → 获取 GitHub 用户信息（login, name, email）
- 已登录用户：自动绑定 GitHub（调用 GitHubBind）
- 未登录：已有账号 → 登录；新用户 → 自动注册（用户名 `github_{maxId+1}`）

### OIDC OAuth
```
GET /api/oauth/oidc?code=xxx&state=xxx
```
- 用 code 换取 OIDC access_token → 获取用户信息（sub, email, name, preferred_username）
- 回调地址: `{ServerAddress}/oauth/oidc`
- 新用户注册：优先用 `preferred_username`，否则 `oidc_{maxId+1}`

### 飞书 OAuth
```
GET /api/oauth/lark?code=xxx&state=xxx
```
- 用 code 换取飞书 access_token → 获取用户信息（open_id, name）
- 回调地址: `{ServerAddress}/oauth/lark`
- 新用户注册：用户名 `lark_{maxId+1}`

### 微信扫码登录
```
GET /api/oauth/wechat?code=xxx
```
- ⚠️ 微信登录**不走 state 验证**
- 用 code 请求 `{WeChatServerAddress}/api/wechat/user?code=xxx` 获取微信 open_id
- 需要 `WeChatServerToken` 作为 Authorization 头
- 新用户注册：用户名 `wechat_{maxId+1}`

### 微信绑定（需已登录）
```
GET /api/oauth/wechat/bind?code=xxx
```

### 邮箱绑定（需已登录 + 验证码）
```
GET /api/oauth/email/bind?email=xxx&code=123456
```

### 生成 OAuth State 码
```
GET /api/oauth/state
```
**响应**:
```json
{ "success": true, "message": "", "data": "随机12位字符串" }
```

---

## 十八、数据模型字段定义

### Channel 完整字段
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 渠道ID |
| `type` | int | 渠道类型（见渠道类型对照表） |
| `key` | string | API密钥（创建时支持 `\n` 分隔批量创建） |
| `status` | int | 状态: 0=未知, 1=启用, 2=手动禁用, 3=自动禁用 |
| `name` | string | 渠道名称 |
| `weight` | int | 权重（同优先级时影响随机选择概率） |
| `created_time` | int64 | 创建时间Unix时间戳 |
| `test_time` | int64 | 最后测试时间 |
| `response_time` | int | 响应时间（毫秒） |
| `base_url` | *string | API基础URL（nil时用默认值） |
| `models` | string | 支持的模型列表（逗号分隔） |
| `group` | string | 分组（逗号分隔，如 "default,vip"） |
| `model_mapping` | *string | 模型映射JSON，如 `{"gpt-4":"gpt-4-0613"}` |
| `priority` | int | 优先级（越大越优先，0为默认） |
| `config` | *string | 渠道配置JSON（见 ChannelConfig） |
| `balance` | float64 | 上游余额 |
| `balance_updated_time` | int64 | 余额更新时间 |
| `used_quota` | int64 | 已用额度 |
| `system_prompt` | *string | 系统提示词 |

**ChannelConfig 结构**（config 字段的 JSON 格式）:
```json
{
  "region": "",
  "sk": "",
  "ak": "",
  "user_id": "",
  "api_version": "",
  "library_id": "",
  "plugin": "",
  "vertex_ai_project_id": "",
  "vertex_ai_adc": ""
}
```
- `region`/`sk`/`ak`: AWS/阿里云等需要
- `api_version`: Azure 需要的 API 版本
- `library_id`: AIProxy Library
- `vertex_ai_project_id`/`vertex_ai_adc`: VertexAI 配置

### Token 完整字段
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 令牌ID |
| `user_id` | int | 所属用户ID |
| `key` | string | 令牌密钥（格式 `sk-XXXX`，创建时自动生成） |
| `status` | int | 状态: 1=启用, 2=禁用, 3=过期, 4=耗尽 |
| `name` | string | 令牌名称（≤30字符） |
| `created_time` | int64 | 创建时间 |
| `accessed_time` | int64 | 最后访问时间 |
| `expired_time` | int64 | 过期时间（-1=永不过期, 0=已过期, >0=Unix时间戳） |
| `remain_quota` | int64 | 剩余额度 |
| `unlimited_quota` | bool | 是否无限额度 |
| `used_quota` | int64 | 已用额度 |
| `models` | *string | 限制可用模型（nil或空=不限制，逗号分隔） |
| `subnet` | *string | 限制IP网段（nil或空=不限制，CIDR格式） |

### User 完整字段
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 用户ID |
| `username` | string | 用户名 |
| `password` | string | 密码（MD5哈希） |
| `display_name` | string | 显示名称 |
| `role` | int | 角色: 0=访客, 1=普通, 10=管理员, 100=超级管理员 |
| `status` | int | 状态: 1=启用, 2=禁用 |
| `email` | string | 邮箱 |
| `github_id` | string | GitHub ID |
| `wechat_id` | string | 微信ID |
| `lark_id` | string | 飞书ID |
| `oidc_id` | string | OIDC ID |
| `access_token` | string | API访问令牌（UUID格式） |
| `quota` | int64 | 当前额度 |
| `used_quota` | int64 | 已用额度 |
| `request_count` | int | 请求次数 |
| `group` | string | 用户分组（默认 "default"） |
| `aff_code` | string | 邀请码（4位随机字符串） |
| `inviter_id` | int | 邀请人ID |

### Redemption 完整字段
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 兑换码ID |
| `user_id` | int | 创建者ID |
| `name` | string | 兑换码名称（1-20字符） |
| `key` | string | 兑换码密钥（UUID格式） |
| `status` | int | 状态: 1=未使用, 2=已禁用, 3=已使用 |
| `quota` | int64 | 额度值 |
| `created_time` | int64 | 创建时间 |
| `redeemed_time` | int64 | 兑换时间 |

### Log 完整字段
| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 日志ID |
| `user_id` | int | 用户ID |
| `created_at` | int64 | 创建时间 |
| `type` | int | 类型: 1=充值, 2=消耗, 3=管理 |
| `content` | string | 日志内容 |
| `username` | string | 用户名 |
| `token_name` | string | 令牌名称 |
| `model_name` | string | 模型名称 |
| `quota` | int | 额度变化值 |
| `channel_id` | int | 渠道ID |
| `token_id` | int | 令牌ID |
| `elapsed_time` | float64 | 耗时（毫秒） |

---

## 十九、重要业务逻辑说明

### 额度计算
- 内部单位: 1 额度 = 1/500000 USD（即 `QuotaPerUnit` 默认值）
- `DisplayInCurrencyEnabled=true` 时，API返回值自动除以 `QuotaPerUnit` 转为 USD
- 最终计费: `实际额度 = ModelRatio × CompletionRatio × GroupRatio × token数量`

### 令牌配额预扣/结算
1. `PreConsumeTokenQuota`: 请求前检查并预扣令牌额度 + 用户额度
2. 请求完成后 `PostConsumeTokenQuota`: 多退少补
3. 额度不足时自动发邮件提醒
4. 令牌过期/耗尽时自动更新状态

### 渠道自动禁用/启用
- `ShouldDisableChannel`: 基于 OpenAI 错误码判断（401/403/429等）
- `MetricDisableChannel`: 基于滑动窗口错误率
- `ShouldEnableChannel`: 测试成功后自动重新启用
- 可通过 `AutomaticDisableChannelEnabled` 配置开关
- `ChannelDisableThreshold`: 响应时间超阈值（秒）自动禁用

### 余额查询支持的渠道
| 渠道类型 | 余额查询方式 |
|----------|-------------|
| OpenAI / Custom | `/v1/dashboard/billing/subscription` + `/usage` |
| CloseAI | `/dashboard/billing/credit_grants` |
| OpenAISB | `https://api.openai-sb.com/sb-api/user/status` |
| AIProxy | `https://aiproxy.io/api/report/getUserOverview` |
| API2GPT | `https://api.api2gpt.com/dashboard/billing/credit_grants` |
| AIGC2D | `https://api.aigc2d.com/dashboard/billing/credit_grants` |
| SiliconFlow | `https://api.siliconflow.cn/v1/user/info` |
| DeepSeek | `https://api.deepseek.com/user/balance` (取CNY余额) |
| OpenRouter | `https://openrouter.ai/api/v1/credits` |
| Azure | ❌ 未实现 |
| 其他 | ❌ 未实现 |

### 代理模式
`/v1/oneapi/proxy/:channelid/*target` 支持:
- 指定渠道ID透传到上游
- `*target` 匹配上游 API 路径
- 自动使用渠道的 key、base_url、config

### 登录方式限制
- `PasswordLoginEnabled=false`: 禁止密码登录
- `PasswordRegisterEnabled=false`: 禁止密码注册（仅允许OAuth注册）
- `RegisterEnabled=false`: 完全关闭新用户注册
- `EmailVerificationEnabled=true`: 注册时需邮箱验证码
- `EmailDomainRestrictionEnabled=true`: 仅允许白名单域名的邮箱注册
