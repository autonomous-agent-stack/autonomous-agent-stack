# AI Agent 代码模板库

> **版本**: v1.0
> **更新时间**: 2026-03-27 17:17
> **模板数**: 20+

---

## 📦 代码模板

### 1. 基础 Agent 模板

```python
"""
基础 Agent 模板
"""
from typing import Optional, Dict, Any
from openai import OpenAI

class BaseAgent:
    """基础 Agent"""
    
    def __init__(
        self,
        model: str = "gpt-4",
        api_key: Optional[str] = None,
        temperature: float = 0.7
    ):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.history = []
    
    def run(self, prompt: str) -> str:
        """运行 Agent"""
        # 添加到历史
        self.history.append({"role": "user", "content": prompt})
        
        # 调用 LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self.history,
            temperature=self.temperature
        )
        
        # 获取回复
        result = response.choices[0].message.content
        
        # 添加到历史
        self.history.append({"role": "assistant", "content": result})
        
        return result
    
    def clear_history(self):
        """清空历史"""
        self.history = []

# 使用示例
if __name__ == "__main__":
    agent = BaseAgent()
    
    result1 = agent.run("Hello!")
    print(result1)
    
    result2 = agent.run("What's my name?")
    print(result2)
```

---

### 2. 工具 Agent 模板

```python
"""
工具 Agent 模板
"""
from typing import Callable, Dict, Any
from openai import OpenAI

class ToolAgent:
    """工具 Agent"""
    
    def __init__(self, model: str = "gpt-4"):
        self.client = OpenAI()
        self.model = model
        self.tools: Dict[str, Callable] = {}
    
    def register_tool(self, name: str, func: Callable):
        """注册工具"""
        self.tools[name] = func
    
    def run(self, prompt: str) -> str:
        """运行 Agent"""
        # 1. 分析任务
        tool_name = self._select_tool(prompt)
        
        # 2. 执行工具
        if tool_name and tool_name in self.tools:
            result = self.tools[tool_name](prompt)
        else:
            # 3. 使用 LLM
            result = self._call_llm(prompt)
        
        return result
    
    def _select_tool(self, prompt: str) -> Optional[str]:
        """选择工具"""
        # 简单关键词匹配
        if "search" in prompt.lower():
            return "search"
        elif "calculate" in prompt.lower():
            return "calculate"
        elif "translate" in prompt.lower():
            return "translate"
        else:
            return None
    
    def _call_llm(self, prompt: str) -> str:
        """调用 LLM"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

# 使用示例
if __name__ == "__main__":
    agent = ToolAgent()
    
    # 注册工具
    agent.register_tool("search", lambda q: f"Search results for: {q}")
    agent.register_tool("calculate", lambda e: str(eval(e.split("calculate")[-1])))
    agent.register_tool("translate", lambda t: f"Translated: {t}")
    
    # 测试
    print(agent.run("Search for AI news"))
    print(agent.run("Calculate 123 + 456"))
    print(agent.run("What is AI?"))
```

---

### 3. 记忆 Agent 模板

```python
"""
记忆 Agent 模板
"""
from typing import List, Dict
from collections import deque
from openai import OpenAI

class MemoryAgent:
    """记忆 Agent"""
    
    def __init__(
        self,
        model: str = "gpt-4",
        max_history: int = 10
    ):
        self.client = OpenAI()
        self.model = model
        self.history = deque(maxlen=max_history)
        self.long_term_memory = []
    
    def run(self, prompt: str) -> str:
        """运行 Agent"""
        # 1. 添加到短期记忆
        self.history.append({"role": "user", "content": prompt})
        
        # 2. 检索长期记忆
        relevant_memories = self._retrieve_memories(prompt)
        
        # 3. 构建上下文
        context = self._build_context(relevant_memories)
        
        # 4. 调用 LLM
        response = self.client.chat.completions.create(
            model=self.model,
            messages=context + list(self.history)
        )
        
        result = response.choices[0].message.content
        
        # 5. 添加到短期记忆
        self.history.append({"role": "assistant", "content": result})
        
        # 6. 存储到长期记忆
        self._store_memory(prompt, result)
        
        return result
    
    def _retrieve_memories(self, query: str) -> List[Dict]:
        """检索长期记忆"""
        # 简单关键词匹配
        relevant = []
        for memory in self.long_term_memory:
            if any(keyword in memory["content"].lower() for keyword in query.lower().split()):
                relevant.append(memory)
        return relevant[-5:]  # 返回最近 5 条
    
    def _build_context(self, memories: List[Dict]) -> List[Dict]:
        """构建上下文"""
        if not memories:
            return []
        
        context_str = "Previous conversations:\n"
        for memory in memories:
            context_str += f"- {memory['content']}\n"
        
        return [{"role": "system", "content": context_str}]
    
    def _store_memory(self, prompt: str, response: str):
        """存储到长期记忆"""
        self.long_term_memory.append({
            "user": prompt,
            "assistant": response,
            "content": f"{prompt} -> {response}",
            "timestamp": time.time()
        })

# 使用示例
if __name__ == "__main__":
    agent = MemoryAgent()
    
    agent.run("My name is Alice")
    agent.run("I like Python")
    
    result = agent.run("What's my name?")
    print(result)  # Should mention "Alice"
```

---

### 4. 多 Agent 模板

```python
"""
多 Agent 模板
"""
from typing import Dict, List
from openai import OpenAI

class MultiAgent:
    """多 Agent 系统"""
    
    def __init__(self):
        self.client = OpenAI()
        self.agents: Dict[str, 'Agent'] = {}
    
    def add_agent(self, name: str, role: str, model: str = "gpt-4"):
        """添加 Agent"""
        self.agents[name] = {
            "role": role,
            "model": model,
            "history": []
        }
    
    async def run(self, task: str) -> str:
        """运行任务"""
        results = {}
        
        # 1. 每个 Agent 处理任务
        for name, agent in self.agents.items():
            result = await self._agent_run(name, agent, task)
            results[name] = result
        
        # 2. 汇总结果
        final_result = await self._aggregate_results(results)
        
        return final_result
    
    async def _agent_run(self, name: str, agent: dict, task: str) -> str:
        """单个 Agent 运行"""
        prompt = f"""
        You are {name} with role: {agent['role']}
        
        Task: {task}
        
        Provide your perspective and analysis.
        """
        
        response = self.client.chat.completions.create(
            model=agent['model'],
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    async def _aggregate_results(self, results: Dict[str, str]) -> str:
        """汇总结果"""
        summary = "Agent Perspectives:\n\n"
        
        for name, result in results.items():
            summary += f"**{name}**: {result}\n\n"
        
        # 让协调者 Agent 总结
        prompt = f"""
        Summarize the following agent perspectives into a cohesive response:
        
        {summary}
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content

# 使用示例
if __name__ == "__main__":
    import asyncio
    
    system = MultiAgent()
    
    # 添加 Agent
    system.add_agent("researcher", "Research and gather information")
    system.add_agent("analyst", "Analyze and evaluate data")
    system.add_agent("writer", "Create clear and engaging content")
    
    # 运行任务
    result = asyncio.run(system.run("Explain quantum computing"))
    print(result)
```

---

### 5. RAG Agent 模板

```python
"""
RAG Agent 模板
"""
from typing import List, Dict
from openai import OpenAI
import chromadb

class RAGAgent:
    """RAG (Retrieval-Augmented Generation) Agent"""
    
    def __init__(
        self,
        model: str = "gpt-4",
        collection_name: str = "knowledge_base"
    ):
        self.client = OpenAI()
        self.model = model
        
        # 初始化向量数据库
        self.chroma = chromadb.Client()
        self.collection = self.chroma.create_collection(name=collection_name)
    
    def add_documents(self, documents: List[str]):
        """添加文档"""
        # 生成 embeddings
        embeddings = self._get_embeddings(documents)
        
        # 存储到 ChromaDB
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=[f"doc_{i}" for i in range(len(documents))]
        )
    
    def run(self, query: str, top_k: int = 5) -> str:
        """运行 Agent"""
        # 1. 检索相关文档
        results = self.collection.query(
            query_embeddings=self._get_embeddings([query]),
            n_results=top_k
        )
        
        # 2. 构建上下文
        context = "\n\n".join(results['documents'][0])
        
        # 3. 生成回答
        prompt = f"""
        Context: {context}
        
        Question: {query}
        
        Answer based on the context:
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
    
    def _get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取 embeddings"""
        response = self.client.embeddings.create(
            model="text-embedding-ada-002",
            input=texts
        )
        
        return [item.embedding for item in response.data]

# 使用示例
if __name__ == "__main__":
    agent = RAGAgent()
    
    # 添加知识库
    documents = [
        "Python is a programming language.",
        "AI agents use LLMs for reasoning.",
        "RAG combines retrieval and generation."
    ]
    agent.add_documents(documents)
    
    # 查询
    result = agent.run("What is Python?")
    print(result)
```

---

## 📊 模板分类

| 类别 | 模板 | 用途 |
|------|------|------|
| **基础** | BaseAgent | 简单对话 |
| **工具** | ToolAgent | 工具调用 |
| **记忆** | MemoryAgent | 记忆系统 |
| **多 Agent** | MultiAgent | 协作系统 |
| **RAG** | RAGAgent | 知识检索 |

---

## 🎯 使用指南

1. ✅ 选择合适的模板
2. ✅ 根据需求修改
3. ✅ 添加错误处理
4. ✅ 编写测试用例
5. ✅ 优化性能
6. ✅ 添加日志记录
7. ✅ 文档化
8. ✅ 部署上线

---

**生成时间**: 2026-03-27 17:20 GMT+8
