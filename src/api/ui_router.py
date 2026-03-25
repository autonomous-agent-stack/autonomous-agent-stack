"""UI API router - 提供 DAG 节点数据流接口"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
import random

router = APIRouter(prefix="/api/v1/openclaw/agents", tags=["ui"])


class NodeStatus:
    """节点状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class DAGNode:
    """DAG 节点数据模型"""
    def __init__(
        self,
        id: str,
        label: str,
        status: str = NodeStatus.PENDING,
        duration_ms: int = 0,
        progress: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.label = label
        self.status = status
        self.duration_ms = duration_ms
        self.progress = progress
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "label": self.label,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "progress": self.progress,
            "metadata": self.metadata
        }


class DAGEdge:
    """DAG 边数据模型"""
    def __init__(self, from_node: str, to_node: str, label: str = ""):
        self.from_node = from_node
        self.to_node = to_node
        self.label = label

    def to_dict(self) -> Dict[str, str]:
        """转换为字典格式"""
        return {
            "from": self.from_node,
            "to": self.to_node,
            "label": self.label
        }


# 模拟 DAG 状态存储（实际应连接到真实的数据源）
_mock_dag_state = {
    "nodes": [
        DAGNode("planner_001", "规划节点", NodeStatus.SUCCESS, 1200, 1.0),
        DAGNode("generator_001", "生成节点", NodeStatus.RUNNING, 1500, 0.7),
        DAGNode("validator_001", "验证节点", NodeStatus.PENDING, 0, 0.0),
        DAGNode("executor_001", "执行节点", NodeStatus.PENDING, 0, 0.0),
    ],
    "edges": [
        DAGEdge("planner_001", "generator_001", "生成"),
        DAGEdge("generator_001", "validator_001", "验证"),
        DAGEdge("validator_001", "executor_001", "执行"),
    ]
}


@router.get("/tree", response_model=Dict[str, Any])
async def get_dag_tree() -> Dict[str, Any]:
    """
    获取 DAG 树状结构数据
    
    返回适用于浅色极简 UI 的标准数据流：
    - nodes: 节点列表，包含状态、进度、耗时
    - edges: 边列表，描述节点间的关系
    
    UI 渲染要求：
    - 浅色背景：#F9FAFB
    - 无视觉干扰：去除阴影、渐变
    - 实时状态标签：running/success/failed/pending
    - 耗时字段：duration_ms（毫秒）
    """
    try:
        # 模拟动态更新（实际应从数据源获取）
        _update_mock_state()
        
        # 构建响应数据
        response = {
            "nodes": [node.to_dict() for node in _mock_dag_state["nodes"]],
            "edges": [edge.to_dict() for edge in _mock_dag_state["edges"]],
            "metadata": {
                "total_nodes": len(_mock_dag_state["nodes"]),
                "total_edges": len(_mock_dag_state["edges"]),
                "timestamp": datetime.now().isoformat(),
                "ui_theme": {
                    "background": "#F9FAFB",
                    "style": "minimal"
                }
            }
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 DAG 数据失败: {str(e)}")


@router.get("/nodes/{node_id}", response_model=Dict[str, Any])
async def get_node_detail(node_id: str) -> Dict[str, Any]:
    """
    获取单个节点的详细信息
    """
    try:
        node = next(
            (n for n in _mock_dag_state["nodes"] if n.id == node_id),
            None
        )
        
        if not node:
            raise HTTPException(status_code=404, detail=f"节点 {node_id} 不存在")
        
        return {
            "node": node.to_dict(),
            "incoming_edges": [
                e.to_dict() for e in _mock_dag_state["edges"]
                if e.to_node == node_id
            ],
            "outgoing_edges": [
                e.to_dict() for e in _mock_dag_state["edges"]
                if e.from_node == node_id
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取节点详情失败: {str(e)}")


@router.get("/status", response_model=Dict[str, Any])
async def get_system_status() -> Dict[str, Any]:
    """
    获取整体系统状态摘要
    """
    try:
        nodes = _mock_dag_state["nodes"]
        
        status_counts = {
            NodeStatus.PENDING: 0,
            NodeStatus.RUNNING: 0,
            NodeStatus.SUCCESS: 0,
            NodeStatus.FAILED: 0
        }
        
        total_duration = 0
        total_progress = 0.0
        
        for node in nodes:
            status_counts[node.status] += 1
            total_duration += node.duration_ms
            total_progress += node.progress
        
        avg_progress = total_progress / len(nodes) if nodes else 0.0
        
        return {
            "total_nodes": len(nodes),
            "status_breakdown": status_counts,
            "total_duration_ms": total_duration,
            "average_progress": round(avg_progress, 2),
            "is_running": status_counts[NodeStatus.RUNNING] > 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统状态失败: {str(e)}")


def _update_mock_state():
    """
    模拟状态更新（演示用）
    实际应用中应替换为真实的数据源查询
    """
    # 随机更新运行中节点的进度
    for node in _mock_dag_state["nodes"]:
        if node.status == NodeStatus.RUNNING:
            node.progress = min(1.0, node.progress + random.uniform(0.01, 0.05))
            node.duration_ms += random.randint(100, 300)
            
            # 随机完成
            if node.progress >= 1.0:
                node.status = NodeStatus.SUCCESS
                node.progress = 1.0


__all__ = ["router"]
