# auto-model 映射详解

## 概念

auto-model 是为 One API 中每个原始模型自动生成的路由别名，格式为 `auto-{原始模型名}`。

## 工作原理

### 创建渠道时

1. 用户添加渠道（如 agnes），指定模型 `gpt-4o,gpt-4o-mini`
2. 系统自动添加 `auto-gpt-4o,auto-gpt-4o-mini` 到模型的 models 字段
3. 系统自动在 model_mapping 中添加：`{"auto-gpt-4o": "gpt-4o", "auto-gpt-4o-mini": "gpt-4o-mini"}`

### 请求路由时

1. 用户请求 `auto-gpt-4o`
2. One API 的 Distribute 中间件查找 ability 表中支持 `auto-gpt-4o` 的渠道
3. 找到渠道后，model_mapping 将 `auto-gpt-4o` 映射为 `gpt-4o`
4. 请求转发到上游渠道，使用实际的 `gpt-4o` 模型

## 优势

1. **统一入口**：使用 `auto-*` 模型，不关心底层是哪个渠道
2. **自动负载均衡**：多个渠道支持同一模型时，One API 自动选择
3. **故障切换**：一个渠道不可用时，自动切换到其他渠道
4. **优先级控制**：通过渠道 priority 和 weight 控制路由偏好

## 示例

### 场景：多个渠道提供 gpt-4o

| 渠道 | 模型 | 优先级 |
|------|------|--------|
| agnes | gpt-4o, auto-gpt-4o | 10 |
| openai | gpt-4o, auto-gpt-4o | 5 |

用户请求 `auto-gpt-4o`：
- 优先路由到 agnes（优先级高）
- agnes 不可用时，降级到 openai

### 场景：混合模型

| 渠道 | 原始模型 | auto-model |
|------|----------|------------|
| agnes | gpt-4o | auto-gpt-4o |
| deepseek | deepseek-chat | auto-deepseek-chat |
| siliconflow | Qwen/Qwen2.5-72B-Instruct | auto-Qwen/Qwen2.5-72B-Instruct |

用户可使用的 auto-model 列表：
- `auto-gpt-4o`
- `auto-deepseek-chat`
- `auto-Qwen/Qwen2.5-72B-Instruct`

## 同步操作

```bash
# 同步单个渠道的 auto-model
python3 scripts/auto_model.py sync --id 1

# 同步所有渠道的 auto-model
python3 scripts/auto_model.py sync

# 查看当前 auto-model 映射
python3 scripts/auto_model.py list

# 查看可用 auto-model
python3 scripts/auto_model.py available
```

## 注意事项

1. auto-model 映射在**添加渠道时自动创建**，通常无需手动同步
2. 手动修改渠道的 models 或 model_mapping 后，需要运行 sync 重新同步
3. auto-model 名称格式固定为 `auto-{原始模型名}`，不支持自定义前缀
4. 如果原始模型名本身以 `auto-` 开头，不会生成递归映射
