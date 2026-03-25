"""
图编排引擎 - 核心工作流执行器

负责 DAG 的规划、生成、执行和评估，提供完整的节点生命周期日志追踪。
"""

import json
import time
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field

from .structured_logger import get_logger


class NodeType(Enum):
    """节点类型枚举"""
    PLANNER = "planner"          # 规划节点
    GENERATOR = "generator"      # 生成节点
    EXECUTOR = "executor"        # 执行节点
    EVALUATOR = "evaluator"      # 评估节点
    TOOL = "tool"                # 工具节点
    CUSTOM = "custom"            # 自定义节点


class NodeStatus(Enum):
    """节点状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class NodeResult:
    """节点执行结果"""
    status: NodeStatus
    output: Any = None
    error: Optional[Exception] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphNode:
    """图节点定义"""
    id: str
    type: NodeType
    handler: Callable
    dependencies: List[str] = field(default_factory=list)
    retry_config: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphEngine:
    """图编排引擎"""
    
    def __init__(self, graph_id: str = "default"):
        """初始化图引擎
        
        Args:
            graph_id: 图ID
        """
        self.graph_id = graph_id
        self.nodes: Dict[str, GraphNode] = {}
        self.logger = get_logger(f"GraphEngine.{graph_id}")
        self.execution_history: List[Dict[str, Any]] = []
        
        self.logger.info(
            "graph_engine",
            "initialized",
            graph_id=graph_id
        )
    
    def add_node(self, node: GraphNode) -> None:
        """添加节点到图中
        
        Args:
            node: 图节点
        """
        self.nodes[node.id] = node
        self.logger.debug(
            "graph_engine",
            "node_added",
            node_id=node.id,
            node_type=node.type.value,
            dependencies=node.dependencies
        )
    
    def execute(
        self,
        start_nodes: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, NodeResult]:
        """执行图
        
        Args:
            start_nodes: 起始节点列表（None 表示执行所有无依赖节点）
            context: 执行上下文
            
        Returns:
            节点ID到执行结果的映射
        """
        if start_nodes is None:
            start_nodes = self._get_root_nodes()
        
        context = context or {}
        results: Dict[str, NodeResult] = {}
        
        self.logger.info(
            "graph_engine",
            "execution_started",
            graph_id=self.graph_id,
            total_nodes=len(self.nodes),
            start_nodes=start_nodes
        )
        
        execution_start = time.time()
        
        # 拓扑排序执行
        execution_order = self._topological_sort()
        
        for node_id in execution_order:
            node = self.nodes[node_id]
            
            # 检查依赖是否满足
            if not self._dependencies_satisfied(node, results):
                self.logger.debug(
                    "graph_engine",
                    "node_skipped",
                    node_id=node_id,
                    reason="dependencies_not_satisfied"
                )
                results[node_id] = NodeResult(status=NodeStatus.SKIPPED)
                continue
            
            # 执行节点
            result = self._execute_node(node, context, results)
            results[node_id] = result
            
            # 记录到历史
            self.execution_history.append({
                "node_id": node_id,
                "status": result.status.value,
                "duration_ms": result.duration_ms,
                "timestamp": time.time()
            })
            
            # 如果节点失败且不继续，停止执行
            if result.status == NodeStatus.FAILED:
                self.logger.error(
                    "graph_engine",
                    "execution_failed",
                    failed_node=node_id,
                    error_message=str(result.error) if result.error else "Unknown error"
                )
                break
        
        total_duration_ms = int((time.time() - execution_start) * 1000)
        
        self.logger.info(
            "graph_engine",
            "execution_completed",
            graph_id=self.graph_id,
            total_duration_ms=total_duration_ms,
            nodes_executed=len([r for r in results.values() if r.status == NodeStatus.COMPLETED]),
            nodes_failed=len([r for r in results.values() if r.status == NodeStatus.FAILED])
        )
        
        return results
    
    def _execute_node(
        self,
        node: GraphNode,
        context: Dict[str, Any],
        previous_results: Dict[str, NodeResult]
    ) -> NodeResult:
        """执行单个节点
        
        Args:
            node: 要执行的节点
            context: 执行上下文
            previous_results: 前序节点结果
            
        Returns:
            节点执行结果
        """
        max_attempts = node.retry_config.get("max_attempts", 1)
        base_delay_ms = node.retry_config.get("base_delay_ms", 1000)
        
        for attempt in range(1, max_attempts + 1):
            try:
                with self.logger.node_execution(
                    node.type.value,
                    "execute_node",
                    node_id=node.id,
                    attempt=attempt,
                    max_attempts=max_attempts
                ) as _:
                    # 准备输入
                    inputs = self._prepare_inputs(node, context, previous_results)
                    
                    # 执行节点处理函数
                    output = node.handler(inputs)
                    
                    return NodeResult(
                        status=NodeStatus.COMPLETED,
                        output=output,
                        duration_ms=0  # 上下文管理器已记录
                    )
                    
            except Exception as e:
                if attempt < max_attempts:
                    delay_ms = int(base_delay_ms * (2 ** (attempt - 1)))
                    
                    self.logger.log_retry(
                        node.type.value,
                        attempt,
                        max_attempts,
                        e,
                        delay_ms
                    )
                    
                    time.sleep(delay_ms / 1000.0)
                else:
                    return NodeResult(
                        status=NodeStatus.FAILED,
                        error=e,
                        duration_ms=0
                    )
        
        return NodeResult(status=NodeStatus.FAILED)
    
    def _prepare_inputs(
        self,
        node: GraphNode,
        context: Dict[str, Any],
        previous_results: Dict[str, NodeResult]
    ) -> Dict[str, Any]:
        """准备节点输入
        
        Args:
            node: 节点
            context: 全局上下文
            previous_results: 前序节点结果
            
        Returns:
            合并后的输入字典
        """
        inputs = {
            "context": context,
            "node_id": node.id,
            "node_type": node.type.value
        }
        
        # 添加依赖节点的输出
        for dep_id in node.dependencies:
            if dep_id in previous_results:
                inputs[dep_id] = previous_results[dep_id].output
        
        return inputs
    
    def _get_root_nodes(self) -> List[str]:
        """获取根节点（无依赖的节点）"""
        return [
            node_id for node_id, node in self.nodes.items()
            if not node.dependencies
        ]
    
    def _dependencies_satisfied(
        self,
        node: GraphNode,
        results: Dict[str, NodeResult]
    ) -> bool:
        """检查节点依赖是否已满足
        
        Args:
            node: 节点
            results: 已执行的结果
            
        Returns:
            依赖是否全部满足
        """
        for dep_id in node.dependencies:
            if dep_id not in results:
                return False
            if results[dep_id].status != NodeStatus.COMPLETED:
                return False
        return True
    
    def _topological_sort(self) -> List[str]:
        """拓扑排序
        
        Returns:
            排序后的节点ID列表
        """
        in_degree = {node_id: 0 for node_id in self.nodes}
        
        # 计算入度
        for node_id, node in self.nodes.items():
            for dep_id in node.dependencies:
                if dep_id in in_degree:
                    in_degree[node_id] += 1
        
        # 找出所有入度为0的节点
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            
            # 减少依赖此节点的其他节点的入度
            for other_id, other_node in self.nodes.items():
                if node_id in other_node.dependencies:
                    in_degree[other_id] -= 1
                    if in_degree[other_id] == 0:
                        queue.append(other_id)
        
        return result
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计信息
        
        Returns:
            统计信息字典
        """
        if not self.execution_history:
            return {"total_executions": 0}
        
        completed = [h for h in self.execution_history if h["status"] == "completed"]
        failed = [h for h in self.execution_history if h["status"] == "failed"]
        
        return {
            "total_executions": len(self.execution_history),
            "completed": len(completed),
            "failed": len(failed),
            "average_duration_ms": int(
                sum(h["duration_ms"] for h in completed) / len(completed)
            ) if completed else 0,
            "success_rate": len(completed) / len(self.execution_history)
            if self.execution_history else 0
        }
