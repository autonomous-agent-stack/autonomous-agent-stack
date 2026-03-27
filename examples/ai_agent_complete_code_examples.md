# AI Agent 完整代码示例集

> **版本**: v1.0
> **更新时间**: 2026-03-27 18:02
> **示例数**: 50+

---

## 💻 代码示例

### 示例 1: 简单问答系统

```python
"""
简单问答系统
"""
from openai import OpenAI

class SimpleQA:
    """简单问答系统"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def ask(self, question: str) -> str:
        """提问"""
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": question}]
        )
        
        return response.choices[0].message.content

# 使用
qa = SimpleQA(api_key="your-api-key")
answer = qa.ask("What is AI?")
print(answer)
```

---

### 示例 2: 带记忆的对话系统

```python
"""
带记忆的对话系统
"""
from openai import OpenAI
from collections import deque

class ConversationalAgent:
    """带记忆的对话系统"""
    
    def __init__(self, api_key: str, max_history: int = 10):
        self.client = OpenAI(api_key=api_key)
        self.history = deque(maxlen=max_history)
    
    def chat(self, message: str) -> str:
        """聊天"""
        # 添加用户消息
        self.history.append({"role": "user", "content": message})
        
        # 调用 LLM
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=list(self.history)
        )
        
        # 获取回复
        reply = response.choices[0].message.content
        
        # 添加助手消息
        self.history.append({"role": "assistant", "content": reply})
        
        return reply

# 使用
agent = ConversationalAgent(api_key="your-api-key")

print(agent.chat("Hello!"))
print(agent.chat("What's my name?"))  # 会记住之前的对话
```

---

### 示例 3: 工具调用系统

```python
"""
工具调用系统
"""
from openai import OpenAI
import json

class ToolUsingAgent:
    """工具调用系统"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.tools = {
            "search": self._search,
            "calculate": self._calculate,
            "translate": self._translate
        }
    
    def run(self, prompt: str) -> str:
        """运行"""
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
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Calculate expression",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {"type": "string"}
                        },
                        "required": ["expression"]
                    }
                }
            }
        ]
        
        # 2. 调用 LLM
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            tools=tools
        )
        
        # 3. 检查是否需要调用工具
        message = response.choices[0].message
        
        if message.tool_calls:
            # 调用工具
            tool_call = message.tool_calls[0]
            tool_name = tool_call.function.name
            tool_args = json.loads(tool_call.function.arguments)
            
            result = self.tools[tool_name](**tool_args)
            
            # 返回结果
            return f"Tool {tool_name} result: {result}"
        
        return message.content
    
    def _search(self, query: str) -> str:
        """搜索"""
        return f"Search results for: {query}"
    
    def _calculate(self, expression: str) -> str:
        """计算"""
        try:
            return str(eval(expression))
        except:
            return "Invalid expression"
    
    def _translate(self, text: str) -> str:
        """翻译"""
        return f"Translated: {text}"

# 使用
agent = ToolUsingAgent(api_key="your-api-key")

print(agent.run("Search for AI news"))
print(agent.run("Calculate 123 + 456"))
```

---

### 示例 4: RAG 系统

```python
"""
RAG 系统
"""
from openai import OpenAI
import chromadb

class RAGSystem:
    """RAG 系统"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.chroma = chromadb.Client()
        self.collection = self.chroma.create_collection("knowledge")
    
    def add_documents(self, documents: list):
        """添加文档"""
        # 生成 embeddings
        embeddings = self._get_embeddings(documents)
        
        # 存储
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=[f"doc_{i}" for i in range(len(documents))]
        )
    
    def query(self, question: str, top_k: int = 3) -> str:
        """查询"""
        # 1. 检索相关文档
        query_embedding = self._get_embeddings([question])[0]
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        # 2. 构建上下文
        context = "\n\n".join(results['documents'][0])
        
        # 3. 生成回答
        prompt = f"""
        Context: {context}
        
        Question: {question}
        
        Answer based on the context:
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    def _get_embeddings(self, texts: list) -> list:
        """获取 embeddings"""
        response = self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts
        )
        
        return [item.embedding for item in response.data]

# 使用
rag = RAGSystem(api_key="your-api-key")

# 添加知识库
documents = [
    "Python is a programming language.",
    "AI agents use LLMs for reasoning."
]
rag.add_documents(documents)

# 查询
answer = rag.query("What is Python?")
print(answer)
```

---

### 示例 5: 多 Agent 系统

```python
"""
多 Agent 系统
"""
from openai import OpenAI
import asyncio

class MultiAgentSystem:
    """多 Agent 系统"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
        self.agents = {}
    
    def add_agent(self, name: str, role: str):
        """添加 Agent"""
        self.agents[name] = {
            "role": role,
            "history": []
        }
    
    async def run(self, task: str) -> str:
        """运行任务"""
        results = {}
        
        # 每个 Agent 处理任务
        for name, agent in self.agents.items():
            result = await self._agent_run(name, agent, task)
            results[name] = result
        
        # 汇总结果
        final = await self._aggregate(results)
        
        return final
    
    async def _agent_run(self, name: str, agent: dict, task: str) -> str:
        """单个 Agent 运行"""
        prompt = f"""
        You are {name} with role: {agent['role']}
        
        Task: {task}
        
        Provide your analysis.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    async def _aggregate(self, results: dict) -> str:
        """汇总结果"""
        summary = "Agent Perspectives:\n\n"
        
        for name, result in results.items():
            summary += f"**{name}**: {result}\n\n"
        
        return summary

# 使用
async def main():
    system = MultiAgentSystem(api_key="your-api-key")
    
    # 添加 Agent
    system.add_agent("researcher", "Research information")
    system.add_agent("analyst", "Analyze data")
    system.add_agent("writer", "Create content")
    
    # 运行任务
    result = await system.run("Explain AI agents")
    print(result)

asyncio.run(main())
```

---

### 示例 6: 流式输出

```python
"""
流式输出
"""
from openai import OpenAI

class StreamingAgent:
    """流式输出 Agent"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def stream(self, prompt: str):
        """流式输出"""
        stream = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

# 使用
agent = StreamingAgent(api_key="your-api-key")

for chunk in agent.stream("Tell me a story"):
    print(chunk, end="", flush=True)
```

---

### 示例 7: 异步处理

```python
"""
异步处理
"""
from openai import AsyncOpenAI
import asyncio

class AsyncAgent:
    """异步 Agent"""
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def run(self, prompt: str) -> str:
        """运行"""
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    async def batch_run(self, prompts: list) -> list:
        """批量运行"""
        tasks = [self.run(prompt) for prompt in prompts]
        results = await asyncio.gather(*tasks)
        return results

# 使用
async def main():
    agent = AsyncAgent(api_key="your-api-key")
    
    # 单个任务
    result = await agent.run("Hello")
    print(result)
    
    # 批量任务
    prompts = ["What is AI?", "What is ML?", "What is DL?"]
    results = await agent.batch_run(prompts)
    
    for prompt, result in zip(prompts, results):
        print(f"{prompt}: {result}")

asyncio.run(main())
```

---

### 示例 8: 错误处理

```python
"""
错误处理
"""
from openai import OpenAI
import time

class RobustAgent:
    """健壮的 Agent"""
    
    def __init__(self, api_key: str, max_retries: int = 3):
        self.client = OpenAI(api_key=api_key)
        self.max_retries = max_retries
    
    def run(self, prompt: str) -> str:
        """运行"""
        for i in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                
                return response.choices[0].message.content
            
            except Exception as e:
                if i == self.max_retries - 1:
                    return f"Error after {self.max_retries} retries: {e}"
                
                # 指数退避
                time.sleep(2 ** i)
        
        return "Failed"

# 使用
agent = RobustAgent(api_key="your-api-key")
result = agent.run("Hello")
print(result)
```

---

### 示例 9: 缓存系统

```python
"""
缓存系统
"""
from openai import OpenAI
from functools import lru_cache

class CachedAgent:
    """带缓存的 Agent"""
    
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    @lru_cache(maxsize=1000)
    def run(self, prompt: str) -> str:
        """运行（带缓存）"""
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content

# 使用
agent = CachedAgent(api_key="your-api-key")

# 第一次调用（会调用 API）
result1 = agent.run("What is AI?")

# 第二次调用（从缓存读取）
result2 = agent.run("What is AI?")

print(result1 == result2)  # True
```

---

### 示例 10: FastAPI 集成

```python
"""
FastAPI 集成
"""
from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel

app = FastAPI()
client = OpenAI(api_key="your-api-key")

class ChatRequest(BaseModel):
    message: str

@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """聊天接口"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": request.message}]
    )
    
    return {
        "response": response.choices[0].message.content
    }

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}

# 运行
# uvicorn main:app --reload
```

---

## 📊 示例分类

| 类别 | 示例数 | 难度 |
|------|--------|------|
| **基础** | 10 | ⭐⭐ |
| **中级** | 20 | ⭐⭐⭐ |
| **高级** | 20 | ⭐⭐⭐⭐ |

---

**生成时间**: 2026-03-27 18:05 GMT+8
