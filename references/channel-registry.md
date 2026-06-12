# 渠道注册表说明

## 概述

`data/channels.csv` 是渠道注册表，随 Skill 发布到 GitHub，社区可通过 PR 贡献新渠道。

## 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✅ | 渠道名称（唯一标识，小写英文） |
| `type` | ✅ | One API 渠道类型 ID（见渠道类型对照表） |
| `base_url` | ✅ | API 基础地址 |
| `models` | ✅ | 支持的模型列表（逗号分隔） |
| `description` | ❌ | 渠道描述 |
| `api_key_url` | ❌ | API Key 获取地址 |
| `doc_url` | ❌ | 文档地址 |

## 渠道类型对照表

| 值 | 类型 | 值 | 类型 |
|----|------|----|------|
| 1 | OpenAI | 37 | DeepSeek |
| 3 | Azure | 38 | TogetherAI |
| 13 | Anthropic | 39 | Doubao |
| 14 | Baidu | 40 | Novita |
| 15 | Zhipu | 41 | SiliconFlow |
| 16 | Ali | 42 | XAI |
| 19 | Tencent | 43 | OpenRouter |
| 20 | Gemini | 47 | OpenAICompatible |
| 31 | Moonshot | 48 | GeminiOpenAICompatible |
| 36 | Groq | | |

## 添加新渠道

### 方式一：直接编辑 CSV

在 `data/channels.csv` 中添加一行：

```csv
newchannel,1,https://api.newchannel.com,model-a,model-b,新渠道描述,https://newchannel.com/keys,https://docs.newchannel.com
```

### 方式二：使用脚本

```bash
python3 scripts/channel_manager.py add-to-registry \
  --name newchannel \
  --type openai \
  --base-url "https://api.newchannel.com" \
  --models "model-a,model-b" \
  --description "新渠道描述" \
  --api-key-url "https://newchannel.com/keys"
```

### 方式三：GitHub PR

Fork 仓库 → 编辑 `data/channels.csv` → 提交 PR → 合并后随 Skill 发布

## 注意事项

1. `name` 必须唯一，不区分大小写
2. `models` 中不要包含 auto-model 前缀，添加到 One API 时会自动生成
3. `base_url` 不要以 `/` 结尾
4. 渠道类型 ID 必须与 One API 源码中的 `channeltype` 常量一致
5. 社区贡献的渠道信息需要确保准确性
