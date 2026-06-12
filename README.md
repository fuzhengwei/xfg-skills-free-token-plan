# xfg-skills-free-token-plan

Free Token Plan — 基于 One API 的 AI 模型 API 自动化管理技能。

## 功能

- 🔗 **服务连接**：检测/配置 One API 服务，支持自部署引导
- 📡 **渠道管理**：维护渠道注册表，一键添加渠道 + auto-model 映射
- 🔑 **Key 分发**：自动创建 API Key，返回完整连接信息（地址+模型+Key）
- 💊 **健康检查**：定时检测渠道可用性，自动降级/通知

## 快速开始

### 1. 配置 One API 服务

```bash
python3 scripts/service_manager.py save --url http://YOUR_IP:4000 --username root --password YOUR_PASSWORD
```

### 2. 添加渠道

```bash
# 查看可用渠道
python3 scripts/channel_manager.py list-registry

# 添加渠道
python3 scripts/channel_manager.py add --name deepseek --key sk-your-api-key
```

### 3. 获取 API Key

```bash
python3 scripts/token_manager.py distribute
```

### 4. 健康检查

```bash
python3 scripts/health_checker.py check-all
```

## 目录结构

```
├── SKILL.md                          # Skill 入口文件
├── scripts/
│   ├── oneapi_client.py              # One API HTTP 客户端
│   ├── service_manager.py            # 服务连接管理
│   ├── channel_manager.py            # 渠道管理 + 注册表
│   ├── token_manager.py              # API Key 管理
│   ├── health_checker.py             # 健康检查
│   ├── auto_model.py                 # auto-model 映射
│   └── setup_helper.py              # 部署引导
├── data/
│   ├── channels.csv                  # 渠道注册表
│   └── service_config.json           # 服务连接配置（本地）
├── references/
│   ├── architecture.md               # 架构设计
│   ├── auto-model.md                 # auto-model 详解
│   ├── channel-registry.md           # 注册表说明
│   └── oneapi-api-reference.md       # One API 接口参考
├── assets/
│   └── docker-compose-template.yml   # Docker Compose 模板
└── one-api/                          # One API 源码（参考）
```

## auto-model 机制

每个渠道的模型自动映射为 `auto-{model}`：

- `deepseek-chat` → `auto-deepseek-chat`
- `gpt-4o` → `auto-gpt-4o`

使用 `auto-*` 模型时，One API 自动路由到可用渠道。

## 贡献渠道

编辑 `data/channels.csv` 添加新渠道，或提交 PR。

## License

Apache-2.0
