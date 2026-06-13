# Free Token Plan

基于 [One API](https://github.com/songquanpeng/one-api) 的 AI 模型 API 统一网关管理技能，自动创建/分发 API Key，管理渠道，验证渠道。

## 功能

| 功能 | 说明 | 触发词 |
|------|------|--------|
| 🔑 **Key 分发** | 自动创建 API Key，返回地址 + Key + 可用模型 | 给我来个key、apikey、来点额度、给我个令牌 |
| 📡 **渠道管理** | 一键添加渠道 + auto-model 映射，换渠道不改配置 | 添加渠道、渠道列表、有哪些渠道 |
| ✅ **渠道验证** | 验证渠道可用性，不可用自动降级，可用自动恢复 | 检查渠道、测试渠道、验证渠道 |
| 🤖 **可用模型** | 列出当前所有可用模型 | 可用模型、模型列表 |
| 🔗 **服务连接** | 配置 One API 服务地址和账户，支持自部署 | 配置one-api、连接服务、部署one-api |
| ❓ **帮助** | 输出完整功能说明 | help、帮助、能做什么 |

## 安装

### 方式一：从 GitHub 克隆（推荐）

```bash
# 克隆仓库到 OpenClaw Skills 目录
git clone git@github.com:fuzhengwei/xfg-skills-free-token-plan.git ~/.qclaw/skills/xfg-skills-free-token-plan
```

克隆后重启 OpenClaw 即可生效，对话中输入触发词即可使用。

### 方式二：手动安装

1. 下载本仓库 [ZIP 包](https://github.com/fuzhengwei/xfg-skills-free-token-plan/archive/refs/heads/main.zip) 或克隆到本地
2. 将 `xfg-skills-free-token-plan` 目录复制到 OpenClaw Skills 目录：
   - macOS/Linux：`~/.qclaw/skills/`
   - Windows：`%USERPROFILE%\.qclaw\skills\`
3. 重启 OpenClaw

### 依赖

- **Python 3**：Skill 脚本使用 Python 3 运行，需确保 `python3` 可用
- **One API 服务**：需要一个运行中的 One API 实例（见下方「部署 One API」）
- **Docker**（可选）：用于自部署 One API + MySQL

### 验证安装

安装后对 AI 说「帮助」或「能做什么」，如果返回 Free Token Plan 的功能列表，说明安装成功。

## 使用案例

> 以下是在 OpenClaw 对话中直接使用的提示词，复制粘贴即可。

### 场景一：首次配置（从零开始）

```
配置 one-api，地址 http://81.70.245.73:4000，账户 root，密码 12345678
```

```
添加 deepseek 渠道，key 是 sk-xxxxxxxxxxxxxxxx
```

```
给我来个 key
```

### 场景二：添加多个渠道

```
添加 agnes 渠道，key 是 sk-agnes-xxxxx
```

```
添加 moonshot 渠道，key 是 sk-moonshot-xxxxx
```

```
有哪些渠道
```

### 场景三：验证渠道

```
检查渠道
```

返回示例：
```
渠道验证完成: ✅ 3 正常（优先级10）, ❌ 1 不可用
🔻 deepseek: 优先级 10 → 1（降级）
```

下次再验证，如果降级的渠道恢复了：

```
验证渠道
```

```
渠道验证完成: ✅ 4 正常（优先级10）, ❌ 0 不可用
🔺 deepseek: 优先级 1 → 10（恢复）
```

### 场景四：查看可用模型

```
可用模型
```

### 场景五：获取 API Key 给别人用

```
给我来个 key
```

返回：
```
🔑 API Key 创建成功！
地址: http://81.70.245.73:4000
Key:  sk-xxxxxxxxxxxxxxxx
模型: auto-model, deepseek-chat, agnes-2.0-flash, ...
```

对方在 AI 工具中：
- API Base URL：`http://81.70.245.73:4000`
- API Key：`sk-xxxxxxxxxxxxxxxx`
- 模型名：`auto-model`（统一名称，换渠道不用改）

## 核心机制

### 统一优先级 + 负载均衡

所有通过此技能配置的渠道默认优先级 **10**，One API 在同优先级渠道间自动负载均衡。

```
渠道A（优先级10）──┐
渠道B（优先级10）──┼──→ One API 自动负载均衡 → 用户请求
渠道C（优先级10）──┘
```

### 渠道验证 + 自动降级/恢复

| 状态 | 优先级 | 说明 |
|------|--------|------|
| ✅ 可用 | 10 | 正常参与负载均衡 |
| ❌ 不可用 | 1 | 降级，不再参与负载均衡 |
| 🔄 恢复可用 | 10 | 下次验证通过后自动恢复 |

- 验证不可用 → 优先级降为 1（渠道保留，不删除）
- 下次验证可用 → 优先级恢复为 10（重新参与负载均衡）
- 手动禁用（状态2）的渠道 → 跳过，不修改

### auto-model 统一模型

每个渠道添加时自动将真实模型映射为固定名称 `auto-model`：

| 渠道模型 | 映射 |
|----------|------|
| `agnes-2.0-flash` | `auto-model → agnes-2.0-flash` |
| `deepseek-chat` | `auto-model → deepseek-chat` |

**核心价值**：在 AI 工具中统一使用 `auto-model` 作为模型名，换渠道只需改映射，不用改工具配置。

## 快速开始

### 1. 部署 One API（首次使用）

```bash
# 部署 MySQL
docker run --name oneapi-mysql -d --restart always \
  -p 13306:3306 \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -e MYSQL_DATABASE=oneapi \
  -v /home/ubuntu/data/mysql:/var/lib/mysql \
  registry.cn-hangzhou.aliyuncs.com/xfg-studio/mysql:8.0

# 部署 One API
docker run --name one-api -d --restart always \
  -p 4000:3000 \
  -e SQL_DSN="root:123456@tcp(你的服务器IP:13306)/oneapi" \
  -e TZ=Asia/Shanghai \
  -v /home/ubuntu/data/one-api:/data \
  registry.cn-hangzhou.aliyuncs.com/xfg-studio/one-api:v0.6.10
```

部署后访问 `http://你的IP:4000`，用默认账号 `root/12345678` 登录。

> 也可使用 `assets/docker-compose-template.yml` 一键部署。

### 2. 配置服务连接

```
配置 one-api，地址 http://xxx:4000，账户 root，密码 xxx
```

### 3. 添加渠道

```
添加 deepseek 渠道，key 是 sk-xxx
```

### 4. 获取 API Key

```
给我来个 key
```

### 5. 验证渠道

```
检查渠道
```

## 全部脚本命令

```bash
# 服务管理
python3 scripts/service_manager.py detect                    # 检测配置状态
python3 scripts/service_manager.py save --url URL --username USER --password PASS  # 保存配置

# 渠道管理
python3 scripts/channel_manager.py list-registry             # 查看渠道注册表
python3 scripts/channel_manager.py add --name NAME --key KEY # 从注册表添加渠道
python3 scripts/channel_manager.py list                      # 列出已添加渠道
python3 scripts/channel_manager.py add-custom ...            # 自定义参数添加

# Key 管理
python3 scripts/token_manager.py create --name NAME --unlimited  # 创建令牌
python3 scripts/token_manager.py list                        # 列出令牌
python3 scripts/token_manager.py distribute                  # 分发 API Key

# 渠道验证
python3 scripts/health_checker.py check-all                  # 验证 + 自动降级/恢复
python3 scripts/health_checker.py check-all --no-auto-fix    # 仅验证，不降级/恢复
python3 scripts/health_checker.py check-channel --id N       # 验证单个渠道
python3 scripts/health_checker.py history                    # 查看验证历史

# auto-model
python3 scripts/auto_model.py list                           # 查看映射

# 部署引导
python3 scripts/setup_helper.py deploy --ip YOUR_IP          # 生成部署脚本
```

## 目录结构

```
├── SKILL.md                          # Skill 入口文件（AI Agent 使用）
├── README.md                         # 本文件
├── scripts/
│   ├── oneapi_client.py              # One API HTTP 客户端
│   ├── service_manager.py            # 服务连接管理
│   ├── channel_manager.py            # 渠道管理 + 注册表
│   ├── token_manager.py              # API Key 管理
│   ├── health_checker.py             # 渠道验证 + 自动降级/恢复
│   ├── auto_model.py                 # auto-model 映射
│   └── setup_helper.py              # 部署引导
├── data/
│   ├── channels.csv                  # 渠道注册表（社区可贡献）
│   ├── service_config.json           # 服务连接配置（本地，已 gitignore）
│   └── service_config.template.json  # 配置模板
├── references/
│   ├── architecture.md               # 架构设计
│   ├── auto-model.md                 # auto-model 详解
│   ├── channel-registry.md           # 注册表说明
│   └── oneapi-api-reference.md       # One API 接口参考
├── assets/
│   └── docker-compose-template.yml   # Docker Compose 模板
└── one-api-http-interfaces.md        # One API HTTP 接口文档
```

## 渠道注册表

`data/channels.csv` 预置以下渠道，提交 PR 可添加更多：

| 渠道 | 类型 | 模型 |
|------|------|------|
| Agnes AI | OpenAI 兼容 | agnes-2.0-flash |
| DeepSeek | DeepSeek | deepseek-chat, deepseek-reasoner |
| 硅基流动 | SiliconFlow | Qwen2.5-72B, Qwen2.5-7B, DeepSeek-V3 |
| Moonshot Kimi | Moonshot | moonshot-v1-8k/32k/128k |
| 智谱AI | 智谱 | glm-4-plus, glm-4-flash, glm-4-long |
| 阿里通义千问 | 阿里 | qwen-plus, qwen-turbo, qwen-max |
| 腾讯混元 | 腾讯 | hunyuan-lite, hunyuan-standard, hunyuan-pro |
| MiniMax | MiniMax | MiniMax-Text-01, abab6.5s-chat |

## 注意事项

- `data/service_config.json` 含密码，已加入 `.gitignore`，不要泄露
- API Key 创建后仅返回一次完整内容，务必及时保存
- auto-model 映射在添加渠道时自动创建，手动修改渠道后需重新同步
- 渠道验证为手动触发（「检查渠道/测试渠道/验证渠道」），不可用自动降级，可用自动恢复
- 所有渠道默认优先级10（统一负载均衡），不可用降级为1，验证可用后恢复为10
- One API 默认 root 密码 `12345678`，生产环境务必修改
- 手动禁用（状态2）的渠道不会被验证或修改
- 渠道注册表是社区共享的，提交 PR 即可添加新渠道

## 贡献

1. Fork 本仓库
2. 编辑 `data/channels.csv` 添加新渠道
3. 提交 PR

## License

Apache-2.0
