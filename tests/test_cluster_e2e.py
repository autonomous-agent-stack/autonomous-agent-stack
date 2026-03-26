"""Cluster 端到端测试

测试场景：
1. 节点注册
2. 节点健康检查
3. 任务分发
4. 负载均衡
5. 集群状态
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.autoresearch.core.services.cluster_manager import (
    ClusterManager,
    ClusterNode,
    NodeStatus,
    LoadBalanceStrategy,
)


# ========================================================================
# Test 1: 节点注册
# ========================================================================

class TestNodeRegistration:
    """节点注册测试"""
    
    @pytest.mark.asyncio
    async def test_register_node(self):
        """测试注册节点"""
        manager = ClusterManager()
        
        # 模拟健康检查成功
        with patch.object(manager, 'health_check', return_value=True):
            node = await manager.register_node(
                name="test-node-1",
                endpoint="https://test.example.com",
                api_key="test-key",
                capabilities=["openclaw", "docker"],
            )
            
            assert node.node_id.startswith("node_test-node-1_")
            assert node.name == "test-node-1"
            assert node.endpoint == "https://test.example.com"
            assert node.capabilities == ["openclaw", "docker"]
            assert node.status == NodeStatus.ONLINE
    
    @pytest.mark.asyncio
    async def test_register_duplicate_node(self):
        """测试注册重复节点"""
        manager = ClusterManager()
        
        with patch.object(manager, 'health_check', return_value=True):
            node1 = await manager.register_node(
                name="test-node-1",
                endpoint="https://test.example.com",
                api_key="test-key",
                capabilities=["openclaw"],
            )
            
            node2 = await manager.register_node(
                name="test-node-2",
                endpoint="https://test.example.com",  # 相同端点
                api_key="test-key-2",
                capabilities=["openclaw"],
            )
            
            # 应该返回相同节点
            assert node1.node_id == node2.node_id
    
    @pytest.mark.asyncio
    async def test_unregister_node(self):
        """测试注销节点"""
        manager = ClusterManager()
        
        with patch.object(manager, 'health_check', return_value=True):
            node = await manager.register_node(
                name="test-node",
                endpoint="https://test.example.com",
                api_key="test-key",
                capabilities=["openclaw"],
            )
            
            assert len(manager.nodes) == 1
            
            success = await manager.unregister_node(node.node_id)
            
            assert success is True
            assert len(manager.nodes) == 0


# ========================================================================
# Test 2: 健康检查
# ========================================================================

class TestHealthCheck:
    """健康检查测试"""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """测试健康检查成功"""
        manager = ClusterManager()
        
        node = ClusterNode(
            node_id="test-node",
            name="test-node",
            endpoint="https://test.example.com",
            api_key="test-key",
        )
        
        # 模拟 HTTP 200 响应
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"load": 0.5}
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            is_healthy = await manager.health_check(node)
            
            assert is_healthy is True
            assert node.status == NodeStatus.ONLINE
            assert node.load == 0.5
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """测试健康检查失败"""
        manager = ClusterManager()
        
        node = ClusterNode(
            node_id="test-node",
            name="test-node",
            endpoint="https://test.example.com",
            api_key="test-key",
        )
        
        # 模拟 HTTP 500 响应
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            is_healthy = await manager.health_check(node)
            
            assert is_healthy is False
            assert node.status == NodeStatus.OFFLINE


# ========================================================================
# Test 3: 任务分发
# ========================================================================

class TestTaskDispatch:
    """任务分发测试"""
    
    @pytest.mark.asyncio
    async def test_dispatch_task(self):
        """测试分发任务"""
        manager = ClusterManager()
        
        with patch.object(manager, 'health_check', return_value=True):
            node = await manager.register_node(
                name="test-node",
                endpoint="https://test.example.com",
                api_key="test-key",
                capabilities=["openclaw"],
            )
        
        # 模拟 HTTP 202 响应
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_response.json.return_value = {"agent_run_id": "ar_123"}
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await manager.dispatch_task(
                node_id=node.node_id,
                task={"prompt": "test"},
            )
            
            assert result["agent_run_id"] == "ar_123"
            assert node.total_tasks == 1
            assert node.successful_tasks == 1
    
    @pytest.mark.asyncio
    async def test_dispatch_task_smart(self):
        """测试智能分发"""
        manager = ClusterManager()
        
        # 注册多个节点
        with patch.object(manager, 'health_check', return_value=True):
            await manager.register_node(
                name="node-1",
                endpoint="https://node1.example.com",
                api_key="key-1",
                capabilities=["openclaw", "webauthn"],
            )
            
            await manager.register_node(
                name="node-2",
                endpoint="https://node2.example.com",
                api_key="key-2",
                capabilities=["openclaw"],
            )
        
        # 模拟 HTTP 响应
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 202
            mock_response.json.return_value = {"agent_run_id": "ar_123"}
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await manager.dispatch_task_smart(
                task={"prompt": "test"},
                required_capabilities=["openclaw", "webauthn"],
            )
            
            # 应该选择 node-1（有 webauthn 能力）
            assert result["node_name"] == "node-1"


# ========================================================================
# Test 4: 负载均衡
# ========================================================================

class TestLoadBalancing:
    """负载均衡测试"""
    
    @pytest.mark.asyncio
    async def test_least_load_strategy(self):
        """测试最低负载策略"""
        manager = ClusterManager()
        
        with patch.object(manager, 'health_check', return_value=True):
            node1 = await manager.register_node(
                name="node-1",
                endpoint="https://node1.example.com",
                api_key="key-1",
                capabilities=["openclaw"],
            )
            node1.load = 0.8
            
            node2 = await manager.register_node(
                name="node-2",
                endpoint="https://node2.example.com",
                api_key="key-2",
                capabilities=["openclaw"],
            )
            node2.load = 0.3
        
        # 选择负载最低的节点
        node = await manager.get_available_node(
            required_capabilities=["openclaw"],
            strategy=LoadBalanceStrategy.LEAST_LOAD,
        )
        
        assert node.name == "node-2"
    
    @pytest.mark.asyncio
    async def test_round_robin_strategy(self):
        """测试轮询策略"""
        manager = ClusterManager()
        
        with patch.object(manager, 'health_check', return_value=True):
            node1 = await manager.register_node(
                name="node-1",
                endpoint="https://node1.example.com",
                api_key="key-1",
                capabilities=["openclaw"],
            )
            node1.total_tasks = 5
            
            node2 = await manager.register_node(
                name="node-2",
                endpoint="https://node2.example.com",
                api_key="key-2",
                capabilities=["openclaw"],
            )
            node2.total_tasks = 2
        
        # 选择任务数最少的节点
        node = await manager.get_available_node(
            required_capabilities=["openclaw"],
            strategy=LoadBalanceStrategy.ROUND_ROBIN,
        )
        
        assert node.name == "node-2"


# ========================================================================
# Test 5: 集群状态
# ========================================================================

class TestClusterStatus:
    """集群状态测试"""
    
    @pytest.mark.asyncio
    async def test_get_cluster_status(self):
        """测试获取集群状态"""
        manager = ClusterManager()
        
        with patch.object(manager, 'health_check', return_value=True):
            await manager.register_node(
                name="node-1",
                endpoint="https://node1.example.com",
                api_key="key-1",
                capabilities=["openclaw"],
            )
            
            await manager.register_node(
                name="node-2",
                endpoint="https://node2.example.com",
                api_key="key-2",
                capabilities=["openclaw"],
            )
        
        status = manager.get_cluster_status()
        
        assert status["total_nodes"] == 2
        assert status["online_nodes"] == 2
        assert status["offline_nodes"] == 0
