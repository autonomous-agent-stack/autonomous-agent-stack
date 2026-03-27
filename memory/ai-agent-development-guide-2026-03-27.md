# AI Agent 开发实战指南 - 从 0 到 1

> **创建时间**：2026-03-27 17:20 GMT+8
> **目标读者**：开发者
> **难度**：中级
> **预计时间**：2-4 小时

---

## 📋 目录

1. [快速开始](#快速开始)
2. [核心概念](#核心概念)
3. [基础实现](#基础实现)
4. [进阶功能](#进阶功能)
5. [生产部署](#生产部署)
6. [最佳实践](#最佳实践)

---

## 🚀 快速开始

### 最小可行 Agent（5 分钟）

```python
# minimal_agent.py
from openai import OpenAI

class MinimalAgent:
    def __init__(self, api_key):
        self.client = OpenAI(api_key=api_key)
    
    def run(self, task):
        """执行任务"""
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一个有用的 AI 助手。"},
                {"role": "user", "content": task}
            ]
        )
        return response.choices[0].message.content

# 使用示例
agent = MinimalAgent(api_key="your-api-key")
result = agent.run("帮我写一个 Python 函数，计算斐波那契数列")
print(result)
```

**运行**：
```bash
python minimal_agent.py
```

---

## 🧠 核心概念

### 1. Agent 定义

**什么是 AI Agent？**

```python
class Agent:
    """
    AI Agent 核心定义
    
    特征：
    1. 感知环境（Perception）
    2. 做出决策（Decision）
    3. 执行行动（Action）
    4. 学习改进（Learning）
    """
    
    def perceive(self, environment):
        """感知环境"""
        pass
    
    def decide(self, perception):
        """做出决策"""
        pass
    
    def act(self, decision):
        """执行行动"""
        pass
    
    def learn(self, experience):
        """学习改进"""
        pass
```

### 2. 核心组件

```python
# 组件图
"""
┌─────────────────────────────────────────┐
│            AI Agent Architecture          │
├─────────────────────────────────────────┤
│                                           │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │  Memory  │  │ Planning │  │ Actions ││
│  │          │◄─┤          │◄─┤         ││
│  └──────────┘  └──────────┘  └─────────┘│
│       ▲              │              ▲   │
│       │              │              │   │
│       ▼              ▼              ▼   │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │   LLM    │  │  Tools   │  │ Feedback││
│  │          │  │          │  │         ││
│  └──────────┘  └──────────┘  └─────────┘│
│                                           │
└─────────────────────────────────────────┘
"""
```

---

## 🏗️ 基础实现

### 完整的 Agent 类

```python
# agent.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json

@dataclass
class Message:
    role: str
    content: str

class Agent:
    def __init__(
        self,
        name: str,
        llm_client,
        system_prompt: str = "你是一个有用的 AI 助手。",
        tools: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.llm = llm_client
        self.system_prompt = system_prompt
        self.tools = tools or {}
        self.memory: List[Message] = []
    
    def add_to_memory(self, role: str, content: str):
        """添加到记忆"""
        self.memory.append(Message(role=role, content=content))
    
    def get_context(self) -> List[Dict[str, str]]:
        """获取上下文"""
        context = [{"role": "system", "content": self.system_prompt}]
        context.extend([{"role": m.role, "content": m.content} for m in self.memory])
        return context
    
    def think(self, user_input: str) -> str:
        """思考（调用 LLM）"""
        self.add_to_memory("user", user_input)
        
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=self.get_context()
        )
        
        assistant_message = response.choices[0].message.content
        self.add_to_memory("assistant", assistant_message)
        
        return assistant_message
    
    def use_tool(self, tool_name: str, tool_input: Any) -> Any:
        """使用工具"""
        if tool_name not in self.tools:
            raise ValueError(f"工具 {tool_name} 不存在")
        
        return self.tools[tool_name](tool_input)
    
    def run(self, task: str) -> str:
        """运行 Agent"""
        return self.think(task)

# 使用示例
from openai import OpenAI

client = OpenAI(api_key="your-api-key")

agent = Agent(
    name="助手",
    llm_client=client,
    system_prompt="你是一个专业的 Python 开发助手。"
)

result = agent.run("帮我写一个排序算法")
print(result)
```

---

## 🔧 进阶功能

### 1. 工具调用（Tool Use）

```python
# tools.py
import json
from typing import Callable, Dict, Any

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.schemas: Dict[str, Dict] = {}
    
    def register(self, name: str, func: Callable, schema: Dict):
        """注册工具"""
        self.tools[name] = func
        self.schemas[name] = schema
    
    def get_tool_definitions(self) -> List[Dict]:
        """获取工具定义（用于 LLM）"""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    **schema
                }
            }
            for name, schema in self.schemas.items()
        ]
    
    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """执行工具"""
        return self.tools[name](**arguments)

# 定义工具
def search_web(query: str) -> str:
    """搜索网页"""
    # 实现搜索逻辑
    return f"搜索结果：{query}"

def execute_code(code: str) -> str:
    """执行代码"""
    try:
        exec(code)
        return "代码执行成功"
    except Exception as e:
        return f"执行失败：{e}"

# 注册工具
registry = ToolRegistry()
registry.register(
    name="search_web",
    func=search_web,
    schema={
        "description": "搜索网页内容",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词"
                }
            },
            "required": ["query"]
        }
    }
)

registry.register(
    name="execute_code",
    func=execute_code,
    schema={
        "description": "执行 Python 代码",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的代码"
                }
            },
            "required": ["code"]
        }
    }
)

# 带 Tool Use 的 Agent
class ToolAgent(Agent):
    def __init__(self, *args, tool_registry: ToolRegistry, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool_registry = tool_registry
    
    def think_with_tools(self, user_input: str) -> str:
        """带工具的思考"""
        self.add_to_memory("user", user_input)
        
        # 第一次调用：决定是否使用工具
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=self.get_context(),
            tools=self.tool_registry.get_tool_definitions(),
            tool_choice="auto"
        )
        
        message = response.choices[0].message
        
        # 如果需要调用工具
        if message.tool_calls:
            # 执行工具
            tool_results = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                result = self.tool_registry.execute(function_name, arguments)
                tool_results.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "content": str(result)
                })
            
            # 添加工具结果到上下文
            self.memory.append(Message(role="assistant", content=message.content or ""))
            for result in tool_results:
                self.add_to_memory("tool", result["content"])
            
            # 第二次调用：基于工具结果生成最终回答
            final_response = self.llm.chat.completions.create(
                model="gpt-4",
                messages=self.get_context()
            )
            
            final_message = final_response.choices[0].message.content
            self.add_to_memory("assistant", final_message)
            return final_message
        
        # 不需要工具，直接返回
        self.add_to_memory("assistant", message.content)
        return message.content

# 使用示例
agent = ToolAgent(
    name="工具助手",
    llm_client=client,
    tool_registry=registry
)

result = agent.think_with_tools("帮我搜索一下最新的 AI 新闻")
print(result)
```

### 2. 记忆系统（Memory）

```python
# memory.py
from typing import List, Dict, Any
import json
from datetime import datetime

class Memory:
    def __init__(self, max_short_term: int = 10):
        self.short_term: List[Dict[str, Any]] = []
        self.long_term: List[Dict[str, Any]] = []
        self.max_short_term = max_short_term
    
    def add(self, role: str, content: str, metadata: Dict = None):
        """添加记忆"""
        memory_item = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        self.short_term.append(memory_item)
        
        # 如果超过容量，移动到长期记忆
        if len(self.short_term) > self.max_short_term:
            self.long_term.append(self.short_term.pop(0))
    
    def get_recent(self, n: int = 5) -> List[Dict]:
        """获取最近的记忆"""
        return self.short_term[-n:]
    
    def search(self, query: str) -> List[Dict]:
        """搜索记忆"""
        results = []
        for item in self.short_term + self.long_term:
            if query.lower() in item["content"].lower():
                results.append(item)
        return results
    
    def save(self, filepath: str):
        """保存到文件"""
        data = {
            "short_term": self.short_term,
            "long_term": self.long_term
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self, filepath: str):
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.short_term = data.get("short_term", [])
        self.long_term = data.get("long_term", [])

# 带记忆的 Agent
class MemoryAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory_system = Memory()
    
    def think_with_memory(self, user_input: str) -> str:
        """带记忆的思考"""
        # 搜索相关记忆
        relevant_memories = self.memory_system.search(user_input)
        
        # 构建上下文（包含相关记忆）
        context = self.get_context()
        if relevant_memories:
            memory_context = "\n".join([
                f"[{m['timestamp']}] {m['role']}: {m['content']}"
                for m in relevant_memories[-3:]  # 最多 3 条
            ])
            context.insert(1, {
                "role": "system",
                "content": f"相关历史记忆：\n{memory_context}"
            })
        
        # 调用 LLM
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=context
        )
        
        result = response.choices[0].message.content
        
        # 保存到记忆
        self.memory_system.add("user", user_input)
        self.memory_system.add("assistant", result)
        
        return result
```

### 3. 多 Agent 协作

```python
# multi_agent.py
from typing import List, Dict
import asyncio

class MultiAgentSystem:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.communication_log: List[Dict] = []
    
    def add_agent(self, name: str, agent: Agent):
        """添加 Agent"""
        self.agents[name] = agent
    
    def broadcast(self, sender: str, message: str):
        """广播消息"""
        for name, agent in self.agents.items():
            if name != sender:
                self.communication_log.append({
                    "from": sender,
                    "to": name,
                    "message": message,
                    "timestamp": datetime.now().isoformat()
                })
    
    def collaborative_task(self, task: str, roles: List[str]) -> str:
        """协作任务"""
        results = {}
        
        for role in roles:
            if role not in self.agents:
                continue
            
            agent = self.agents[role]
            result = agent.run(task)
            results[role] = result
            
            # 广播结果给其他 Agent
            self.broadcast(role, result)
        
        # 综合结果
        final_result = self._synthesize_results(results)
        return final_result
    
    def _synthesize_results(self, results: Dict[str, str]) -> str:
        """综合结果"""
        synthesis = "综合各 Agent 的意见：\n\n"
        for role, result in results.items():
            synthesis += f"**{role}**：\n{result}\n\n"
        return synthesis

# 使用示例
system = MultiAgentSystem()

# 添加不同角色的 Agent
system.add_agent("开发者", Agent(
    name="开发者",
    llm_client=client,
    system_prompt="你是一个经验丰富的软件工程师，专注于技术实现。"
))

system.add_agent("产品经理", Agent(
    name="产品经理",
    llm_client=client,
    system_prompt="你是一个产品经理，关注用户需求和产品价值。"
))

system.add_agent("设计师", Agent(
    name="设计师",
    llm_client=client,
    system_prompt="你是一个 UI/UX 设计师，关注用户体验和界面设计。"
))

# 执行协作任务
result = system.collaborative_task(
    "设计一个待办事项应用",
    ["开发者", "产品经理", "设计师"]
)
print(result)
```

---

## 🚀 生产部署

### 1. API 服务

```python
# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="AI Agent API")

class TaskRequest(BaseModel):
    task: str
    agent_name: str = "default"

class TaskResponse(BaseModel):
    result: str
    agent_name: str
    execution_time: float

# 初始化 Agent
agents = {
    "default": Agent(
        name="默认助手",
        llm_client=client,
        system_prompt="你是一个有用的 AI 助手。"
    ),
    "coder": Agent(
        name="代码助手",
        llm_client=client,
        system_prompt="你是一个专业的程序员助手。"
    )
}

@app.post("/run", response_model=TaskResponse)
async def run_agent(request: TaskRequest):
    """运行 Agent"""
    import time
    start_time = time.time()
    
    if request.agent_name not in agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent = agents[request.agent_name]
    result = agent.run(request.task)
    
    execution_time = time.time() - start_time
    
    return TaskResponse(
        result=result,
        agent_name=request.agent_name,
        execution_time=execution_time
    )

@app.get("/agents")
async def list_agents():
    """列出所有 Agent"""
    return {"agents": list(agents.keys())}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**运行**：
```bash
python api.py
```

**测试**：
```bash
curl -X POST "http://localhost:8000/run" \
  -H "Content-Type: application/json" \
  -d '{"task": "写一个 Hello World 程序", "agent_name": "coder"}'
```

### 2. 监控和日志

```python
# monitoring.py
import logging
from datetime import datetime
from typing import Dict, Any
import json

class AgentMonitor:
    def __init__(self, log_file: str = "agent.log"):
        self.logger = logging.getLogger("AgentMonitor")
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.INFO)
        
        # 控制台处理器
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        self.metrics: Dict[str, Any] = {
            "total_requests": 0,
            "total_tokens": 0,
            "total_time": 0,
            "errors": 0
        }
    
    def log_request(self, agent_name: str, task: str):
        """记录请求"""
        self.logger.info(f"Agent: {agent_name}, Task: {task}")
        self.metrics["total_requests"] += 1
    
    def log_response(self, agent_name: str, result: str, tokens: int, time: float):
        """记录响应"""
        self.logger.info(f"Agent: {agent_name}, Tokens: {tokens}, Time: {time:.2f}s")
        self.metrics["total_tokens"] += tokens
        self.metrics["total_time"] += time
    
    def log_error(self, agent_name: str, error: str):
        """记录错误"""
        self.logger.error(f"Agent: {agent_name}, Error: {error}")
        self.metrics["errors"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return self.metrics

# 使用示例
monitor = AgentMonitor()

class MonitoredAgent(Agent):
    def __init__(self, *args, monitor: AgentMonitor, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = monitor
    
    def run(self, task: str) -> str:
        import time
        start_time = time.time()
        
        self.monitor.log_request(self.name, task)
        
        try:
            result = super().run(task)
            execution_time = time.time() - start_time
            tokens = len(task.split()) + len(result.split())  # 简化估算
            
            self.monitor.log_response(self.name, result, tokens, execution_time)
            return result
        
        except Exception as e:
            self.monitor.log_error(self.name, str(e))
            raise

# 使用监控 Agent
agent = MonitoredAgent(
    name="监控助手",
    llm_client=client,
    monitor=monitor
)

result = agent.run("你好")
print(monitor.get_metrics())
```

---

## 💡 最佳实践

### 1. 错误处理

```python
class RobustAgent(Agent):
    def run(self, task: str, max_retries: int = 3) -> str:
        """带重试的执行"""
        for attempt in range(max_retries):
            try:
                return super().run(task)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                print(f"尝试 {attempt + 1} 失败：{e}，正在重试...")
                time.sleep(2 ** attempt)  # 指数退避
```

### 2. 成本控制

```python
class CostControlledAgent(Agent):
    def __init__(self, *args, max_tokens_per_day: int = 100000, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_tokens = max_tokens_per_day
        self.used_tokens = 0
    
    def run(self, task: str) -> str:
        # 估算 token 数
        estimated_tokens = len(task.split()) * 1.3
        
        if self.used_tokens + estimated_tokens > self.max_tokens:
            raise ValueError("已达到今日 token 限制")
        
        result = super().run(task)
        
        # 更新使用量
        self.used_tokens += estimated_tokens + len(result.split()) * 1.3
        
        return result
```

### 3. 安全性

```python
class SecureAgent(Agent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.banned_words = ["password", "secret", "token"]
    
    def run(self, task: str) -> str:
        # 检查输入
        if any(word in task.lower() for word in self.banned_words):
            raise ValueError("输入包含敏感信息")
        
        result = super().run(task)
        
        # 检查输出
        if any(word in result.lower() for word in self.banned_words):
            return "[输出已过滤]"
        
        return result
```

---

## 📚 完整示例项目

### 项目结构

```
my_agent/
├── agent/
│   ├── __init__.py
│   ├── core.py          # 核心 Agent 类
│   ├── memory.py        # 记忆系统
│   ├── tools.py         # 工具注册
│   └── monitoring.py    # 监控系统
├── api/
│   ├── __init__.py
│   └── server.py        # API 服务器
├── tests/
│   ├── test_agent.py
│   └── test_tools.py
├── requirements.txt
└── README.md
```

### requirements.txt

```
openai>=1.0.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
```

---

## 🎯 学习路径

### 第 1 周：基础
- Day 1-2：理解 Agent 概念
- Day 3-4：实现最小 Agent
- Day 5-7：添加记忆和工具

### 第 2 周：进阶
- Day 1-3：多 Agent 协作
- Day 4-5：API 部署
- Day 6-7：监控和优化

### 第 3 周：生产
- Day 1-3：错误处理和重试
- Day 4-5：成本控制
- Day 6-7：安全性加固

---

## 🔗 参考资源

- [OpenAI API 文档](https://platform.openai.com/docs)
- [LangChain 文档](https://python.langchain.com/docs)
- [AutoGen 论文](https://arxiv.org/abs/2308.08155)
- [CrewAI 文档](https://docs.crewai.com)

---

**创建者**：小lin 🤖
**类型**：实战指南
**难度**：中级
**更新时间**：2026-03-27
