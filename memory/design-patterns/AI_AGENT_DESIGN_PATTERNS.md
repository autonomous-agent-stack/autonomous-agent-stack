# AI Agent 高级设计模式

> **版本**: v1.0
> **更新时间**: 2026-03-27 13:45
> **设计模式**: 15+

---

## 🎯 核心设计模式

### 1. ReAct 模式（Reasoning + Acting）

**用途**: 交替思考和行动

**实现**:
```python
class ReActAgent:
    """ReAct Agent"""
    
    def run(self, task: str) -> str:
        for _ in range(self.max_iterations):
            # 1. Thought
            thought = self._think(task)
            
            # 2. Action
            action = self._decide_action(thought)
            
            # 3. Execute
            if action["type"] == "finish":
                return action["answer"]
            
            # 4. Observation
            observation = self._execute_action(action)
            
            # 5. Update context
            task = self._update_context(task, thought, action, observation)
        
        return "超过最大轮数"
    
    def _think(self, context: str) -> str:
        """思考"""
        prompt = f"""Context: {context}

What should I think about next?"""
        return self.llm.call(prompt)
    
    def _decide_action(self, thought: str) -> dict:
        """决定行动"""
        prompt = f"""Thought: {thought}

Choose an action:
1. search[query]
2. calculate[expression]
3. finish[answer]

Action:"""
        action_text = self.llm.call(prompt)
        return self._parse_action(action_text)
```

---

### 2. Plan-and-Execute 模式

**用途**: 先规划再执行

**实现**:
```python
class PlanExecuteAgent:
    """Plan-and-Execute Agent"""
    
    def run(self, task: str) -> str:
        # 1. Planning
        plan = self._plan(task)
        
        # 2. Execute
        results = []
        for step in plan.steps:
            result = self._execute_step(step)
            results.append(result)
            
            # 3. Replan if needed
            if self._needs_replan(result):
                plan = self._replan(task, results)
        
        # 4. Finalize
        return self._finalize(results)
    
    def _plan(self, task: str) -> Plan:
        """制定计划"""
        prompt = f"""Task: {task}

Create a step-by-step plan:
1. ...
2. ...
3. ..."""
        
        plan_text = self.llm.call(prompt)
        return self._parse_plan(plan_text)
    
    def _execute_step(self, step: str) -> str:
        """执行步骤"""
        return self.llm.call(step)
    
    def _needs_replan(self, result: str) -> bool:
        """是否需要重新规划"""
        return "failed" in result.lower()
```

---

### 3. Reflection 模式

**用途**: 自我反思和改进

**实现**:
```python
class ReflectionAgent:
    """Reflection Agent"""
    
    def run(self, task: str) -> str:
        # 1. Initial attempt
        draft = self._generate(task)
        
        # 2. Reflect
        reflection = self._reflect(task, draft)
        
        # 3. Improve
        improved = self._improve(task, draft, reflection)
        
        return improved
    
    def _generate(self, task: str) -> str:
        """生成初稿"""
        return self.llm.call(task)
    
    def _reflect(self, task: str, draft: str) -> str:
        """反思"""
        prompt = f"""Task: {task}
Draft: {draft}

Critique this draft:
1. What's good?
2. What's missing?
3. What can be improved?"""
        
        return self.llm.call(prompt)
    
    def _improve(self, task: str, draft: str, reflection: str) -> str:
        """改进"""
        prompt = f"""Task: {task}
Draft: {draft}
Reflection: {reflection}

Create an improved version:"""
        
        return self.llm.call(prompt)
```

---

### 4. Multi-Agent 协作模式

**用途**: 多 Agent 分工协作

**实现**:
```python
class MultiAgentSystem:
    """多 Agent 系统"""
    
    def __init__(self):
        self.agents = {
            "planner": PlannerAgent(),
            "researcher": ResearcherAgent(),
            "writer": WriterAgent(),
            "reviewer": ReviewerAgent()
        }
    
    def run(self, task: str) -> str:
        # 1. Planning
        plan = self.agents["planner"].run(task)
        
        # 2. Research
        research = self.agents["researcher"].run(plan)
        
        # 3. Writing
        draft = self.agents["writer"].run(research)
        
        # 4. Review
        review = self.agents["reviewer"].run(draft)
        
        # 5. Iteration
        if review["needs_revision"]:
            draft = self._revise(draft, review)
        
        return draft
    
    def _revise(self, draft: str, review: dict) -> str:
        """修订"""
        prompt = f"""Draft: {draft}
Review: {review}

Revise the draft:"""
        
        return self.agents["writer"].run(prompt)
```

---

### 5. Tool Learning 模式

**用途**: 学习使用新工具

**实现**:
```python
class ToolLearningAgent:
    """工具学习 Agent"""
    
    def __init__(self):
        self.tools = {}
        self.tool_examples = {}
    
    def learn_tool(self, tool_name: str, examples: List[dict]):
        """学习工具"""
        # 1. 分析示例
        analysis = self._analyze_examples(examples)
        
        # 2. 生成使用规则
        rules = self._generate_rules(analysis)
        
        # 3. 存储知识
        self.tools[tool_name] = {
            "analysis": analysis,
            "rules": rules,
            "examples": examples
        }
    
    def use_tool(self, tool_name: str, context: str) -> dict:
        """使用工具"""
        # 1. 检索知识
        knowledge = self.tools.get(tool_name)
        
        if not knowledge:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # 2. 生成参数
        params = self._generate_params(context, knowledge["rules"])
        
        # 3. 执行工具
        result = self._execute_tool(tool_name, params)
        
        return result
    
    def _analyze_examples(self, examples: List[dict]) -> str:
        """分析示例"""
        prompt = f"""Examples: {examples}

Analyze the pattern:
1. When to use this tool?
2. What parameters are needed?
3. What's the expected output?"""
        
        return self.llm.call(prompt)
```

---

### 6. Memory-Augmented 模式

**用途**: 增强记忆能力

**实现**:
```python
class MemoryAugmentedAgent:
    """记忆增强 Agent"""
    
    def __init__(self):
        # 短期记忆
        self.short_term = deque(maxlen=10)
        
        # 长期记忆（向量数据库）
        self.long_term = VectorDB()
        
        # 工作记忆
        self.working = {}
    
    def run(self, task: str) -> str:
        # 1. 检索相关记忆
        relevant = self._retrieve_memories(task)
        
        # 2. 构建上下文
        context = self._build_context(task, relevant)
        
        # 3. 执行任务
        result = self._execute(context)
        
        # 4. 存储记忆
        self._store_memory(task, result)
        
        return result
    
    def _retrieve_memories(self, query: str) -> List[str]:
        """检索记忆"""
        # 从短期记忆检索
        recent = list(self.short_term)
        
        # 从长期记忆检索
        relevant = self.long_term.search(query, n_results=5)
        
        return recent + relevant
    
    def _store_memory(self, task: str, result: str):
        """存储记忆"""
        # 短期记忆
        self.short_term.append({
            "task": task,
            "result": result,
            "timestamp": time.time()
        })
        
        # 长期记忆（重要内容）
        if self._is_important(task, result):
            embedding = self._embed(f"{task}\n{result}")
            self.long_term.add(
                embedding=embedding,
                metadata={"task": task, "result": result}
            )
```

---

### 7. Hierarchical Planning 模式

**用途**: 分层规划

**实现**:
```python
class HierarchicalPlanningAgent:
    """分层规划 Agent"""
    
    def run(self, task: str) -> str:
        # 1. 高层规划
        high_level_plan = self._high_level_plan(task)
        
        # 2. 中层规划
        mid_level_plans = []
        for goal in high_level_plan.goals:
            mid_plan = self._mid_level_plan(goal)
            mid_level_plans.append(mid_plan)
        
        # 3. 低层执行
        results = []
        for mid_plan in mid_level_plans:
            for step in mid_plan.steps:
                result = self._execute_step(step)
                results.append(result)
        
        # 4. 整合结果
        return self._integrate(results)
    
    def _high_level_plan(self, task: str) -> Plan:
        """高层规划"""
        prompt = f"""Task: {task}

Create high-level goals:
1. ...
2. ...
3. ..."""
        
        return self._parse_plan(self.llm.call(prompt))
    
    def _mid_level_plan(self, goal: str) -> Plan:
        """中层规划"""
        prompt = f"""Goal: {goal}

Create detailed steps:
1. ...
2. ...
3. ..."""
        
        return self._parse_plan(self.llm.call(prompt))
```

---

## 📊 模式对比

| 模式 | 用途 | 复杂度 | 适用场景 |
|------|------|--------|---------|
| **ReAct** | 交替思考行动 | ⭐⭐ | 通用任务 |
| **Plan-Execute** | 先规划再执行 | ⭐⭐⭐ | 复杂任务 |
| **Reflection** | 自我反思改进 | ⭐⭐ | 质量要求高 |
| **Multi-Agent** | 分工协作 | ⭐⭐⭐⭐ | 大型项目 |
| **Tool Learning** | 学习新工具 | ⭐⭐⭐ | 工具密集 |
| **Memory-Augmented** | 增强记忆 | ⭐⭐⭐ | 长期任务 |
| **Hierarchical** | 分层规划 | ⭐⭐⭐⭐ | 超复杂任务 |

---

## 🎯 选择指南

### 简单任务（<5 步）
- ✅ ReAct
- ✅ Reflection

### 中等任务（5-10 步）
- ✅ Plan-Execute
- ✅ Memory-Augmented

### 复杂任务（10+ 步）
- ✅ Multi-Agent
- ✅ Hierarchical

### 工具密集任务
- ✅ Tool Learning
- ✅ ReAct

---

**生成时间**: 2026-03-27 13:50 GMT+8
