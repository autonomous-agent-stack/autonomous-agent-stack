"""Topology Engine - OpenSage 自生成拓扑

根据任务复杂度自动生成任务图（Task Graph）
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SimpleGraph:
    """简单有向图"""
    
    def __init__(self):
        self.nodes: Dict[str, Dict] = {}
        self.edges: List[tuple] = []
        
    def add_node(self, node_id: str, **attrs):
        self.nodes[node_id] = attrs
        
    def add_edge(self, source: str, target: str, **attrs):
        self.edges.append((source, target, attrs))
        
    def topological_sort(self) -> List[str]:
        """拓扑排序（简化版）"""
        # 构建邻接表
        in_degree = {node: 0 for node in self.nodes}
        graph = {node: [] for node in self.nodes}
        
        for source, target, _ in self.edges:
            if source in graph and target in in_degree:
                graph[source].append(target)
                in_degree[target] += 1
            
        # BFS
        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            if node in graph:
                for neighbor in graph[node]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        queue.append(neighbor)
                    
        return result if len(result) == len(self.nodes) else []


class NodeType(Enum):
    """节点类型"""
    PLANNER = "planner"
    GENERATOR = "generator"
    EXECUTOR = "executor"
    EVALUATOR = "evaluator"
    SYNTHESIZER = "synthesizer"


class TaskComplexity(Enum):
    """任务复杂度"""
    SIMPLE = "simple"          # 单步任务
    MEDIUM = "medium"          # 多步任务（2-5 步）
    COMPLEX = "complex"        # 复杂任务（>5 步）
    HIERARCHICAL = "hierarchical"  # 层级任务


@dataclass
class TaskNode:
    """任务节点"""
    node_id: str
    node_type: NodeType
    description: str
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    status: str = "pending"
    assigned_agent: Optional[str] = None
    result: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskEdge:
    """任务边"""
    source: str
    target: str
    condition: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TopologyEngine:
    """拓扑引擎"""
    
    def __init__(self):
        self.graph = SimpleGraph()  # 使用简化图
        self.nodes: Dict[str, TaskNode] = {}
        self.edges: List[TaskEdge] = []
        
    async def analyze_complexity(self, task: str) -> TaskComplexity:
        """分析任务复杂度
        
        Args:
            task: 任务描述
            
        Returns:
            任务复杂度级别
        """
        # 简单启发式规则
        word_count = len(task.split())
        
        # 检查关键词
        complex_keywords = [
            "然后", "之后", "同时", "最后", "先", "再",
            "and then", "after that", "finally"
        ]
        
        hierarchical_keywords = [
            "分解", "拆分", "子任务", "decompose",
            "break down", "subtask"
        ]
        
        has_complex = any(kw in task.lower() for kw in complex_keywords)
        has_hierarchical = any(kw in task.lower() for kw in hierarchical_keywords)
        
        if has_hierarchical or word_count > 200:
            return TaskComplexity.HIERARCHICAL
        elif has_complex or word_count > 100:
            return TaskComplexity.COMPLEX
        elif word_count > 30:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.SIMPLE
            
    async def generate_topology(
        self,
        task: str,
        available_agents: Optional[List[str]] = None
    ) -> nx.DiGraph:
        """生成任务拓扑
        
        Args:
            task: 任务描述
            available_agents: 可用 Agent 列表
            
        Returns:
            任务图
        """
        logger.info(f"[Topology Engine] 生成拓扑: {task[:50]}...")
        
        # 分析复杂度
        complexity = await self.analyze_complexity(task)
        logger.info(f"[Topology Engine] 复杂度: {complexity.value}")
        
        # 根据复杂度生成拓扑
        if complexity == TaskComplexity.SIMPLE:
            await self._generate_simple_topology(task)
        elif complexity == TaskComplexity.MEDIUM:
            await self._generate_medium_topology(task)
        elif complexity == TaskComplexity.COMPLEX:
            await self._generate_complex_topology(task)
        else:  # HIERARCHICAL
            await self._generate_hierarchical_topology(task)
            
        # 分配 Agent
        if available_agents:
            await self._assign_agents(available_agents)
            
        logger.info(f"[Topology Engine] 拓扑生成完成: {len(self.nodes)} 节点")
        
        return self.graph
        
    async def _generate_simple_topology(self, task: str):
        """生成简单拓扑（单节点）"""
        node = TaskNode(
            node_id="task_0",
            node_type=NodeType.EXECUTOR,
            description=task,
            priority=0
        )
        
        self._add_node(node)
        
    async def _generate_medium_topology(self, task: str):
        """生成中等拓扑（线性链）"""
        # 分解任务
        sentences = [s.strip() for s in task.split("。") if s.strip()]
        
        for i, sentence in enumerate(sentences[:5]):
            node_type = self._determine_node_type(i, len(sentences))
            
            node = TaskNode(
                node_id=f"task_{i}",
                node_type=node_type,
                description=sentence,
                dependencies=[f"task_{i-1}"] if i > 0 else [],
                priority=i
            )
            
            self._add_node(node)
            
            # 添加边
            if i > 0:
                edge = TaskEdge(
                    source=f"task_{i-1}",
                    target=f"task_{i}"
                )
                self._add_edge(edge)
                
    async def _generate_complex_topology(self, task: str):
        """生成复杂拓扑（并行 + 依赖）"""
        # 分解任务
        paragraphs = task.split("\n\n")
        
        task_id = 0
        
        # Planner 节点
        planner_node = TaskNode(
            node_id=f"task_{task_id}",
            node_type=NodeType.PLANNER,
            description=f"规划任务: {task[:50]}...",
            priority=0
        )
        self._add_node(planner_node)
        planner_id = f"task_{task_id}"
        task_id += 1
        
        # 为每个段落创建执行节点
        for para in paragraphs:
            if not para.strip():
                continue
                
            executor_node = TaskNode(
                node_id=f"task_{task_id}",
                node_type=NodeType.EXECUTOR,
                description=para[:100],
                dependencies=[planner_id],
                priority=1
            )
            self._add_node(executor_node)
            
            # 添加边
            edge = TaskEdge(
                source=planner_id,
                target=f"task_{task_id}"
            )
            self._add_edge(edge)
            
            task_id += 1
            
        # Evaluator 节点
        evaluator_node = TaskNode(
            node_id=f"task_{task_id}",
            node_type=NodeType.EVALUATOR,
            description="评估所有执行结果",
            priority=2
        )
        self._add_node(evaluator_node)
        
    async def _generate_hierarchical_topology(self, task: str):
        """生成层级拓扑（递归分解）"""
        # TODO: 实现递归分解逻辑
        # 目前简化为复杂拓扑
        await self._generate_complex_topology(task)
        
    def _determine_node_type(self, index: int, total: int) -> NodeType:
        """确定节点类型"""
        if index == 0:
            return NodeType.PLANNER
        elif index == total - 1:
            return NodeType.EVALUATOR
        else:
            return NodeType.EXECUTOR
            
    def _add_node(self, node: TaskNode):
        """添加节点"""
        self.nodes[node.node_id] = node
        self.graph.add_node(
            node.node_id,
            **node.__dict__
        )
        
    def _add_edge(self, edge: TaskEdge):
        """添加边"""
        self.edges.append(edge)
        self.graph.add_edge(
            edge.source,
            edge.target,
            **edge.metadata
        )
        
    async def _assign_agents(self, agents: List[str]):
        """分配 Agent"""
        for i, (node_id, node) in enumerate(self.nodes.items()):
            if agents:
                node.assigned_agent = agents[i % len(agents)]
                
    def get_execution_order(self) -> List[str]:
        """获取执行顺序（拓扑排序）"""
        try:
            return list(nx.topological_sort(self.graph))
        except nx.NetworkXUnfeasible:
            logger.error("[Topology Engine] 图中存在环，无法排序")
            return []
            
    def visualize(self) -> str:
        """可视化拓扑（Mermaid 格式）"""
        lines = ["graph TD"]
        
        for node_id, node in self.nodes.items():
            label = f"{node.node_type.value}: {node.description[:20]}..."
            lines.append(f'    {node_id}["{label}"]')
            
        for edge in self.edges:
            lines.append(f"    {edge.source} --> {edge.target}")
            
        return "\n".join(lines)


# 单例实例
_topology_engine: Optional[TopologyEngine] = None


def get_topology_engine() -> TopologyEngine:
    """获取拓扑引擎单例"""
    global _topology_engine
    if _topology_engine is None:
        _topology_engine = TopologyEngine()
    return _topology_engine
