"""Cluster API - 集群管理 API

功能：
1. 节点注册/注销
2. 节点列表/状态
3. 任务分发
4. 集群状态
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from autoresearch.core.services.cluster_manager import (
    ClusterManager,
    LoadBalanceStrategy,
    get_cluster_manager,
)

router = APIRouter(prefix="/api/v1/cluster", tags=["cluster"])


# ========================================================================
# 数据模型
# ========================================================================


class NodeRegisterRequest(BaseModel):
    """节点注册请求"""

    name: str = Field(..., min_length=1, max_length=100)
    endpoint: str = Field(..., min_length=1)
    api_key: str = Field(..., min_length=1)
    capabilities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NodeRead(BaseModel):
    """节点信息"""

    node_id: str
    name: str
    endpoint: str
    status: str
    load: float
    capabilities: List[str]
    success_rate: float
    last_heartbeat: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int


class TaskDispatchRequest(BaseModel):
    """任务分发请求"""

    task: Dict[str, Any]
    required_capabilities: Optional[List[str]] = None
    strategy: str = "least_load"  # least_load, round_robin, random


class TaskDispatchResponse(BaseModel):
    """任务分发响应"""

    node_id: str
    node_name: str
    result: Dict[str, Any]


class ClusterStatusResponse(BaseModel):
    """集群状态响应"""

    total_nodes: int
    online_nodes: int
    offline_nodes: int
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    nodes: List[Dict[str, Any]]


# ========================================================================
# API 端点
# ========================================================================


@router.get("/health")
def cluster_health() -> dict[str, str]:
    """集群健康检查"""
    return {"status": "ok"}


@router.post("/nodes", response_model=NodeRead, status_code=status.HTTP_201_CREATED)
async def register_node(
    request: NodeRegisterRequest,
    manager: ClusterManager = Depends(get_cluster_manager),
):
    """注册节点"""
    try:
        node = await manager.register_node(
            name=request.name,
            endpoint=request.endpoint,
            api_key=request.api_key,
            capabilities=request.capabilities,
            metadata=request.metadata,
        )

        return NodeRead(
            node_id=node.node_id,
            name=node.name,
            endpoint=node.endpoint,
            status=node.status.value,
            load=node.load,
            capabilities=node.capabilities,
            success_rate=node.success_rate,
            last_heartbeat=node.last_heartbeat.isoformat(),
            total_tasks=node.total_tasks,
            successful_tasks=node.successful_tasks,
            failed_tasks=node.failed_tasks,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/nodes/{node_id}")
async def unregister_node(
    node_id: str,
    manager: ClusterManager = Depends(get_cluster_manager),
):
    """注销节点"""
    success = await manager.unregister_node(node_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"节点不存在: {node_id}",
        )

    return {"success": True, "message": f"节点已注销: {node_id}"}


@router.get("/nodes", response_model=List[NodeRead])
async def list_nodes(
    manager: ClusterManager = Depends(get_cluster_manager),
):
    """列出所有节点"""
    return [
        NodeRead(
            node_id=node.node_id,
            name=node.name,
            endpoint=node.endpoint,
            status=node.status.value,
            load=node.load,
            capabilities=node.capabilities,
            success_rate=node.success_rate,
            last_heartbeat=node.last_heartbeat.isoformat(),
            total_tasks=node.total_tasks,
            successful_tasks=node.successful_tasks,
            failed_tasks=node.failed_tasks,
        )
        for node in manager.nodes.values()
    ]


@router.get("/nodes/{node_id}", response_model=NodeRead)
async def get_node(
    node_id: str,
    manager: ClusterManager = Depends(get_cluster_manager),
):
    """获取节点详情"""
    node = manager.nodes.get(node_id)

    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"节点不存在: {node_id}",
        )

    return NodeRead(
        node_id=node.node_id,
        name=node.name,
        endpoint=node.endpoint,
        status=node.status.value,
        load=node.load,
        capabilities=node.capabilities,
        success_rate=node.success_rate,
        last_heartbeat=node.last_heartbeat.isoformat(),
        total_tasks=node.total_tasks,
        successful_tasks=node.successful_tasks,
        failed_tasks=node.failed_tasks,
    )


@router.post("/dispatch", response_model=TaskDispatchResponse)
async def dispatch_task(
    request: TaskDispatchRequest,
    manager: ClusterManager = Depends(get_cluster_manager),
):
    """智能分发任务"""
    try:
        # 解析策略
        strategy = LoadBalanceStrategy(request.strategy)
    except ValueError:
        strategy = LoadBalanceStrategy.LEAST_LOAD

    try:
        result = await manager.dispatch_task_smart(
            task=request.task,
            required_capabilities=request.required_capabilities,
            strategy=strategy,
        )

        return TaskDispatchResponse(
            node_id=result["node_id"],
            node_name=result["node_name"],
            result=result,
        )

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/nodes/{node_id}/dispatch", response_model=Dict[str, Any])
async def dispatch_task_to_node(
    node_id: str,
    task: Dict[str, Any],
    manager: ClusterManager = Depends(get_cluster_manager),
):
    """分发任务到指定节点"""
    try:
        result = await manager.dispatch_task(node_id, task)
        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/status", response_model=ClusterStatusResponse)
async def get_cluster_status(
    manager: ClusterManager = Depends(get_cluster_manager),
):
    """获取集群状态"""
    status = manager.get_cluster_status()

    return ClusterStatusResponse(**status)


@router.post("/monitoring/start")
async def start_monitoring(
    manager: ClusterManager = Depends(get_cluster_manager),
):
    """启动心跳监控"""
    manager.start_monitoring()

    return {"success": True, "message": "心跳监控已启动"}


@router.post("/monitoring/stop")
async def stop_monitoring(
    manager: ClusterManager = Depends(get_cluster_manager),
):
    """停止心跳监控"""
    manager.stop_monitoring()

    return {"success": True, "message": "心跳监控已停止"}
