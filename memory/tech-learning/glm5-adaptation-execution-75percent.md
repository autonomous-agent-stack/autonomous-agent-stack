# GLM-5 适配执行（75% 火力阶段）

> 执行时间：2026-03-25 13:57-14:00
> 功率：🔥🔥 75%
> 任务：适配前 3 个 notebooks

---

## 🎯 适配目标（75% 火力）

### 目标 Notebooks

1. **vision_with_tools.ipynb** (198 行) ⭐⭐⭐
   - 优先级：P0
   - 难度：低
   - 内容：视觉功能 + 工具使用

2. **calculator_tool.ipynb** (247 行) ⭐⭐⭐
   - 优先级：P0
   - 难度：低
   - 内容：基础工具调用

3. **tool_use_with_pydantic.ipynb** (346 行) ⭐⭐
   - 优先级：P0
   - 难度：中
   - 内容：结构化输出

---

## 🔧 适配步骤

### 1. vision_with_tools.ipynb

**适配点**：
```python
# Claude API
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model="claude-opus-4-1",
    messages=[...],
    tools=[...]
)

# GLM-5 API
from zhipuai import ZhipuAI
client = ZhipuAI()
response = client.chat.completions.create(
    model="glm-4",
    messages=[...],
    tools=[...]
)
```

**执行步骤**：
- [ ] 替换 import 语句
- [ ] 替换 client 初始化
- [ ] 替换 API 调用
- [ ] 调整参数（max_tokens, temperature）
- [ ] 测试验证

---

### 2. calculator_tool.ipynb

**适配点**：
```python
# Claude API
response = client.messages.create(
    model="claude-opus-4-1",
    max_tokens=1024,
    tools=[calculator_tool]
)

# GLM-5 API
response = client.chat.completions.create(
    model="glm-4",
    max_tokens=1024,
    tools=[calculator_tool]
)
```

**执行步骤**：
- [ ] 替换 API 调用
- [ ] 测试计算器功能
- [ ] 验证结果

---

### 3. tool_use_with_pydantic.ipynb

**适配点**：
```python
# Claude API
response = client.messages.create(
    model="claude-opus-4-1",
    tools=[pydantic_tool]
)

# GLM-5 API
response = client.chat.completions.create(
    model="glm-4",
    tools=[pydantic_tool]
)
```

**执行步骤**：
- [ ] 替换 API 调用
- [ ] 测试 Pydantic 模型
- [ ] 验证结构化输出

---

## ⚠️ 已知问题

### 1. 工具格式差异

**Claude 格式**：
```python
tools = [{
    "name": "calculator",
    "description": "...",
    "input_schema": {...}
}]
```

**GLM-5 格式**（OpenAI 兼容）：
```python
tools = [{
    "type": "function",
    "function": {
        "name": "calculator",
        "description": "...",
        "parameters": {...}
    }
}]
```

### 2. 响应格式差异

**Claude 响应**：
```python
response.content[0].text
response.stop_reason
```

**GLM-5 响应**：
```python
response.choices[0].message.content
response.choices[0].finish_reason
```

---

## 📊 预期成果

### 13:57-14:00（75% 火力，3 分钟）

**目标**：
- ✅ 开始适配 vision_with_tools.ipynb
- ⏳ 完成 API 替换
- ⏳ 基础测试

### 14:00-18:00（50% 火力，4 小时）

**目标**：
- ⏳ 完成 vision_with_tools.ipynb
- ⏳ 完成 calculator_tool.ipynb
- ⏳ 完成 tool_use_with_pydantic.ipynb
- ⏳ 批量测试
- ⏳ 文档更新

---

## 💡 执行策略

### 75% 火力（13:57-14:00，3 分钟）

**重点**：
- 快速开始第一个 notebook
- 验证适配可行性
- 记录问题

### 50% 火力（14:00-18:00，4 小时）

**重点**：
- 完成全部适配
- 批量测试
- 质量保证

---

## 🔗 相关文档

- **适配准备**：`memory/glm5-adaptation-preparation-2026-03-25.md`
- **优先级清单**：`memory/glm5-adaptation-priority-list.md`
- **决策记录**：`memory/decision-glm5-integration-2026-03-25.md`

---

**状态**：🔥🔥 75% 火力阶段开始
**剩余时间**：3 分钟
**下一阶段**：🔥 50% 火力（14:00-18:00）
