# 🎯 MASFactory 集成指南

> **将 MASFactory 引入 Autonomous Agent Stack，实现现代化图编排引擎**

---

## 📋 概述

### 核心价值

MASFactory 在 Autonomous Agent Stack 中的定位是**中枢神经与图编排引擎**，它能完美平替甚至大幅超越原来 deer-flow 的硬编码流转逻辑。

**核心优势**：
- ✅ **Vibe Graphing**：意图 → 图，自动生成工作流
- ✅ **图式组合**：Node / Edge 显式定义依赖关系
- ✅ **可观测性**：拓扑预览 + 运行时追踪
- ✅ **ContextBlock**：统一管理工具和上下文

---

## 🏗️ 架构设计

### 四维模块化组装

#### 1. 将 5 大 API 重构成"图节点 (Nodes)"

| 节点类型 | 原对应 API | 核心职责 |
|---------|-----------|---------|
| **Planner Node** | - | 对接 OpenClaw，读取持久化状态，生成下一步目标 |
| **Generator Node** | Generator API | 负责写代码或调用 MCP 工具 |
| **Executor Node** | Executor API | 真实的沙盒环境 |
| **Evaluator Node** | Evaluator API | 承载 MetaClaw 逻辑，打分决定重试或继续 |

**代码示例**：

```python
from src.orchestrator import PlannerNode, GeneratorNode, ExecutorNode, EvaluatorNode

# 创建节点
planner = PlannerNode("planner")
generator = GeneratorNode("generator")
executor = ExecutorNode("executor")
evaluator = EvaluatorNode("evaluator")

# 组装成图
graph = Graph("minimal_loop")
graph.add_node(planner)
graph.add_node(generator)
graph.add_node(executor)
graph.add_node(evaluator)

# 定义流转
graph.add_edge("planner", "generator")
graph.add_edge("generator", "executor")
graph.add_edge("executor", "evaluator")
graph.add_edge("evaluator", "generator", condition="decision == 'retry'")
```

---

#### 2. 构建纯净的 M1 本地执行沙盒

**核心机制**：在 Executor Node 的 `pre_execute` 钩子中植入防御性清理脚本。

**代码实现**：

```python
class ExecutorNode(Node):
    def pre_execute(self, context: ContextBlock):
        """执行前钩子 - AppleDouble 清理"""
        import subprocess
        
        cleanup_script = """
find . -name "._*" -type f -delete
find . -name ".DS_Store" -type f -delete
"""
        
        try:
            subprocess.run(cleanup_script, shell=True, check=True)
            print("✅ AppleDouble 清理完成")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")
```

**效果**：
- ✅ 每次执行前自动清理 `._` 等伪文件
- ✅ 彻底杜绝环境污染导致 Evaluator 节点报错
- ✅ 发挥 M1 本地算力，无需依赖远程服务器

---

#### 3. 用 ContextBlock 无缝挂载 MCP 网关

**核心机制**：新建 `MCPContextBlock`，统一桥接 InfoQuest/MCP 工具链。

**代码实现**：

```python
from src.orchestrator.mcp_context import MCPContextBlock

# 创建 MCP 上下文块
mcp = MCPContextBlock()

# 注册工具
mcp.register_tool("web_search", {
    "endpoint": "https://mcp.infoquest.bytepluses.com/mcp/web_search",
    "auth_required": False
})

# 调用工具
result = await mcp.call_tool("web_search", {
    "query": "AI agent architecture 2026"
})
```

**效果**：
- ✅ 任何 Node 需要外部 API 或文件时，从统一上下文获取权限
- ✅ 避免工具满天飞的混乱状态
- ✅ 支持缓存和会话管理

---

#### 4. 打造清爽的可视化监控看板

**核心机制**：利用 MASFactory 的状态导出功能，搭建极简前端监控面板。

**代码实现**：

```python
from src.orchestrator.visualizer import Visualizer

# 创建可视化器
visualizer = Visualizer(theme="light")

# 导出为 Mermaid 图
mermaid_code = visualizer.export_to_mermaid(graph_structure)

# 生成 HTML 看板
html_dashboard = visualizer.generate_html_dashboard(
    graph_structure,
    evaluation_data={"score": 0.95, "decision": "continue"}
)

# 保存看板
with open("dashboard.html", "w") as f:
    f.write(html_dashboard)
```

**效果**：
- ✅ 实时渲染各个智能体节点的运转状态
- ✅ 显示 SQLite 里的评估分数
- ✅ 展示长耗时任务的进度
- ✅ 干净、清晰的浅色背景，无视觉干扰

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/srxly888-creator/autonomous-agent-stack.git
cd autonomous-agent-stack

# 安装依赖
pip install -r requirements.txt
```

### 2. 创建最小闭环

```python
from src.orchestrator import create_minimal_loop
import asyncio

async def main():
    # 创建最小闭环
    graph = create_minimal_loop()
    
    # 设置初始输入
    graph.context.set("goal", "优化代码性能")
    
    # 执行图
    results = await graph.execute()
    
    # 打印结果
    print(results)

# 运行
asyncio.run(main())
```

### 3. 启动监控看板

```python
from src.orchestrator.visualizer import Visualizer

# 导出图结构
graph_structure = graph.to_dict()

# 生成 HTML 看板
visualizer = Visualizer(theme="light")
html = visualizer.generate_html_dashboard(graph_structure)

# 保存并打开
with open("dashboard.html", "w") as f:
    f.write(html)

# 在浏览器中打开
import webbrowser
webbrowser.open("dashboard.html")
```

---

## 📊 架构对比

### 原 deer-flow vs MASFactory

| 维度 | deer-flow | MASFactory |
|------|-----------|-----------|
| **流转逻辑** | 硬编码 | 图编排（动态） |
| **可视化** | 无 | Mermaid + HTML 看板 |
| **工具管理** | 分散 | ContextBlock 统一管理 |
| **扩展性** | 低 | 高（插件化） |
| **可观测性** | 低 | 高（实时追踪） |

---

## 🎯 最佳实践

### 1. 节点职责单一

每个 Node 只负责一件事：

```python
# ✅ 好的设计
class PlannerNode(Node):
    async def execute(self, context):
        # 只负责规划
        plan = generate_plan(context)
        return plan

# ❌ 不好的设计
class SuperNode(Node):
    async def execute(self, context):
        # 负责太多事情
        plan = generate_plan(context)
        code = generate_code(plan)
        result = execute_code(code)
        evaluation = evaluate_result(result)
        return evaluation
```

### 2. 使用条件边控制流转

```python
# 失败时循环回生成
graph.add_edge("evaluator", "generator", condition="decision == 'retry'")

# 成功时进入下一步
graph.add_edge("evaluator", "next_step", condition="decision == 'continue'")
```

### 3. 利用 ContextBlock 共享数据

```python
# 在 Planner 中设置数据
context.set("plan", plan)

# 在 Generator 中读取数据
plan = context.get("plan")
```

### 4. 定期清理缓存

```python
# 清空 MCP 缓存
mcp.clear_cache()
```

---

## 🚨 常见问题

### Q1: 如何处理并发冲突？

**A**: 使用锁机制保护共享资源。

```python
from threading import Lock

class SafeContextBlock(ContextBlock):
    def __init__(self):
        super().__init__()
        self.lock = Lock()
    
    def set(self, key, value):
        with self.lock:
            self.data[key] = value
```

### Q2: 如何避免过度工程？

**A**: 设计短路机制。

```python
class ShortCircuitGraph(Graph):
    async def execute(self):
        # 检查是否为简单任务
        if self.context.get("is_simple_task"):
            # 直接执行，跳过重型流程
            return await self.execute_simple()
        
        # 复杂任务走完整流程
        return await super().execute()
```

### Q3: 如何调试图编排？

**A**: 使用可视化工具。

```python
# 导出图结构
graph_structure = graph.to_dict()

# 生成 Mermaid 图
visualizer = Visualizer()
mermaid_code = visualizer.export_to_mermaid(graph_structure)
print(mermaid_code)
```

---

## 📖 参考资料

- **MASFactory 官网**: https://masfactory.dev
- **MASFactory 文档**: https://docs.masfactory.dev
- **论文**: http://arxiv.org/abs/2603.06007
- **演示视频**: https://www.youtube.com/watch?v=ANynzVfY32k

---

## 🔗 相关资源

- **主文档**: [README.md](../README.md)
- **架构文档**: [architecture.md](architecture.md)
- **集成指南**: [integration-guide.md](integration-guide.md)
- **API 参考**: [api-reference.md](api-reference.md)
- **路线图**: [roadmap.md](roadmap.md)

---

**集成愉快！** 🚀
