"""Cluster Manager - 集群管理器

功能：
1. 节点注册与发现
2. 健康监控（心跳检测）
3. 任务分发
4. 结果汇总
5. 负载均衡
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import httpx
from enum import Enum

logger = logging.getLogger(__name__)


class NodeStatus(str, Enum):
    """节点状态"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    UNKNOWN = "unknown"


class LoadBalanceStrategy(str, Enum):
    """负载均衡策略"""
    LEAST_LOAD = "least_load"      # 最低负载
    ROUND_ROBIN = "round_robin"    # 轮询
    RANDOM = "random"              # 随机
    CAPABILITY = "capability"      # 按能力


@dataclass
class ClusterNode:
    """集群节点"""
    node_id: str
    name: str
    endpoint: str  # https://xxx.trycloudflare.com
    api_key: str
    status: NodeStatus = NodeStatus.UNKNOWN
    last_heartbeat: datetime = None
    load: float = 0.0  # 0-1
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    
    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.utcnow()
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_tasks == 0:
            return 1.0
        return self.successful_tasks / self.total_tasks
    
    @property
    def is_available(self) -> bool:
        """是否可用"""
        return self.status == NodeStatus.ONLINE and self.load < 0.9


class ClusterManager:
    """集群管理器"""
    
    def __init__(
        self,
        heartbeat_interval: int = 30,
        heartbeat_timeout: int = 90,
        max_retries: int = 3,
    ):
        self.nodes: Dict[str, ClusterNode] = {}
        self.heartbeat_interval = heartbeat_interval  # 秒
        self.heartbeat_timeout = heartbeat_timeout  # 秒
        self.max_retries = max_retries
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def register_node(
        self,
        name: str,
        endpoint: str,
        api_key: str,
        capabilities: List[str],
        metadata: Dict[str, Any] = None,
    ) -> ClusterNode:
        """注册节点
        
        Args:
            name: 节点名称
            endpoint: 节点端点（https://xxx.trycloudflare.com）
            api_key: API 密钥
            capabilities: 能力列表（["openclaw", "docker", "webauthn"]）
            metadata: 元数据
            
        Returns:
            ClusterNode
        """
        # 检查是否已存在
        for node in self.nodes.values():
            if node.endpoint == endpoint:
                logger.warning("⚠️ 节点已存在: %s (%s)", name, endpoint)
                return node
        
        # 生成节点 ID
        node_id = f"node_{name}_{int(datetime.utcnow().timestamp())}"
        
        # 创建节点
        node = ClusterNode(
            node_id=node_id,
            name=name,
            endpoint=endpoint.rstrip("/"),
            api_key=api_key,
            status=NodeStatus.UNKNOWN,
            capabilities=capabilities,
            metadata=metadata or {},
        )
        
        # 健康检查
        is_healthy = await self.health_check(node)
        node.status = NodeStatus.ONLINE if is_healthy else NodeStatus.OFFLINE
        
        # 保存节点
        self.nodes[node_id] = node
        
        logger.info("✅ 节点已注册: %s (%s) - %s", name, endpoint, node.status.value)
        
        return node
    
    async def unregister_node(self, node_id: str) -> bool:
        """注销节点
        
        Args:
            node_id: 节点 ID
            
        Returns:
            是否成功
        """
        if node_id not in self.nodes:
            logger.warning("⚠️ 节点不存在: %s", node_id)
            return False
        
        node = self.nodes[node_id]
        del self.nodes[node_id]
        
        logger.info("✅ 节点已注销: %s (%s)", node.name, node.endpoint)
        
        return True
    
    async def health_check(self, node: ClusterNode) -> bool:
        """健康检查
        
        Args:
            node: 节点
            
        Returns:
            是否健康
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{node.endpoint}/health",
                    headers={"X-API-Key": node.api_key},
                    timeout=10,
                )
                
                if response.status_code == 200:
                    # 解析响应（可能包含负载信息）
                    try:
                        data = response.json()
                        node.load = data.get("load", 0.0)
                        node.metadata.update(data.get("metadata", {}))
                    except:
                        pass
                    
                    node.last_heartbeat = datetime.utcnow()
                    node.status = NodeStatus.ONLINE
                    return True
                else:
                    node.status = NodeStatus.OFFLINE
                    return False
        
        except Exception as e:
            logger.warning("⚠️ 节点健康检查失败: %s - %s", node.name, e)
            node.status = NodeStatus.OFFLINE
            return False
    
    async def get_available_node(
        self,
        required_capabilities: List[str] = None,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOAD,
    ) -> Optional[ClusterNode]:
        """获取可用节点
        
        Args:
            required_capabilities: 必需能力列表
            strategy: 负载均衡策略
            
        Returns:
            ClusterNode or None
        """
        # 1. 筛选可用节点
        available_nodes = [
            node for node in self.nodes.values()
            if node.is_available
        ]
        
        if not available_nodes:
            logger.warning("⚠️ 无可用节点")
            return None
        
        # 2. 筛选满足能力要求的节点
        if required_capabilities:
            available_nodes = [
                node for node in available_nodes
                if all(cap in node.capabilities for cap in required_capabilities)
            ]
        
        if not available_nodes:
            logger.warning("⚠️ 无满足能力的节点: %s", required_capabilities)
            return None
        
        # 3. 根据策略选择节点
        if strategy == LoadBalanceStrategy.LEAST_LOAD:
            # 选择负载最低的节点
            available_nodes.sort(key=lambda n: n.load)
            return available_nodes[0]
        
        elif strategy == LoadBalanceStrategy.RANDOM:
            # 随机选择
            import random
            return random.choice(available_nodes)
        
        elif strategy == LoadBalanceStrategy.ROUND_ROBIN:
            # 轮询（基于总任务数）
            available_nodes.sort(key=lambda n: n.total_tasks)
            return available_nodes[0]
        
        else:
            # 默认：最低负载
            available_nodes.sort(key=lambda n: n.load)
            return available_nodes[0]
    
    async def dispatch_task(
        self,
        node_id: str,
        task: Dict[str, Any],
    ) -> Dict[str, Any]:
        """分发任务到节点
        
        Args:
            node_id: 节点 ID
            task: 任务数据
            
        Returns:
            任务结果
        """
        node = self.nodes.get(node_id)
        if not node:
            raise ValueError(f"节点不存在: {node_id}")
        
        logger.info("🚀 分发任务到节点: %s", node.name)
        
        try:
            # 更新节点状态
            node.status = NodeStatus.BUSY
            node.total_tasks += 1
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{node.endpoint}/api/v1/openclaw/agents",
                    json=task,
                    headers={"X-API-Key": node.api_key},
                    timeout=300,
                )
                
                if response.status_code in [200, 202]:
                    result = response.json()
                    node.successful_tasks += 1
                    node.status = NodeStatus.ONLINE
                    logger.info("✅ 任务分发成功: %s", node.name)
                    return result
                else:
                    node.failed_tasks += 1
                    node.status = NodeStatus.ONLINE
                    logger.error("❌ 任务分发失败: %s - %s", node.name, response.text)
                    raise RuntimeError(f"任务分发失败: {response.text}")
        
        except Exception as e:
            node.failed_tasks += 1
            node.status = NodeStatus.ONLINE
            logger.error("❌ 任务分发异常: %s - %s", node.name, e)
            raise
    
    async def dispatch_task_smart(
        self,
        task: Dict[str, Any],
        required_capabilities: List[str] = None,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.LEAST_LOAD,
    ) -> Dict[str, Any]:
        """智能分发任务（自动选择节点）
        
        Args:
            task: 任务数据
            required_capabilities: 必需能力列表
            strategy: 负载均衡策略
            
        Returns:
            任务结果（包含节点信息）
        """
        # 1. 获取最佳节点
        node = await self.get_available_node(required_capabilities, strategy)
        
        if not node:
            raise RuntimeError("无可用节点")
        
        # 2. 分发任务
        result = await self.dispatch_task(node.node_id, task)
        
        # 3. 添加节点信息
        result["node_id"] = node.node_id
        result["node_name"] = node.name
        
        return result
    
    async def start_heartbeat_monitor(self):
        """启动心跳监控"""
        logger.info("💓 启动心跳监控")
        
        while True:
            try:
                # 并发检查所有节点
                tasks = [
                    self.health_check(node)
                    for node in self.nodes.values()
                ]
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                
                # 检查超时节点
                now = datetime.utcnow()
                for node in self.nodes.values():
                    if node.status == NodeStatus.ONLINE:
                        elapsed = (now - node.last_heartbeat).total_seconds()
                        if elapsed > self.heartbeat_timeout:
                            logger.warning("⚠️ 节点心跳超时: %s (%.0fs)", node.name, elapsed)
                            node.status = NodeStatus.OFFLINE
                
                await asyncio.sleep(self.heartbeat_interval)
            
            except Exception as e:
                logger.error("❌ 心跳监控异常: %s", e)
                await asyncio.sleep(5)
    
    def start_monitoring(self):
        """启动监控（非阻塞）"""
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self.start_heartbeat_monitor())
            logger.info("✅ 心跳监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            logger.info("🛑 心跳监控已停止")
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """获取集群状态"""
        online_nodes = [n for n in self.nodes.values() if n.status == NodeStatus.ONLINE]
        offline_nodes = [n for n in self.nodes.values() if n.status == NodeStatus.OFFLINE]
        
        return {
            "total_nodes": len(self.nodes),
            "online_nodes": len(online_nodes),
            "offline_nodes": len(offline_nodes),
            "total_tasks": sum(n.total_tasks for n in self.nodes.values()),
            "successful_tasks": sum(n.successful_tasks for n in self.nodes.values()),
            "failed_tasks": sum(n.failed_tasks for n in self.nodes.values()),
            "nodes": [
                {
                    "node_id": node.node_id,
                    "name": node.name,
                    "endpoint": node.endpoint,
                    "status": node.status.value,
                    "load": node.load,
                    "capabilities": node.capabilities,
                    "success_rate": node.success_rate,
                    "last_heartbeat": node.last_heartbeat.isoformat(),
                }
                for node in self.nodes.values()
            ],
        }


# 全局实例
_cluster_manager: Optional[ClusterManager] = None


def get_cluster_manager() -> ClusterManager:
    """获取集群管理器实例"""
    global _cluster_manager
    if _cluster_manager is None:
        _cluster_manager = ClusterManager()
    return _cluster_manager


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        manager = ClusterManager()
        
        # 注册节点
        node1 = await manager.register_node(
            name="openclaw-prod-1",
            endpoint="https://openclaw-prod-1.example.com",
            api_key="test-key-1",
            capabilities=["openclaw", "telegram", "webauthn"],
        )
        
        node2 = await manager.register_node(
            name="openclaw-prod-2",
            endpoint="https://openclaw-prod-2.example.com",
            api_key="test-key-2",
            capabilities=["openclaw", "discord"],
        )
        
        # 查看集群状态
        status = manager.get_cluster_status()
        print(f"集群状态: {status}")
        
        # 获取可用节点
        node = await manager.get_available_node(
            required_capabilities=["openclaw", "webauthn"],
        )
        
        if node:
            print(f"最佳节点: {node.name}")
    
    asyncio.run(test())
