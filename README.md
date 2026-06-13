# Free Token Plan

基于 [One API](https://github.com/songquanpeng/one-api) 的 AI 模型 API 统一网关管理技能，自动创建/分发 API Key，管理渠道，健康检查。

## 功能

| 功能 | 说明 | 触发词 |
|------|------|--------|
| 🔑 **Key 分发** | 自动创建 API Key，返回地址 + Key + 可用模型 | 给我来个key、apikey、来点额度、给我个令牌 |
| 📡 **渠道管理** | 一键添加渠道 + auto-model 映射，换渠道不改配置 | 添加渠道、渠道列表、有哪些渠道 |
| 💊 **健康检查** | 检测渠道可用性，自动排优先级，异常渠道自动禁用/恢复 | 检测渠道、健康检查、渠道状态 |
| 🤖 **可用模型** | 列出当前所有可用模型 | 可用模型、模型列表 |
| 🔗 **服务连接** | 配置 One API 服务地址和账户，支持自部署 | 配置one-api、连接服务、部署one-api |
| ❓ **帮助** | 输出完整功能说明 | help、帮助、能做什么 |

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

部署后访问 `http://你的IP:4000`，用默认账号 `root/123456` 登录。

> 也可使用 `assets/docker-compose-template.yml` 一键部署。

### 2. 配置服务连接

```bash
python3 scripts/service_manager.py save \
  --url http://YOUR_IP:4000 \
  --username root \
  --password YOUR_PASSWORD
```

或直接告诉 AI："配置 one-api，地址 http://xxx:4000，账户 root，密码 xxx"

### 3. 添加渠道

```bash
# 查看可用渠道注册表
python3 scripts/channel_manager.py list-registry

# 从注册表添加（自动匹配渠道类型、Base URL、模型列表）
python3 scripts/channel_manager.py add --name deepseek --key sk-your-api-key

# 自定义参数添加
python3 scripts/channel_manager.py add-custom \
  --name my-channel \
  --type 1 \
  --key sk-your-api-key \
  --base-url https://api.example.com \
  --models "gpt-4o,gpt-4o-mini"
```

### 4. 获取 API Key

```bash
# 创建并分发 API Key
python3 scripts/token_manager.py distribute
```

返回格式：
```
🔑 API Key 创建成功！
地址: http://YOUR_IP:4000
Key:  sk-xxxxxxxxxxxxxxxx
模型: auto-model, deepseek-chat, gpt-4o, ...
```

### 5. 健康检查

```bash
# 检测所有渠道 + 自动排优先级
python3 scripts/health_checker.py check-all

# 仅检测，不修改优先级
python3 scripts/health_checker.py check-all --no-auto-fix

# 自定义连续失败阈值（默认2次）
python3 scripts/health_checker.py check-all --failures 3

# 查看检查历史
python3 scripts/health_checker.py history
```

## auto-model 统一模型

每个渠道添加时自动将真实模型映射为固定名称 `auto-model`：

| 渠道模型 | 映射 |
|----------|------|
| `agnes-2.0-flash` | `auto-model → agnes-2.0-flash` |
| `deepseek-chat` | `auto-model → deepseek-chat` |
| `gpt-4o` | `auto-model → gpt-4o` |

**核心价值**：在 AI 工具中统一使用 `auto-model` 作为模型名，换渠道只需改映射，不用改工具配置。多渠道同模型时 One API 自动负载均衡。

```bash
# 查看当前 auto-model 映射
python3 scripts/auto_model.py list
```

## 健康检查机制

### 优先级自动排序

每次检测后按响应速度分4档：

| 响应时间 | 优先级 | 级别 |
|----------|--------|------|
| ≤2s | 10 | 极速 |
| ≤5s | 5 | 快速 |
| ≤10s | 1 | 正常 |
| >10s | 0 | 慢速 |

同档位同优先级 → One API 自动负载均衡。

### 自动恢复

- 渠道连续失败达阈值（默认2次）→ 自动禁用
- 被自动禁用的渠道恢复后 → 重新参与优先级排序
- 手动禁用（状态2）的渠道 → 跳过，不修改
- 检查历史持久化到 `data/health_history.json`，重启后仍可恢复

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

# 健康检查
python3 scripts/health_checker.py check-all                  # 检测 + 自动排优先级
python3 scripts/health_checker.py check-all --no-auto-fix    # 仅检测不改优先级
python3 scripts/health_checker.py check-all --failures N     # 连续失败N次才禁用
python3 scripts/health_checker.py history                    # 查看检查历史

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
│   ├── health_checker.py             # 健康检查 + 自动优先级
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
- 健康检查为手动触发（「检测渠道」），每次检测自动排优先级
- One API 默认 root 密码 `123456`，生产环境务必修改
- MySQL 需要开放端口供 One API 连接，注意防火墙规则
- 手动禁用（状态2）的渠道不会被检测或修改，仅自动禁用（状态3）的渠道参与恢复

## 贡献

1. Fork 本仓库
2. 编辑 `data/channels.csv` 添加新渠道
3. 提交 PR

## License

Apache-2.0
