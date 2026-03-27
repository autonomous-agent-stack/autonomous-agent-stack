# AI Agent 面试题库完整版 2.0

> **版本**: v2.0
> **更新时间**: 2026-03-27 17:12
> **题目数**: 100+

---

## 📝 面试题库

### 基础概念（20 题）

#### 1. 什么是 AI Agent？

**答案**:
AI Agent 是一个能够自主感知环境、做出决策并执行行动的系统。它通常包括：
- **感知**：接收输入（文本、图像等）
- **推理**：使用 LLM 进行推理
- **行动**：调用工具或执行操作
- **记忆**：存储和检索信息

**评分标准**:
- ✅ 提到感知-推理-行动循环（3 分）
- ✅ 提到 LLM 作为核心（2 分）
- ✅ 提到工具使用（2 分）
- ✅ 提到记忆系统（2 分）
- ✅ 举例说明（1 分）

---

#### 2. Agent 和 Chatbot 的区别？

**答案**:
| 特性 | Chatbot | Agent |
|------|---------|-------|
| **自主性** | 低 | 高 |
| **工具使用** | 有限 | 广泛 |
| **目标导向** | 弱 | 强 |
| **学习能力** | 弱 | 强 |
| **复杂任务** | 难 | 易 |

**关键区别**:
- Agent 可以**主动**执行任务
- Agent 可以**使用工具**
- Agent 可以**规划**和**推理**

---

#### 3. ReAct 模式是什么？

**答案**:
ReAct = Reasoning + Acting

**流程**:
```
Question → Thought → Action → Observation → ... → Answer
```

**示例**:
```
Question: What is the weather in Beijing?

Thought: I need to search for Beijing weather
Action: search("Beijing weather")
Observation: Beijing: 25°C, sunny

Thought: I have the answer
Answer: Beijing is 25°C and sunny
```

**优势**:
- ✅ 可解释性强
- ✅ 可以自我纠正
- ✅ 适合复杂任务

---

#### 4. 什么是 Prompt Engineering？

**答案**:
Prompt Engineering 是设计和优化输入提示词以引导 LLM 生成期望输出的技术。

**核心技巧**:
1. **清晰指令**：明确说明任务
2. **Few-shot**：提供示例
3. **Chain-of-thought**：分步推理
4. **角色扮演**：设定角色
5. **格式化输出**：指定格式

**示例**:
```python
# ❌ 差的 Prompt
"Summarize this text"

# ✅ 好的 Prompt
"""
Task: Summarize the following text in 3 bullet points.

Text: {text}

Requirements:
- Each bullet point should be < 20 words
- Focus on key insights
- Use simple language

Output format:
• Point 1
• Point 2
• Point 3
"""
```

---

#### 5. Token 是什么？为什么重要？

**答案**:
Token 是 LLM 处理文本的基本单位。

**计算方式**:
- 英文：~4 字符 = 1 token
- 中文：~1.5 字符 = 1 token

**重要性**:
1. **成本**：API 按 token 计费
2. **限制**：模型有 token 上限
3. **性能**：token 越多，延迟越高

**优化策略**:
```python
# 1. 计算 token 数
import tiktoken
encoder = tiktoken.encoding_for_model("gpt-4")
token_count = len(encoder.encode(text))

# 2. 截断到限制
max_tokens = 4000
if token_count > max_tokens:
    tokens = tokens[:max_tokens]
    text = encoder.decode(tokens)
```

---

### 架构设计（20 题）

#### 6. 如何设计一个多 Agent 系统？

**答案**:

**架构模式**:
```
User Request
    ↓
Orchestrator Agent（协调者）
    ↓
┌───────┬───────┬───────┐
│ Agent1│ Agent2│ Agent3│
│(研究) │(写作) │(审查) │
└───────┴───────┴───────┘
    ↓
Final Output
```

**关键组件**:
1. **Orchestrator**：任务分配和协调
2. **Worker Agents**：执行具体任务
3. **Shared Memory**：共享上下文
4. **Communication**：Agent 间通信

**代码示例**:
```python
class MultiAgentSystem:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()
        self.workers = {
            "researcher": ResearcherAgent(),
            "writer": WriterAgent(),
            "reviewer": ReviewerAgent()
        }
    
    async def run(self, task: str) -> str:
        # 1. 分解任务
        subtasks = await self.orchestrator.decompose(task)
        
        # 2. 分配给 workers
        results = {}
        for subtask in subtasks:
            agent = self.workers[subtask.agent_type]
            results[subtask.id] = await agent.run(subtask)
        
        # 3. 整合结果
        final = await self.orchestrator.integrate(results)
        
        return final
```

---

#### 7. Agent 记忆系统如何设计？

**答案**:

**三层记忆架构**:
1. **短期记忆**（Conversation Buffer）
   - 最近 N 轮对话
   - 存储在内存
   - 快速访问

2. **工作记忆**（Working Memory）
   - 当前任务上下文
   - 存储在内存
   - 任务相关

3. **长期记忆**（Long-term Memory）
   - 向量数据库
   - 持久化存储
   - 语义检索

**代码实现**:
```python
class MemorySystem:
    def __init__(self):
        # 短期记忆
        self.short_term = deque(maxlen=10)
        
        # 工作记忆
        self.working = {}
        
        # 长期记忆
        self.long_term = ChromaDB()
    
    async def remember(self, content: str, memory_type: str):
        """记住"""
        if memory_type == "short":
            self.short_term.append(content)
        elif memory_type == "working":
            self.working["context"] = content
        else:
            await self.long_term.add(content)
    
    async def recall(self, query: str, memory_type: str):
        """回忆"""
        if memory_type == "short":
            return list(self.short_term)
        elif memory_type == "working":
            return self.working.get("context")
        else:
            return await self.long_term.search(query)
```

---

#### 8. 如何实现 Agent 工具调用？

**答案**:

**Function Calling 流程**:
```
1. 定义工具 → 2. LLM 决策 → 3. 执行工具 → 4. 返回结果
```

**代码实现**:
```python
# 1. 定义工具
tools = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search the web",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        }
    }
]

# 2. LLM 决策
response = await client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Search for AI news"}],
    tools=tools
)

# 3. 执行工具
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    function_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)
    
    result = await execute_tool(function_name, arguments)
    
    # 4. 返回结果
    return result
```

---

### 性能优化（20 题）

#### 9. 如何优化 Agent 响应时间？

**答案**:

**优化策略**:
1. **并发执行**（-70% 时间）
```python
# 串行
result1 = await llm.call(prompt1)  # 3s
result2 = await db.query(query)    # 1s
# 总计: 4s

# 并发
result1, result2 = await asyncio.gather(
    llm.call(prompt1),
    db.query(query)
)
# 总计: 3s
```

2. **缓存**（-60% 时间）
```python
@lru_cache(maxsize=1000)
def cached_call(prompt: str):
    return llm.call(prompt)
```

3. **流式输出**（-50% 感知延迟）
```python
async for chunk in llm.stream(prompt):
    yield chunk
```

4. **模型选择**（-40% 时间）
```python
if len(prompt) < 500:
    model = "gpt-3.5-turbo"  # 快
else:
    model = "gpt-4"  # 准
```

---

#### 10. 如何降低 Agent 成本？

**答案**:

**成本优化策略**:
1. **缓存**（-70% 成本）
2. **模型降级**（-75% 成本）
3. **Token 优化**（-60% 成本）
4. **批量处理**（-40% 成本）
5. **预计算**（-50% 成本）

**成本监控**:
```python
class CostMonitor:
    def __init__(self):
        self.total_cost = 0
    
    async def track(self, model: str, tokens: int):
        # 计算成本
        cost = self._calculate_cost(model, tokens)
        self.total_cost += cost
        
        # 警告
        if self.total_cost > 100:
            logger.warning(f"Cost exceeded $100: ${self.total_cost:.2f}")
```

---

### 故障排查（20 题）

#### 11. Agent 常见错误有哪些？

**答案**:

**常见错误**:
1. **Token 超限**
   - 症状：`Error: This model's maximum context length is 8192 tokens`
   - 解决：截断或分段

2. **API 限流**
   - 症状：`Error: Rate limit exceeded`
   - 解决：添加重试和限流

3. **无限循环**
   - 症状：Agent 一直循环
   - 解决：设置最大轮数

4. **工具调用失败**
   - 症状：工具执行错误
   - 解决：添加错误处理

5. **内存溢出**
   - 症状：`Error: Out of memory`
   - 解决：流式处理

**通用解决方案**:
```python
async def safe_agent(prompt: str) -> str:
    max_retries = 3
    max_iterations = 10
    
    for i in range(max_retries):
        try:
            for j in range(max_iterations):
                result = await agent.run(prompt)
                
                if is_complete(result):
                    return result
            
            raise Exception("Max iterations exceeded")
        
        except Exception as e:
            if i == max_retries - 1:
                raise
            await asyncio.sleep(2 ** i)
```

---

### 安全防护（20 题）

#### 12. 如何防止 Prompt 注入？

**答案**:

**防护措施**:
1. **输入验证**
```python
def validate_input(prompt: str) -> str:
    forbidden = [
        r'ignore.*instructions',
        r'system:',
        r'you are now'
    ]
    
    for pattern in forbidden:
        if re.search(pattern, prompt, re.IGNORECASE):
            raise ValueError("Potential injection detected")
    
    return prompt
```

2. **权限隔离**
```python
# 限制 Agent 权限
agent = Agent(
    allowed_tools=["search", "calculate"],
    allowed_domains=["wikipedia.org"]
)
```

3. **输出过滤**
```python
def sanitize_output(output: str) -> str:
    # 移除敏感信息
    output = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[REDACTED]', output)
    return output
```

---

## 📊 面试题分类

| 类别 | 题目数 | 难度 |
|------|--------|------|
| **基础概念** | 20 | ⭐⭐ |
| **架构设计** | 20 | ⭐⭐⭐ |
| **性能优化** | 20 | ⭐⭐⭐ |
| **故障排查** | 20 | ⭐⭐⭐ |
| **安全防护** | 20 | ⭐⭐⭐⭐ |

---

**生成时间**: 2026-03-27 17:15 GMT+8
