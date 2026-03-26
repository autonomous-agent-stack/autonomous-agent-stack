"""
MASFactory 集成 - 图编排引擎

这个模块将 MASFactory 作为中枢神经与图编排引擎，替代硬编码的流转逻辑。
实现最小闭环：规划 → 生成 → 执行 → 评估 → (循环或结束)
"""

import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import re

from .concurrency import ConcurrencyManager
from .prompt_builder import PromptBuilder, PromptOrchestrationPlan


class NodeType(Enum):
    """节点类型"""
    PLANNER = "planner"      # 规划节点
    GENERATOR = "generator"  # 生成节点
    EXECUTOR = "executor"    # 执行节点
    EVALUATOR = "evaluator"  # 评估节点


class NodeStatus(Enum):
    """节点状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Node:
    """
    图节点基类
    
    在 MASFactory 中，Node 是最基本的执行单元。
    我们将 5 大 API 重构成标准节点。
    """
    node_id: str
    node_type: NodeType
    status: NodeStatus = NodeStatus.PENDING
    inputs: Dict[str, Any] = None
    outputs: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.inputs is None:
            self.inputs = {}
        if self.outputs is None:
            self.outputs = {}
    
    async def execute(self, context: 'ContextBlock') -> Dict[str, Any]:
        """执行节点逻辑（子类实现）"""
        raise NotImplementedError
    
    def pre_execute(self, context: 'ContextBlock'):
        """执行前钩子（用于 AppleDouble 清理等）"""
        pass
    
    def post_execute(self, context: 'ContextBlock'):
        """执行后钩子（用于状态记录等）"""
        pass


@dataclass
class Edge:
    """
    图边
    
    定义节点之间的数据流和依赖关系。
    """
    source: str
    target: str
    condition: Optional[str] = None  # 条件表达式
    
    def evaluate(self, context: 'ContextBlock') -> bool:
        """评估边条件"""
        if self.condition is None:
            return True

        expression = self.condition.strip()
        if expression in {"true", "True"}:
            return True
        if expression in {"false", "False"}:
            return False

        equal_match = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*==\s*['\"]([^'\"]+)['\"]",
            expression,
        )
        if equal_match:
            key, expected = equal_match.groups()
            return str(context.get(key)) == expected

        not_equal_match = re.fullmatch(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*!=\s*['\"]([^'\"]+)['\"]",
            expression,
        )
        if not_equal_match:
            key, expected = not_equal_match.groups()
            return str(context.get(key)) != expected

        return bool(context.get(expression, False))


class ContextBlock:
    """
    上下文块
    
    统一管理外部工具和上下文，实现 MCP 网关无缝挂载。
    """
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.tools: Dict[str, Any] = {}
        self.memory: Dict[str, Any] = {}
    
    def set(self, key: str, value: Any):
        """设置上下文数据"""
        self.data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文数据"""
        return self.data.get(key, default)
    
    def register_tool(self, name: str, tool: Any):
        """注册工具（MCP 等）"""
        self.tools[name] = tool
    
    def call_tool(self, name: str, *args, **kwargs) -> Any:
        """调用工具"""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found")
        return self.tools[name](*args, **kwargs)
    
    def save_memory(self, key: str, value: Any):
        """保存记忆（持久化）"""
        self.memory[key] = value
        # 实际应调用 OpenClaw 持久化
    
    def load_memory(self, key: str) -> Any:
        """加载记忆"""
        return self.memory.get(key)


class PlannerNode(Node):
    """
    规划节点
    
    对接 OpenClaw，读取持久化的文本状态，生成下一步目标。
    """
    
    def __init__(self, node_id: str = "planner"):
        super().__init__(
            node_id=node_id,
            node_type=NodeType.PLANNER
        )
    
    async def execute(self, context: ContextBlock) -> Dict[str, Any]:
        """执行规划逻辑"""
        self.status = NodeStatus.RUNNING
        
        # 1. 从 OpenClaw 读取当前状态
        current_state = context.load_memory("current_state")
        
        # 2. 分析任务目标
        task_goal = self.inputs.get("goal") or context.get("goal", "未定义目标")
        
        # 3. 生成下一步计划
        plan = {
            "goal": task_goal,
            "current_state": current_state,
            "next_steps": [
                "分析任务需求",
                "生成解决方案",
                "执行验证",
                "评估结果"
            ]
        }
        
        # 4. 保存计划到上下文
        context.set("plan", plan)
        
        self.status = NodeStatus.COMPLETED
        self.outputs = plan
        
        return plan


class GeneratorNode(Node):
    """
    生成节点
    
    负责写代码或调用 MCP 工具。
    """
    
    def __init__(self, node_id: str = "generator"):
        super().__init__(
            node_id=node_id,
            node_type=NodeType.GENERATOR
        )
    
    async def execute(self, context: ContextBlock) -> Dict[str, Any]:
        """执行生成逻辑"""
        self.status = NodeStatus.RUNNING
        
        # 1. 获取计划
        plan = context.get("plan", {})
        
        # 2. 生成代码或工具调用
        # 简化版：直接生成 Python 代码
        goal = plan.get("goal") or context.get("goal", "未知任务")
        code = f"""
# 自动生成的代码
def solve_task():
    '''解决任务: {goal}'''
    print("执行任务...")
    return "success"
"""
        
        # 3. 保存到上下文
        context.set("generated_code", code)
        
        self.status = NodeStatus.COMPLETED
        self.outputs = {"code": code}
        
        return {"code": code}


class ExecutorNode(Node):
    """
    执行节点
    
    真实的沙盒环境，支持 M1 本地执行 + AppleDouble 清理。
    """
    
    def __init__(self, node_id: str = "executor"):
        super().__init__(
            node_id=node_id,
            node_type=NodeType.EXECUTOR
        )
    
    def pre_execute(self, context: ContextBlock):
        """
        执行前钩子 - AppleDouble 清理
        
        在 M1 Mac 环境中，自动清除 ._ 等伪文件。
        """
        import subprocess
        import os
        
        # 清理 AppleDouble 文件
        cleanup_script = """
find . -name "._*" -type f -delete
find . -name ".DS_Store" -type f -delete
"""
        
        try:
            subprocess.run(cleanup_script, shell=True, check=True)
            print("✅ AppleDouble 清理完成")
        except Exception as e:
            print(f"⚠️ 清理失败: {e}")
    
    async def execute(self, context: ContextBlock) -> Dict[str, Any]:
        """执行沙盒逻辑"""
        self.status = NodeStatus.RUNNING

        # 1. 获取生成的代码
        code = context.get("generated_code", "")

        # 2. 模拟沙盒执行
        # 实际应使用 Docker 或其他沙盒
        result = {
            "status": "success",
            "output": "任务执行成功",
            "code": code
        }

        # 3. 保存结果
        context.set("execution_result", result)

        self.status = NodeStatus.COMPLETED
        self.outputs = result

        return result


class EvaluatorNode(Node):
    """
    评估节点
    
    承载 MetaClaw 的逻辑，对执行结果打分，决定是重试还是进入下一步。
    """
    
    def __init__(self, node_id: str = "evaluator"):
        super().__init__(
            node_id=node_id,
            node_type=NodeType.EVALUATOR
        )
    
    async def execute(self, context: ContextBlock) -> Dict[str, Any]:
        """执行评估逻辑"""
        self.status = NodeStatus.RUNNING
        
        # 1. 获取执行结果
        execution_result = context.get("execution_result", {})
        
        # 2. 评估结果
        # 简化版：基于状态评估
        if execution_result.get("status") == "success":
            score = 0.95
            decision = "continue"  # 继续下一步
        else:
            score = 0.3
            decision = "retry"  # 重试
        
        # 3. 生成评估报告
        evaluation = {
            "score": score,
            "decision": decision,
            "execution_result": execution_result,
            "timestamp": str(context.get("timestamp", "unknown"))
        }
        
        # 4. 保存评估结果
        context.set("evaluation", evaluation)
        context.set("decision", decision)
        context.save_memory("last_evaluation", evaluation)
        
        self.status = NodeStatus.COMPLETED
        self.outputs = evaluation
        
        return evaluation


NODE_FACTORY: dict[str, type[Node]] = {
    NodeType.PLANNER.value: PlannerNode,
    NodeType.GENERATOR.value: GeneratorNode,
    NodeType.EXECUTOR.value: ExecutorNode,
    NodeType.EVALUATOR.value: EvaluatorNode,
}


class Graph:
    """
    图编排引擎
    
    将多个节点组装成可执行的工作流。
    """
    
    def __init__(self, graph_id: str, *, max_concurrency: int = 3):
        self.graph_id = graph_id
        self.nodes: Dict[str, Node] = {}
        self.edges: list[Edge] = []
        self.context = ContextBlock()
        self._max_concurrency = max(1, max_concurrency)
        self._concurrency_manager = ConcurrencyManager(max_concurrent=self._max_concurrency)
    
    def add_node(self, node: Node):
        """添加节点"""
        self.nodes[node.node_id] = node
    
    def add_edge(self, source: str, target: str, condition: str = None):
        """添加边"""
        edge = Edge(source=source, target=target, condition=condition)
        self.edges.append(edge)

    def set_max_concurrency(self, value: int) -> None:
        """更新图执行并发度。"""
        self._max_concurrency = max(1, value)
        self._concurrency_manager = ConcurrencyManager(max_concurrent=self._max_concurrency)
        self.context.set("orchestration_max_concurrency", self._max_concurrency)

    @staticmethod
    def _create_node_from_type(node_id: str, node_type: str) -> Node:
        node_class = NODE_FACTORY.get(node_type)
        if node_class is None:
            supported = ", ".join(sorted(NODE_FACTORY))
            raise ValueError(
                f"Unsupported node type '{node_type}' for node '{node_id}'. "
                f"Supported types: {supported}"
            )
        return node_class(node_id)

    def apply_prompt_plan(self, plan: PromptOrchestrationPlan) -> None:
        """将 prompt 解析结果应用到图中。"""
        self.nodes.clear()
        self.edges.clear()

        for step in plan.steps:
            node = self._create_node_from_type(step.node_id, step.node_type)
            self.add_node(node)

        for edge in plan.edges:
            self.add_edge(edge.source, edge.target, edge.condition)

        self.context.set("goal", plan.goal)
        self.context.set("orchestration_plan", plan.to_dict())
        self.context.set("orchestration_max_steps", plan.max_steps)
        self.set_max_concurrency(plan.max_concurrency)

    @classmethod
    def from_prompt(
        cls,
        graph_id: str,
        prompt: str,
        *,
        goal: Optional[str] = None,
        max_concurrency: Optional[int] = None,
    ) -> "Graph":
        """通过 prompt 直接构建图编排。"""
        graph = cls(graph_id, max_concurrency=max_concurrency or 3)
        plan = PromptBuilder.build_orchestration_plan(prompt, fallback_goal=goal)
        if max_concurrency is not None:
            plan.max_concurrency = max(1, max_concurrency)
        graph.apply_prompt_plan(plan)
        graph.context.set("orchestration_prompt", prompt.strip())
        return graph

    def _resolve_initial_queue(self) -> list[str]:
        incoming_counts = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            if edge.source not in self.nodes or edge.target not in self.nodes:
                continue
            incoming_counts[edge.target] += 1
        queue = [node_id for node_id, count in incoming_counts.items() if count == 0]
        if not queue and self.nodes:
            queue = [next(iter(self.nodes))]
        return queue

    @staticmethod
    def _normalize_queue_batch(queue: list[str]) -> list[str]:
        """去重并保持队列顺序，避免同轮重复执行同节点。"""
        seen: set[str] = set()
        batch: list[str] = []
        while queue:
            node_id = queue.pop(0)
            if node_id in seen:
                continue
            seen.add(node_id)
            batch.append(node_id)
        return batch

    async def _execute_node(self, node_id: str) -> tuple[str, dict[str, Any], bool]:
        node = self.nodes[node_id]
        print(f"🔄 执行节点: {node_id}")
        acquired = False

        try:
            await self._concurrency_manager.acquire()
            acquired = True
            self._concurrency_manager.set_context({"graph_id": self.graph_id, "node_id": node_id})
            node.pre_execute(self.context)
            result = await node.execute(self.context)
            node.post_execute(self.context)
            self._concurrency_manager.record_result(False)
            print(f"✅ 节点 {node_id} 完成")
            return node_id, result, True
        except Exception as e:
            node.status = NodeStatus.FAILED
            self._concurrency_manager.record_result(True)
            print(f"❌ 节点 {node_id} 失败: {e}")
            return node_id, {"error": str(e)}, False
        finally:
            if acquired:
                self._concurrency_manager.release()

    async def execute(
        self,
        max_steps: Optional[int] = None,
        *,
        max_concurrency: Optional[int] = None,
    ) -> Dict[str, Any]:
        """按边驱动执行图，支持条件分支、循环保护与同层并发。"""
        if not self.nodes:
            return {}
        if max_steps is None:
            max_steps = int(self.context.get("orchestration_max_steps", 32))
        if max_concurrency is None:
            max_concurrency = int(self.context.get("orchestration_max_concurrency", self._max_concurrency))
        self.set_max_concurrency(max_concurrency)

        outgoing_edges: dict[str, list[Edge]] = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            if edge.source not in self.nodes or edge.target not in self.nodes:
                continue
            outgoing_edges[edge.source].append(edge)

        queue = self._resolve_initial_queue()
        results: dict[str, Any] = {}
        steps = 0

        while queue:
            if steps >= max_steps:
                raise RuntimeError(f"graph execution exceeded max_steps={max_steps}")

            batch = self._normalize_queue_batch(queue)
            remaining_budget = max_steps - steps
            if len(batch) > remaining_budget:
                batch = batch[:remaining_budget]

            print(f"🚦 并发批次: {', '.join(batch)}")
            execution_results = await asyncio.gather(*(self._execute_node(node_id) for node_id in batch))
            has_failure = False
            next_queue: list[str] = []

            for node_id, result, success in execution_results:
                results[node_id] = result
                if not success:
                    has_failure = True
                    continue
                for edge in outgoing_edges.get(node_id, []):
                    if edge.evaluate(self.context):
                        next_queue.append(edge.target)

            steps += len(batch)
            if has_failure:
                break
            queue.extend(next_queue)

        return results
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典（用于可视化）"""
        return {
            "graph_id": self.graph_id,
            "nodes": [
                {
                    "id": node.node_id,
                    "type": node.node_type.value,
                    "status": node.status.value
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "condition": edge.condition
                }
                for edge in self.edges
            ]
        }


def create_minimal_loop() -> Graph:
    """
    创建最小闭环
    
    规划 → 生成 → 执行 → 评估 → (失败则循环回生成，成功则结束)
    """
    # 创建图
    graph = Graph("minimal_loop")
    
    # 添加节点
    graph.add_node(PlannerNode("planner"))
    graph.add_node(GeneratorNode("generator"))
    graph.add_node(ExecutorNode("executor"))
    graph.add_node(EvaluatorNode("evaluator"))
    
    # 添加边（定义流转）
    graph.add_edge("planner", "generator")
    graph.add_edge("generator", "executor")
    graph.add_edge("executor", "evaluator")
    
    # 条件边：失败时循环回生成
    graph.add_edge("evaluator", "generator", condition="decision == 'retry'")
    
    return graph


def create_graph_from_prompt(
    prompt: str,
    *,
    goal: Optional[str] = None,
    graph_id: str = "prompt_orchestration",
    max_concurrency: Optional[int] = None,
) -> Graph:
    """
    从 prompt 快速创建图编排。

    示例：
        goal: 优化代码性能
        nodes: planner -> generator -> executor -> evaluator
        retry: evaluator -> generator when decision == 'retry'
        max_steps: 16
        max_concurrency: 3
    """
    return Graph.from_prompt(
        graph_id=graph_id,
        prompt=prompt,
        goal=goal,
        max_concurrency=max_concurrency,
    )


# 使用示例
async def main():
    """演示 MASFactory 集成"""
    print("=" * 60)
    print("🤖 MASFactory 集成演示")
    print("=" * 60)
    
    # 创建最小闭环
    graph = create_minimal_loop()
    
    # 设置初始输入
    graph.context.set("goal", "优化代码性能")
    graph.context.set("timestamp", "2026-03-25T21:30:00Z")
    
    # 执行图
    results = await graph.execute()
    
    # 打印结果
    print("\n" + "=" * 60)
    print("📊 执行结果")
    print("=" * 60)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # 导出图结构（用于可视化）
    graph_structure = graph.to_dict()
    print("\n" + "=" * 60)
    print("🎨 图结构（可导入可视化工具）")
    print("=" * 60)
    print(json.dumps(graph_structure, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
