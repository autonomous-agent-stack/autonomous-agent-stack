# 🚀 Autonomous Agent Stack - 发展路线图

## 📊 当前状态（2026-03-26 09:58）

### ✅ 已实现功能

| 模块 | 状态 | 文件数 | 说明 |
|------|------|--------|------|
| **LLM 后端** | ✅ 完成 | 5 | Claude/OpenAI/GLM-5 |
| **通信总线** | ✅ 完成 | 3 | MessageBus + Event Bus |
| **编排引擎** | ✅ 完成 | 15+ | Graph Engine + MCP + HITL |
| **P4 演化闭环** | ✅ 完成 | 6 | Evolution Manager |
| **安全防御** | ✅ 完成 | 3 | AST Scanner + AppleDouble Cleaner |
| **品牌审计** | ✅ 完成 | 1 | Brand Auditor |
| **视觉网关** | ✅ 完成 | 1 | Vision Gateway |

---

## 🎯 下一步发展方向

### 🔴 P0：连贯对话系统（1-2 天）

#### 目标
实现多轮对话的上下文管理和记忆系统。

#### 核心组件

##### 1. **ConversationManager**（对话管理器）
```python
# src/autoresearch/core/conversation_manager.py

class ConversationManager:
    """多轮对话管理器"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.memory_store: MemoryStore = None
        
    async def create_session(self, user_id: str) -> str:
        """创建新会话"""
        pass
        
    async def get_context(self, session_id: str) -> ConversationContext:
        """获取对话上下文"""
        pass
        
    async def add_message(
        self,
        session_id: str,
        role: str,  # user/assistant/system
        content: str
    ):
        """添加消息到会话"""
        pass
```

##### 2. **MemoryStore**（记忆存储）
```python
# src/autoresearch/core/memory_store.py

class MemoryStore:
    """对话记忆存储"""
    
    async def save(self, session_id: str, memory: ConversationMemory):
        """保存记忆"""
        pass
        
    async def load(self, session_id: str) -> ConversationMemory:
        """加载记忆"""
        pass
        
    async def summarize(self, session_id: str) -> str:
        """总结对话历史"""
        pass
```

##### 3. **ContextWindow**（上下文窗口）
```python
# src/autoresearch/core/context_window.py

class ContextWindow:
    """滑动上下文窗口"""
    
    def __init__(self, max_tokens: int = 128000):
        self.max_tokens = max_tokens
        self.messages: List[Message] = []
        
    def add_message(self, message: Message):
        """添加消息，自动管理窗口大小"""
        pass
        
    def get_context(self) -> List[Message]:
        """获取当前上下文"""
        pass
```

#### 实施步骤

1. **创建核心类**（4 小时）
   - ConversationManager
   - MemoryStore
   - ContextWindow

2. **集成到 API**（2 小时）
   - `/api/v1/chat` 端点
   - 会话管理路由

3. **测试**（2 小时）
   - 多轮对话测试
   - 记忆持久化测试

---

### 🟡 P1：Claude CLI 集成（2-3 天）

#### 目标
将 Claude CLI 作为底层执行引擎，实现 Agent 能力。

#### 核心组件

##### 1. **ClaudeCLIAdapter**（适配器）
```python
# src/autoresearch/agents/claude_cli_adapter.py

class ClaudeCLIAdapter:
    """Claude CLI 适配器"""
    
    def __init__(self, cli_path: str = "claude"):
        self.cli_path = cli_path
        
    async def execute(
        self,
        prompt: str,
        context: Optional[ConversationContext] = None
    ) -> str:
        """执行 Claude CLI"""
        pass
        
    async def stream(
        self,
        prompt: str,
        context: Optional[ConversationContext] = None
    ) -> AsyncIterator[str]:
        """流式执行"""
        pass
```

##### 2. **ClaudeAgent**（Agent 封装）
```python
# src/autoresearch/agents/claude_agent.py

class ClaudeAgent:
    """基于 Claude CLI 的 Agent"""
    
    def __init__(self, adapter: ClaudeCLIAdapter):
        self.adapter = adapter
        self.conversation_manager = ConversationManager()
        
    async def chat(
        self,
        message: str,
        session_id: Optional[str] = None
    ) -> str:
        """对话接口"""
        pass
        
    async def execute_task(
        self,
        task: str,
        tools: Optional[List[Tool]] = None
    ) -> TaskResult:
        """执行任务"""
        pass
```

#### 实施步骤

1. **适配器实现**（4 小时）
   - CLI 调用封装
   - 流式输出处理

2. **Agent 封装**（4 小时）
   - 对话管理
   - 工具集成

3. **测试**（2 小时）
   - 端到端测试
   - 性能测试

---

### 🟡 P1：OpenSage 完整实现（3-4 天）

#### 目标
实现 OpenSage 的自生成拓扑和动态工具合成。

#### 已实现部分
- ✅ Graph Engine（图引擎）
- ✅ Node Protocol（节点协议）
- ✅ Task Decomposer（任务分解器）

#### 待实现部分

##### 1. **DynamicToolSynthesizer**（动态工具合成）
```python
# src/autoresearch/core/tool_synthesizer.py

class DynamicToolSynthesizer:
    """动态工具合成器"""
    
    async def synthesize(
        self,
        task_description: str,
        context: TaskContext
    ) -> Tool:
        """根据任务描述生成工具"""
        pass
        
    async def validate_tool(self, tool: Tool) -> bool:
        """验证生成的工具"""
        pass
```

##### 2. **SelfGeneratingTopology**（自生成拓扑）
```python
# src/autoresearch/core/topology_generator.py

class SelfGeneratingTopology:
    """自生成智能体拓扑"""
    
    async def generate(
        self,
        task: str,
        available_agents: List[Agent]
    ) -> Topology:
        """生成最优拓扑结构"""
        pass
        
    async def optimize(
        self,
        topology: Topology,
        performance_metrics: Metrics
    ) -> Topology:
        """优化拓扑"""
        pass
```

##### 3. **HierarchicalMemory**（分层记忆）
```python
# src/autoresearch/core/hierarchical_memory.py

class HierarchicalMemory:
    """分层图记忆"""
    
    def __init__(self):
        self.short_term: MemoryGraph = None  # 短期记忆
        self.long_term: MemoryGraph = None   # 长期记忆
        self.episodic: MemoryGraph = None    # 情景记忆
        
    async def store(self, experience: Experience):
        """存储经验"""
        pass
        
    async def recall(self, query: str) -> List[Experience]:
        """回忆相关经验"""
        pass
```

#### 实施步骤

1. **动态工具合成**（6 小时）
2. **自生成拓扑**（6 小时）
3. **分层记忆**（8 小时）
4. **测试**（4 小时）

---

### 🟢 P2：MAS Factory 编排（3-5 天）

#### 目标
使用 MASFactory 实现多智能体协同编排。

#### 核心组件

##### 1. **MASFactoryBridge**（桥接器）
```python
# src/autoresearch/orchestration/masfactory_bridge.py

class MASFactoryBridge:
    """MASFactory 桥接器"""
    
    def __init__(self, mas_config: MASConfig):
        self.config = mas_config
        
    async def create_agent(
        self,
        agent_spec: AgentSpec
    ) -> MASAgent:
        """创建 MAS Agent"""
        pass
        
    async def orchestrate(
        self,
        task: str,
        agents: List[MASAgent]
    ) -> OrchestrationResult:
        """编排多智能体协同"""
        pass
```

##### 2. **AgentOrchestrator**（编排器）
```python
# src/autoresearch/orchestration/agent_orchestrator.py

class AgentOrchestrator:
    """智能体编排器"""
    
    async def plan(
        self,
        task: str
    ) -> OrchestrationPlan:
        """规划编排方案"""
        pass
        
    async def execute(
        self,
        plan: OrchestrationPlan
    ) -> OrchestrationResult:
        """执行编排"""
        pass
        
    async def monitor(
        self,
        execution_id: str
    ) -> ExecutionStatus:
        """监控执行状态"""
        pass
```

##### 3. **ConflictResolver**（冲突解决）
```python
# src/autoresearch/orchestration/conflict_resolver.py

class ConflictResolver:
    """智能体冲突解决器"""
    
    async def detect(
        self,
        agent_outputs: List[AgentOutput]
    ) -> List[Conflict]:
        """检测冲突"""
        pass
        
    async def resolve(
        self,
        conflicts: List[Conflict]
    ) -> Resolution:
        """解决冲突"""
        pass
```

#### 实施步骤

1. **MASFactory 集成**（6 小时）
2. **编排器实现**（8 小时）
3. **冲突解决**（6 小时）
4. **测试**（4 小时）

---

## 📋 优先级建议

### 🔴 立即开始（本周）

**P0：连贯对话系统**
- 原因：这是所有功能的基础
- 时间：1-2 天
- 产出：可用的多轮对话系统

### 🟡 近期规划（下周）

**P1：Claude CLI 集成 + OpenSage 完整实现**
- 原因：增强 Agent 能力
- 时间：5-7 天
- 产出：强大的 Agent 执行引擎

### 🟢 中期规划（2-3 周后）

**P2：MAS Factory 编排**
- 原因：实现多智能体协同
- 时间：3-5 天
- 产出：企业级编排系统

---

## 🎯 快速启动方案

### 方案 A：最小可用版本（MVP）

**今天完成**：
1. ✅ ConversationManager（2 小时）
2. ✅ MemoryStore（1 小时）
3. ✅ API 端点（1 小时）
4. ✅ 测试（1 小时）

**明天完成**：
1. ✅ Claude CLI 集成（4 小时）
2. ✅ Agent 封装（4 小时）

**产出**：可用的对话 + Agent 系统

---

### 方案 B：完整实现（1 周）

**Day 1-2**：连贯对话系统
**Day 3-4**：Claude CLI 集成
**Day 5-7**：OpenSage 完整实现

**产出**：生产级 Agent 平台

---

## 📊 技术栈

| 组件 | 技术选择 | 原因 |
|------|---------|------|
| **对话管理** | SQLite + Memory | 简单可靠 |
| **Agent 执行** | Claude CLI | 官方工具，稳定 |
| **编排引擎** | MASFactory | 成熟的开源方案 |
| **记忆系统** | Graph RAG | 支持复杂查询 |

---

## 🚀 下一步行动

**大佬，你希望我：**

1. **立即开始 P0（连贯对话系统）** ✅ 推荐
   - 今天完成核心类
   - 明天完成 API 集成

2. **先做 Claude CLI 集成**
   - 快速验证 Agent 能力
   - 后续再补充对话管理

3. **优先实现 OpenSage 完整功能**
   - 实现自生成拓扑
   - 动态工具合成

**请选择：1 / 2 / 3 或其他指令** 🤔

---

**创建时间**: 2026-03-26 09:58 GMT+8
