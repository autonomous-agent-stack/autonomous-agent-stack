# AI Agent 快速入门 10 分钟教程

> **版本**: v1.0
> **学习时间**: 10 分钟
> **目标**: 快速掌握 AI Agent 开发

---

## 🚀 第 1 分钟：最简单的 Agent

```python
from openai import OpenAI

client = OpenAI()

def agent(task: str) -> str:
    """1 分钟创建 Agent"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": task}]
    )
    return response.choices[0].message.content

# 使用
result = agent("What is AI?")
print(result)
```

---

## 🛠️ 第 2-3 分钟：添加工具

```python
class ToolAgent:
    """带工具的 Agent"""
    
    def __init__(self):
        self.tools = {
            "search": self._search,
            "calculate": self._calculate
        }
    
    def run(self, task: str) -> str:
        # 选择工具
        if "search" in task.lower():
            return self.tools["search"](task)
        elif "calculate" in task.lower():
            return self.tools["calculate"](task)
        else:
            return agent(task)
    
    def _search(self, query: str) -> str:
        return f"Search: {query}"
    
    def _calculate(self, expression: str) -> str:
        return str(eval(expression))

# 使用
agent = ToolAgent()
print(agent.run("Calculate 2+2"))
```

---

## 💾 第 4-5 分钟：添加记忆

```python
from collections import deque

class MemoryAgent:
    """带记忆的 Agent"""
    
    def __init__(self):
        self.history = deque(maxlen=10)  # 记住最近 10 轮
    
    def run(self, task: str) -> str:
        # 记录用户输入
        self.history.append({"role": "user", "content": task})
        
        # 调用 LLM（带历史）
        response = client.chat.completions.create(
            model="gpt-4",
            messages=list(self.history)
        )
        
        result = response.choices[0].message.content
        
        # 记录助手回复
        self.history.append({"role": "assistant", "content": result})
        
        return result

# 使用
agent = MemoryAgent()
agent.run("My name is Alice")
agent.run("What's my name?")  # 会记住 "Alice"
```

---

## ⚡ 第 6-7 分钟：异步处理

```python
import asyncio

async def async_agent(tasks: list) -> list:
    """异步批量处理"""
    async def process(task):
        # 模拟异步调用
        await asyncio.sleep(0.1)
        return agent(task)
    
    # 并发处理
    results = await asyncio.gather(
        *[process(task) for task in tasks]
    )
    
    return results

# 使用
tasks = ["What is AI?", "What is ML?", "What is DL?"]
results = asyncio.run(async_agent(tasks))
print(results)
```

---

## 🔧 第 8-9 分钟：错误处理

```python
class SafeAgent:
    """安全的 Agent"""
    
    def __init__(self, max_retries=3):
        self.max_retries = max_retries
    
    def run(self, task: str) -> str:
        for i in range(self.max_retries):
            try:
                return agent(task)
            except Exception as e:
                if i == self.max_retries - 1:
                    return f"Error: {e}"
                time.sleep(2 ** i)  # 指数退避
        
        return "Failed"

# 使用
agent = SafeAgent()
result = agent.run("What is AI?")
```

---

## 📊 第 10 分钟：完整示例

```python
# 完整的 Agent 类
class CompleteAgent:
    """完整 Agent：工具 + 记忆 + 错误处理"""
    
    def __init__(self):
        self.history = deque(maxlen=10)
        self.tools = {}
        self.max_retries = 3
    
    def add_tool(self, name: str, func):
        """添加工具"""
        self.tools[name] = func
    
    def run(self, task: str) -> str:
        """运行"""
        # 重试机制
        for i in range(self.max_retries):
            try:
                # 记录输入
                self.history.append({"role": "user", "content": task})
                
                # 检查是否需要工具
                result = self._execute(task)
                
                # 记录输出
                self.history.append({"role": "assistant", "content": result})
                
                return result
            
            except Exception as e:
                if i == self.max_retries - 1:
                    return f"Error: {e}"
                time.sleep(2 ** i)
        
        return "Failed"
    
    def _execute(self, task: str) -> str:
        """执行任务"""
        # 检查工具
        for tool_name, tool_func in self.tools.items():
            if tool_name in task.lower():
                return tool_func(task)
        
        # 调用 LLM
        response = client.chat.completions.create(
            model="gpt-4",
            messages=list(self.history)
        )
        
        return response.choices[0].message.content

# 使用
agent = CompleteAgent()
agent.add_tool("search", lambda q: f"Search: {q}")
agent.add_tool("calculate", lambda e: str(eval(e.split("calculate")[-1])))

print(agent.run("Search for AI news"))
print(agent.run("Calculate 123 + 456"))
```

---

## 🎯 学习成果

- ✅ 1 分钟：基础 Agent
- ✅ 2 分钟：添加工具
- ✅ 2 分钟：添加记忆
- ✅ 2 分钟：异步处理
- ✅ 2 分钟：错误处理
- ✅ 1 分钟：完整示例

**10 分钟掌握 AI Agent 开发！** 🚀

---

**生成时间**: 2026-03-27 14:45 GMT+8
