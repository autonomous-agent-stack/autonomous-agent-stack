"""
TopicRouter 测试用例

测试话题路由器的核心功能
"""

import pytest
import sys
import os
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.gateway.topic_router import TopicRouter
from src.gateway.route_table import RouteTable


class TestTopicRouter:
    """TopicRouter 测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        router = TopicRouter()
        
        assert router.bot is None
        assert router.route_table is not None
        assert router.mirror is not None
        assert router.route_count == 0
    
    def test_initialization_with_custom_route_table(self):
        """测试使用自定义路由表初始化"""
        custom_routes = RouteTable()
        router = TopicRouter(route_table=custom_routes)
        
        assert router.route_table == custom_routes
    
    @pytest.mark.asyncio
    async def test_route_message_success(self):
        """测试成功路由消息"""
        router = TopicRouter()
        
        result = await router.route_message(
            "intelligence",
            "这是一条情报消息",
            mirror=False
        )
        
        assert result["status"] == "success"
        assert result["message_type"] == "intelligence"
        assert result["chat_id"] == -1001234567890
        assert result["thread_id"] == 10
        assert "message_id" in result
        assert result["mirrored"] is False
        assert router.route_count == 1
    
    @pytest.mark.asyncio
    async def test_route_message_with_mirror(self):
        """测试带镜像的消息路由"""
        router = TopicRouter()
        
        result = await router.route_message(
            "intelligence",
            "需要备份的情报消息",
            mirror=True,
            sender_id="user_123"
        )
        
        assert result["status"] == "success"
        assert result["mirrored"] is True
        assert "backup_message_id" in result
        assert result["backup_thread_id"] == 110
    
    @pytest.mark.asyncio
    async def test_route_message_unknown_type(self):
        """测试路由未知消息类型"""
        router = TopicRouter()
        
        result = await router.route_message(
            "unknown_type",
            "未知类型的消息"
        )
        
        assert result["status"] == "error"
        assert "No route found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_route_message_disabled_route(self):
        """测试路由到已禁用的路由"""
        router = TopicRouter()
        router.route_table.disable_route("intelligence")
        
        result = await router.route_message(
            "intelligence",
            "测试消息"
        )
        
        assert result["status"] == "error"
        assert "No route found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_route_message_to_security(self):
        """测试路由到安全审计群组"""
        router = TopicRouter()
        
        result = await router.route_message(
            "security",
            "安全审计消息"
        )
        
        assert result["status"] == "success"
        assert result["chat_id"] == -1009876543210
        assert result["thread_id"] is None
    
    @pytest.mark.asyncio
    async def test_mirror_message_manual(self):
        """测试手动镜像消息"""
        router = TopicRouter()
        
        result = await router.mirror_message(
            -1001234567890,
            10,
            -1001234567890,
            110,
            "手动镜像的消息内容"
        )
        
        assert result["status"] == "success"
        assert "backup_message_id" in result
    
    @pytest.mark.asyncio
    async def test_broadcast_message_all(self):
        """测试广播到所有路由"""
        router = TopicRouter()
        
        result = await router.broadcast_message("广播消息测试")
        
        assert result["status"] == "success"
        assert result["sent_count"] == 3
        assert result["total_count"] == 3
        assert len(result["results"]) == 3
    
    @pytest.mark.asyncio
    async def test_broadcast_message_specific_types(self):
        """测试广播到指定类型"""
        router = TopicRouter()
        
        result = await router.broadcast_message(
            "选择性广播",
            message_types=["intelligence", "content"]
        )
        
        assert result["status"] == "success"
        assert result["sent_count"] == 2
        assert result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_broadcast_message_with_disabled_route(self):
        """测试广播包含禁用路由的情况"""
        router = TopicRouter()
        router.route_table.disable_route("security")
        
        result = await router.broadcast_message("测试广播")
        
        # 应该只发送到启用的路由
        assert result["sent_count"] == 2
        assert result["total_count"] == 2
    
    def test_get_router_stats(self):
        """测试获取路由器统计"""
        router = TopicRouter()
        
        stats = router.get_router_stats()
        
        assert stats["total_routed"] == 0
        assert stats["available_routes"] == 3
        assert "mirror_stats" in stats
    
    def test_add_route_via_router(self):
        """测试通过路由器添加路由"""
        router = TopicRouter()
        
        result = router.add_route(
            "testing",
            -1009999999999,
            99,
            "通过路由器添加的测试路由"
        )
        
        assert result is True
        assert "testing" in router.route_table.routes
    
    @pytest.mark.asyncio
    async def test_route_message_without_backup(self):
        """测试路由没有备份的消息（如 security 类型）"""
        router = TopicRouter()
        
        result = await router.route_message(
            "security",
            "安全消息",
            mirror=True
        )
        
        assert result["status"] == "success"
        # security 路由没有备份话题，所以 mirrored 应该是 False
        assert result["mirrored"] is False
