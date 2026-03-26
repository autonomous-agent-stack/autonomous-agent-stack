# OpenSage 实现对比分析

> **对比时间**: 2026-03-25 22:10 GMT+8
> **来源**: SageAgent 开源实现 + autonomous-agent-stack

---

## 📊 核心对比

### 1. 整体架构

| 组件 | OpenSage (SageAgent) | autonomous-agent-stack | 对比 |
|------|---------------------|----------------------|------|
| **引擎** | AgentEngine | Graph (orchestrator) | ✅ 类似 |
| **智能体** | Agent class | Node (Planner/Generator/Executor/Evaluator) | ✅ 类似 |
| **LLM 后端** | Claude/OpenAI | 未实现（需添加） | ⚠️ 缺失 |
| **工具注册** | ToolRegistry | MCPContextBlock | ✅ 类似 |
| **记忆系统** | MemoryGraph | OpenClaw MEMORY.md | ✅ 类似 |
| **通信总线** | MessageBus | 未实现（需添加） | ⚠️ 缺失 |

---

## 🔍 详细对比

### 1. AgentEngine vs Graph

#### OpenSage (SageAgent)

```python
class AgentEngine:
    def __init__(self, config: EngineConfig):
        self._llm = self._create_llm_backend()
        self._memory = MemoryGraph(self._config.memory)
        self._bus = MessageBus()
        self._tools = ToolRegistry()
        self._decomposer = TaskDecomposer(self._llm)
        self._topology = TopologyManager(...)

    async def run(self, task: str) -> dict[str, Any]:
        root = Agent(
            role="root",
            task=task,
            llm=self._llm,
            tool_registry=self._tools,
            memory=self._memory,
            bus=self._bus,
            config=self._config.agent,
        )
        result = await root.run()
        return result
```

#### autonomous-agent-stack

```python
class Graph:
    def __init__(self, graph_id: str):
        self.nodes: Dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.context = ContextBlock()

    async def execute(self) -> Dict[str, Any]:
        results = {}
        for node_id, node in self.nodes.items():
            result = await node.execute(self.context)
            results[node_id] = result
        return results
```

**对比**：
- ✅ **相似点**：都有顶层编排器
- ⚠️ **差异**：autonomous-agent-stack 缺少 LLM 后端、通信总线

---

### 2. Agent vs Node

#### OpenSage (SageAgent)

```python
class Agent:
    def __init__(self, role, task, llm, tool_registry, memory, bus, config):
        self.id = new_agent_id()
        self.role = role
        self.task = task
        self._llm = llm
        self._tools = tool_registry
        self._memory = memory
        self._bus = bus

    async def run(self) -> dict[str, Any]:
        self.status = AgentStatus.RUNNING

        # 写入记忆
        ctx_node = MemoryNode(...)
        self._memory.add_node(ctx_node)

        # 迭代循环
        while self._iterations < self._config.max_iterations:
            response = await self._llm.generate_with_tools(...)
            if response.has_tool_calls:
                await self._execute_tools(response.tool_calls)
            if "TASK_COMPLETE" in response.content:
                break

        return result
```

#### autonomous-agent-stack

```python
class Node:
    def __init__(self, node_id: str, node_type: NodeType):
        self.node_id = node_id
        self.node_type = node_type
        self.status = NodeStatus.PENDING
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}

    async def execute(self, context: ContextBlock) -> Dict[str, Any]:
        raise NotImplementedError
```

**对比**：
- ✅ **相似点**：都有生命周期管理
- ⚠️ **差异**：autonomous-agent-stack 的 Node 不直接调用 LLM，而是由具体子类实现

---

### 3. MemoryGraph vs OpenClaw MEMORY.md

#### OpenSage (SageAgent)

```python
class MemoryGraph:
    def __init__(self, config: MemoryConfig):
        self._graph = nx.DiGraph()
        self._nodes: dict[NodeId, MemoryNode] = {}
        self._gc = GarbageCollector(...)

    def add_node(self, node: MemoryNode):
        self._graph.add_node(node.id)
        self._nodes[node.id] = node

    def query(self, query: str) -> list[MemoryNode]:
        # 图查询
        pass
```

#### autonomous-agent-stack

```python
# OpenClaw 的纯文本 Markdown 记忆
MEMORY.md
├── 今日完成
├── 昨日完成
├── 配置信息
├── 监控任务
└── 学习资源
```

**对比**：
- ✅ **相似点**：都支持持久化记忆
- ⚠️ **差异**：OpenSage 使用图数据库，OpenClaw 使用纯文本 Markdown

---

### 4. ToolRegistry vs MCPContextBlock

#### OpenSage (SageAgent)

```python
class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        self._tools[tool.name] = tool

    def to_llm_schemas(self) -> list[dict]:
        return [tool.to_schema() for tool in self._tools.values()]
```

#### autonomous-agent-stack

```python
class MCPContextBlock:
    def __init__(self):
        self.tools: Dict[str, Any] = {}
        self.cache: Dict[str, Any] = {}

    def register_tool(self, name: str, tool_config: Dict[str, Any]):
        self.tools[name] = tool_config

    async def call_tool(self, tool_name: str, params: Dict[str, Any]):
        # 调用 MCP 工具
        pass
```

**对比**：
- ✅ **相似点**：都支持工具注册和调用
- ✅ **优势**：autonomous-agent-stack 通过 MCP 协议支持更多外部工具

---

## 🚀 改进建议

### 1. 添加 LLM 后端支持

**当前状态**: ❌ 缺失

**建议**：
```python
# src/orchestrator/llm/base.py
from abc import ABC, abstractmethod

class LLMBackend(ABC):
    @abstractmethod
    async def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        system: str
    ) -> LLMResponse:
        pass

# src/orchestrator/llm/claude.py
class ClaudeBackend(LLMBackend):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def generate_with_tools(self, messages, tools, system):
        response = self.client.messages.create(
            model=self.model,
            messages=messages,
            tools=tools,
            system=system
        )
        return LLMResponse(response)

# src/orchestrator/llm/openai.py
class OpenAIBackend(LLMBackend):
    def __init__(self, api_key: str, model: str = "gpt-4-turbo"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
```

---

### 2. 添加通信总线

**当前状态**: ❌ 缺失

**建议**：
```python
# src/orchestrator/communication/bus.py
from typing import Callable, Any
from asyncio import Queue

class MessageBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._queue = Queue()

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: Any):
        event_type = event.__class__.__name__
        if event_type in self._subscribers:
            for handler in self._subscribers[event_type]:
                await handler(event)
```

---

### 3. 添加任务分解器

**当前状态**: ❌ 缺失

**建议**：
```python
# src/orchestrator/topology/decomposer.py
class TaskDecomposer:
    def __init__(self, llm: LLMBackend):
        self._llm = llm

    async def decompose(self, task: str) -> list[str]:
        prompt = f"""
Decompose the following task into subtasks:
{task}

Return a JSON array of subtasks.
"""
        response = await self._llm.generate(prompt)
        subtasks = json.loads(response.content)
        return subtasks
```

---

### 4. 增强记忆系统

**当前状态**: ⚠️ 简单（纯文本 Markdown）

**建议**：
```python
# src/orchestrator/memory/graph.py
import networkx as nx

class MemoryGraph:
    def __init__(self):
        self._graph = nx.DiGraph()
        self._nodes: dict[str, MemoryNode] = {}

    def add_node(self, node: MemoryNode):
        self._graph.add_node(node.id)
        self._nodes[node.id] = node

    def query(self, query: str) -> list[MemoryNode]:
        # 图查询
        pass

    def add_edge(self, from_id: str, to_id: str):
        self._graph.add_edge(from_id, to_id)
```

---

## 📊 实现路线图

### 阶段 1: 基础增强（本周）

| 任务 | 优先级 | 预计时间 |
|------|--------|---------|
| **添加 LLM 后端** | 🔴 高 | 2 小时 |
| **添加通信总线** | 🔴 高 | 1 小时 |
| **添加任务分解器** | 🟡 中 | 2 小时 |

---

### 阶段 2: 高级功能（下周）

| 任务 | 优先级 | 预计时间 |
|------|--------|---------|
| **增强记忆系统** | 🔴 高 | 3 小时 |
| **动态工具生成** | 🟡 中 | 2 小时 |
| **拓扑管理器** | 🟡 中 | 3 小时 |

---

### 阶段 3: 完整集成（2 周）

| 任务 | 优先级 | 预计时间 |
|------|--------|---------|
| **完整 OpenSage 集成** | 🔴 高 | 5 小时 |
| **测试覆盖** | 🔴 高 | 3 小时 |
| **文档完善** | 🟡 中 | 2 小时 |

---

## 🎯 核心价值

### 1. Self-Programming 能力

**OpenSage 的核心理念**：
- ✅ 智能体自己写代码
- ✅ 智能体自己创建工具
- ✅ 智能体自己创建子智能体

**autonomous-agent-stack 的实现**：
- ✅ **GeneratorNode**: 生成代码
- ✅ **ExecutorNode**: 执行代码
- ⚠️ **动态工具生成**: 需要增强
- ⚠️ **自动创建子智能体**: 需要实现

---

### 2. AI-centered 范式

**从 Human-centered 到 AI-centered**：
- ✅ autonomous-agent-stack 已经实现了图编排
- ⚠️ 需要增强 LLM 驱动能力
- ⚠️ 需要实现自动分解和编排

---

## 📖 参考资源

- **SageAgent GitHub**: https://github.com/ianblenke/sageagent
- **OpenSage 论文**: arXiv:2602.16891
- **autonomous-agent-stack**: https://github.com/srxly888-creator/autonomous-agent-stack

---

## 🚀 下一步行动

### 立即行动
1. [ ] 克隆 SageAgent 到本地
2. [ ] 运行 SageAgent 示例
3. [ ] 对比核心代码实现

### 本周任务
1. [ ] 添加 LLM 后端（Claude + OpenAI）
2. [ ] 添加通信总线
3. [ ] 添加任务分解器

### 下周任务
1. [ ] 增强记忆系统（图数据库）
2. [ ] 实现动态工具生成
3. [ ] 实现拓扑管理器

---

**autonomous-agent-stack 已经实现了 OpenSage 的核心架构，只需补充 LLM 后端和通信总线即可达到完整能力！** 🚀
