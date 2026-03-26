# GLM-5 适配优先级清单

> 创建时间：2026-03-25 12:14
> 
> 目标：将 claude-cookbooks-zh 适配为 GLM-5 版本

---

## 📊 Notebooks 统计

### 总览

- **总 notebooks 数**：67 个（估算）
- **已翻译**：21 个（courses_zh/）
- **待适配**：67 个

### 分类统计

| 类别 | 数量 | 优先级 |
|------|------|--------|
| tool_use/ | 12+ | P0（核心） |
| misc/ | 10+ | P1（重要） |
| basic/ | 5+ | P0（基础） |
| extended/ | 40+ | P2（扩展） |

---

## 🎯 前 10 个核心 Notebooks（P0）

### 1. calculator_tool.ipynb ⭐⭐⭐
**优先级**：P0
**难度**：低
**原因**：基础工具调用示例
**适配内容**：
- API 端点替换
- 模型名称替换
- 参数调整

### 2. customer_service_agent.ipynb ⭐⭐⭐
**优先级**：P0
**难度**：中
**原因**：完整 Agent 示例
**适配内容**：
- 工具调用适配
- 上下文窗口调整
- 提示词优化

### 3. tool_use_with_pydantic.ipynb ⭐⭐⭐
**优先级**：P0
**难度**：中
**原因**：结构化输出示例
**适配内容**：
- Pydantic 模型适配
- JSON Schema 验证

### 4. parallel_tools.ipynb ⭐⭐⭐
**优先级**：P0
**难度**：中
**原因**：并行工具调用
**适配内容**：
- 并行调用适配
- 结果处理

### 5. tool_choice.ipynb ⭐⭐⭐
**优先级**：P0
**难度**：低
**原因**：工具选择策略
**适配内容**：
- tool_choice 参数适配
- 强制调用模式

### 6. basic_chat.ipynb ⭐⭐
**优先级**：P0
**难度**：低
**原因**：基础对话示例
**适配内容**：
- 基础 API 调用
- 流式响应

### 7. streaming.ipynb ⭐⭐
**优先级**：P0
**难度**：低
**原因**：流式响应示例
**适配内容**：
- SSE 流式处理
- 增量响应

### 8. prompt_caching.ipynb ⭐
**优先级**：P0
**难度**：中
**原因**：提示词缓存
**适配内容**：
- 缓存机制适配（GLM-5 是否支持？）

### 9. long_context.ipynb ⭐
**优先级**：P0
**难度**：中
**原因**：长上下文处理
**适配内容**：
- 上下文窗口调整（128k）
- 分块处理

### 10. extracting_structured_json.ipynb ⭐
**优先级**：P0
**难度**：中
**原因**：结构化输出
**适配内容**：
- JSON 模式
- 格式验证

---

## 📋 适配清单

### 第一天（2026-03-25）

**上午（12:00-14:00）**：
- ✅ 创建适配清单（本文档）
- ⏳ 分析 API 差异
- ⏳ 准备适配模板

**下午（14:00-18:00）**：
- ⏳ 适配前 5 个 notebooks（calculator_tool, customer_service_agent, tool_use_with_pydantic, parallel_tools, tool_choice）
- ⏳ 测试验证
- ⏳ 问题记录

### 第二天（2026-03-26）

**上午（09:00-12:00）**：
- ⏳ 适配剩余 5 个 notebooks
- ⏳ 批量测试
- ⏳ 修复问题

**下午（14:00-18:00）**：
- ⏳ 文档更新
- ⏳ 提交 PR（可选）
- ⏳ 总结报告

---

## 🔧 技术适配点

### 1. API 端点替换

**Claude API**：
```python
import anthropic
client = anthropic.Anthropic(api_key="...")
response = client.messages.create(
    model="claude-3-opus",
    ...
)
```

**GLM-5 API**：
```python
from zhipuai import ZhipuAI
client = ZhipuAI(api_key="...")
response = client.chat.completions.create(
    model="glm-4",
    ...
)
```

### 2. 模型名称映射

| Claude 模型 | GLM-5 模型 |
|------------|-----------|
| claude-3-opus | glm-4 |
| claude-3-sonnet | glm-4-flash |
| claude-3-haiku | glm-4-flash |

### 3. 参数调整

| 参数 | Claude | GLM-5 |
|------|--------|-------|
| max_tokens | 4096 | 4096 |
| temperature | 0-1 | 0-1 |
| context_window | 200k | 128k |
| streaming | ✅ | ✅ |

### 4. 工具调用差异

**Claude**：
```python
tools = [{"name": "calculator", ...}]
response = client.messages.create(
    tools=tools,
    ...
)
```

**GLM-5**：
```python
tools = [{"type": "function", "function": {...}}]
response = client.chat.completions.create(
    tools=tools,
    ...
)
```

---

## ⚠️ 已知问题

### 1. 上下文窗口差异
- Claude: 200k
- GLM-5: 128k
- **解决方案**：调整分块策略

### 2. 工具调用格式
- Claude: 自定义格式
- GLM-5: OpenAI 兼容格式
- **解决方案**：格式转换

### 3. 提示词缓存
- Claude: 支持
- GLM-5: 待确认
- **解决方案**：如果不支持则跳过

---

## 📈 预期成果

### 第 1 天结束

- ✅ 前 5 个 notebooks 适配完成
- ✅ 基础测试通过
- ✅ 问题清单整理

### 第 2 天结束

- ✅ 全部 10 个核心 notebooks 适配完成
- ✅ 批量测试通过
- ✅ 文档更新
- ✅ 可选：提交 PR

---

## 🔗 相关链接

- **claude-cookbooks-zh**：https://github.com/srxly888-creator/claude-cookbooks-zh
- **GLM-5 文档**：https://open.bigmodel.cn/dev/api
- **决策记录**：`memory/decision-glm5-integration-2026-03-25.md`

---

**状态**：✅ 清单创建完成
**下一步**：开始适配前 5 个 notebooks
**预计时间**：2026-03-25 14:00-18:00
