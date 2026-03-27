# AI Agent 快速参考速查表

> **版本**: v1.0
> **更新时间**: 2026-03-27
> **适用**: 日常开发

---

## 🚀 快速启动

### OpenClaw CLI 常用命令

```bash
# 启动 Gateway
openclaw gateway start

# 查看状态
openclaw status

# 查看日志
openclaw logs -f

# 停止服务
openclaw gateway stop
```

### Git 快捷命令

```bash
# 快速提交
git add . && git commit -m "feat: 描述"

# 快速推送
git push origin main

# 查看状态
git status

# 查看历史
git log --oneline --graph --all
```

---

## 📝 Prompt 模板速查

### 角色 Prompt

```
你是{{role}}，职责是{{responsibility}}。

你的技能包括：
- {{skill_1}}
- {{skill_2}}

你的工作流程：
1. {{step_1}}
2. {{step_2}}
3. {{step_3}}
```

### 任务 Prompt

```
任务：{{task_description}}

输入：{{input}}
输出要求：{{output_format}}

约束条件：
- {{constraint_1}}
- {{constraint_2}}
```

### ReAct Prompt

```
Question: {{question}}

Thought: 你应该思考如何解决这个问题
Action: 工具名称（如 search, calculator）
Action Input: 工具输入参数

Observation: 工具执行结果

Thought: 基于观察，下一步是什么
Action: ...

Final Answer: 最终答案
```

---

## 🔧 工具定义速查

### Python 工具定义

```python
tools = [
    {
        "name": "search_web",
        "description": "搜索互联网信息",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    }
]
```

### Claude Tool Use

```python
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    tools=tools,
    messages=[
        {"role": "user", "content": "搜索最新的 AI Agent 研究"}
    ]
)
```

---

## 💾 记忆系统速查

### ChromaDB 初始化

```python
import chromadb

client = chromadb.Client()
collection = client.create_collection("agent_memory")

# 添加文档
collection.add(
    documents=["文档内容"],
    metadatas=[{"source": "file.txt"}],
    ids=["doc1"]
)

# 查询
results = collection.query(
    query_texts=["查询内容"],
    n_results=5
)
```

### 对话记忆

```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

# 保存对话
memory.save_context(
    {"input": "用户输入"},
    {"output": "Agent 输出"}
)

# 加载历史
history = memory.load_memory_variables({})
```

---

## 🎯 Agent 模式速查

### ReAct 模式

```python
from langchain.agents import initialize_agent

agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent="react",
    verbose=True
)

result = agent.run("问题")
```

### Plan-and-Execute

```python
from langchain_experimental.plan_and_execute import PlanAndExecute

agent = PlanAndExecute(
    planner=planner,
    executor=executor,
    tools=tools
)

result = agent.run("复杂任务")
```

---

## 📊 性能优化速查

### Token 优化

| 技术 | 效果 | 示例 |
|------|------|------|
| **压缩 Prompt** | -30% | 移除冗余词 |
| **缓存结果** | -50% | 相同查询缓存 |
| **批量处理** | -40% | 合并相似请求 |
| **流式输出** | 体验+ | 实时显示 |

### 成本控制

| 策略 | 成本节省 | 代码示例 |
|------|---------|---------|
| **国产模型** | -98% | `model="glm-5"` |
| **降级策略** | -60% | 备用模型 |
| **Token 限制** | -20% | `max_tokens=1024` |
| **温度调整** | -15% | `temperature=0.3` |

---

## 🔍 调试技巧速查

### 日志记录

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
logger.info("Agent 执行步骤")
```

### 错误追踪

```python
try:
    result = agent.run(task)
except Exception as e:
    logger.error(f"Agent 失败: {e}")
    # 降级策略
    result = fallback_agent.run(task)
```

### 性能监控

```python
import time

start_time = time.time()
result = agent.run(task)
duration = time.time() - start_time

logger.info(f"执行时间: {duration:.2f}s")
```

---

## 🛡️ 安全最佳实践速查

### 输入验证

```python
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    query: str
    
    @validator('query')
    def validate_query(cls, v):
        # 检查长度
        if len(v) > 1000:
            raise ValueError("查询过长")
        
        # 检查危险字符
        dangerous = ['<', '>', '{', '}', ';']
        for char in dangerous:
            if char in v:
                raise ValueError(f"非法字符: {char}")
        
        return v
```

### 权限控制

```python
# 工具权限检查
if not permission_manager.check(tool_name, Permission.EXECUTE):
    raise PermissionError(f"无权限执行工具: {tool_name}")

# 资源访问控制
if not access_control.check(user_id, resource_id):
    raise AccessDeniedError("访问被拒绝")
```

---

## 📚 常用 API 速查

### OpenAI API

```python
from openai import OpenAI

client = OpenAI()

response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)
```

### Claude API

```python
from anthropic import Anthropic

client = Anthropic()

response = client.messages.create(
    model="claude-3-opus-20240229",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)
```

### GLM API

```python
from zhipuai import ZhipuAI

client = ZhipuAI()

response = client.chat.completions.create(
    model="glm-5",
    messages=[
        {"role": "user", "content": "Hello"}
    ]
)
```

---

## 🎨 格式化速查

### Markdown 表格

```markdown
| 列1 | 列2 | 列3 |
|-----|-----|-----|
| 内容1 | 内容2 | 内容3 |
```

### 代码块

````markdown
```python
# Python 代码
print("Hello")
```
````

### 引用

```markdown
> 这是一段引用
```

---

## 🚨 故障排查速查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| **Token 超限** | 上下文过长 | 压缩 Prompt / 使用长上下文模型 |
| **工具调用失败** | 权限不足 | 检查工具权限 |
| **响应超时** | 网络问题 | 增加超时时间 / 重试 |
| **成本过高** | 调用频繁 | 启用缓存 / 优化 Prompt |

---

## 📖 推荐资源速查

### 官方文档

| 资源 | 链接 |
|------|------|
| **OpenAI** | https://platform.openai.com/docs |
| **Anthropic** | https://docs.anthropic.com |
| **LangChain** | https://python.langchain.com |
| **OpenClaw** | https://docs.openclaw.ai |

### 学习平台

| 平台 | 链接 |
|------|------|
| **DeepLearning.AI** | https://www.deeplearning.ai |
| **Coursera** | https://www.coursera.org |
| **Udemy** | https://www.udemy.com |

### 开源项目

| 项目 | Stars | 链接 |
|------|-------|------|
| **AutoGPT** | 160k+ | https://github.com/Significant-Gravitas/Auto-GPT |
| **AutoGen** | 30k+ | https://github.com/microsoft/autogen |
| **CrewAI** | 15k+ | https://github.com/joaomdmoura/crewAI |

---

**生成时间**: 2026-03-27 14:00 GMT+8
**覆盖领域**: 10+
**代码示例**: 20+
