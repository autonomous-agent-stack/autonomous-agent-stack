"""
集成测试 - 测试完整的路由和镜像流程
"""

import pytest
import sys
import os
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.gateway.topic_router import TopicRouter
from src.security.apple_double_cleaner import AppleDoubleCleaner


class TestIntegration:
    """集成测试类"""
    
    @pytest.mark.asyncio
    async def test_full_routing_workflow(self):
        """测试完整的路由工作流"""
        # 1. 环境清理
        cleaned = AppleDoubleCleaner.clean(".")
        assert cleaned >= 0
        
        # 2. 初始化路由器
        router = TopicRouter()
        
        # 3. 路由不同类型的消息
        intelligence_result = await router.route_message(
            "intelligence",
            "市场情报：某公司计划发布新产品",
            mirror=True
        )
        
        content_result = await router.route_message(
            "content",
            "内容实验室：新文章草稿完成",
            mirror=True
        )
        
        security_result = await router.route_message(
            "security",
            "安全审计：检测到异常登录",
            mirror=False
        )
        
        # 4. 验证结果
        assert intelligence_result["status"] == "success"
        assert intelligence_result["mirrored"] is True
        
        assert content_result["status"] == "success"
        assert content_result["mirrored"] is True
        
        assert security_result["status"] == "success"
        assert security_result["mirrored"] is False  # security 没有备份
        
        # 5. 验证统计
        stats = router.get_router_stats()
        assert stats["total_routed"] == 3
    
    @pytest.mark.asyncio
    async def test_dynamic_route_management(self):
        """测试动态路由管理"""
        router = TopicRouter()
        
        # 添加新路由
        add_result = router.add_route(
            "urgent",
            -1001111111111,
            50,
            "紧急通知话题"
        )
        assert add_result is True
        
        # 路由到新话题
        result = await router.route_message(
            "urgent",
            "紧急：服务器宕机",
            mirror=True
        )
        
        assert result["status"] == "success"
        assert result["chat_id"] == -1001111111111
        assert result["thread_id"] == 50
        
        # 禁用路由
        router.route_table.disable_route("urgent")
        
        # 再次尝试路由应该失败
        result = await router.route_message(
            "urgent",
            "这应该失败"
        )
        
        assert result["status"] == "error"
    
    @pytest.mark.asyncio
    async def test_broadcast_with_mixed_states(self):
        """测试混合状态下的广播"""
        router = TopicRouter()
        
        # 禁用部分路由
        router.route_table.disable_route("content")
        
        # 广播应该只发送到启用的路由
        result = await router.broadcast_message("重要通知")
        
        assert result["sent_count"] == 2  # intelligence 和 security
        assert result["total_count"] == 2
    
    @pytest.mark.asyncio
    async def test_manual_mirror_workflow(self):
        """测试手动镜像工作流"""
        router = TopicRouter()
        
        # 手动镜像消息
        result = await router.mirror_message(
            source_chat_id=-1001234567890,
            source_thread_id=10,
            target_chat_id=-1001234567890,
            target_thread_id=110,
            text="需要手动备份的重要内容"
        )
        
        assert result["status"] == "success"
        assert result["backup_message_id"] >= 10000
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """测试错误处理"""
        router = TopicRouter()
        
        # 测试无效消息类型
        result = await router.route_message("invalid", "测试")
        assert result["status"] == "error"
        
        # 测试空消息（应该成功）
        result = await router.route_message("intelligence", "")
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_concurrent_routing(self):
        """测试并发路由"""
        router = TopicRouter()
        
        # 并发路由多条消息
        tasks = [
            router.route_message("intelligence", f"消息 {i}", mirror=True)
            for i in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 所有消息都应该成功
        assert all(r["status"] == "success" for r in results)
        assert router.route_count == 10
    
    @pytest.mark.asyncio
    async def test_backup_route_calculation(self):
        """测试备份路由计算"""
        router = TopicRouter()
        
        # intelligence 路由的备份
        backup = router.route_table.get_backup_route("intelligence")
        assert backup is not None
        assert backup["thread_id"] == 110  # 10 + 100
        
        # content 路由的备份
        backup = router.route_table.get_backup_route("content")
        assert backup is not None
        assert backup["thread_id"] == 120  # 20 + 100
        
        # security 路由没有备份
        backup = router.route_table.get_backup_route("security")
        assert backup is None
    
    def test_security_cleanup_before_operations(self):
        """测试操作前的安全清理"""
        # 创建一些测试用的 ._ 文件
        test_dir = "/tmp/test_appledouble"
        os.makedirs(test_dir, exist_ok=True)
        
        test_file = os.path.join(test_dir, "._test")
        with open(test_file, 'w') as f:
            f.write("test")
        
        # 执行清理
        cleaned = AppleDoubleCleaner.clean(test_dir)
        
        assert cleaned >= 0
        
        # 清理后文件应该被删除
        assert not os.path.exists(test_file)
        
        # 清理测试目录
        os.rmdir(test_dir)
    
    @pytest.mark.asyncio
    async def test_route_update_and_reroute(self):
        """测试路由更新后重新路由"""
        router = TopicRouter()
        
        # 初始路由
        result1 = await router.route_message("intelligence", "测试1")
        assert result1["thread_id"] == 10
        
        # 更新路由
        router.route_table.update_route("intelligence", thread_id=15)
        
        # 新路由应该使用更新后的配置
        result2 = await router.route_message("intelligence", "测试2")
        assert result2["thread_id"] == 15
    
    @pytest.mark.asyncio
    async def test_list_routes_completeness(self):
        """测试列出所有路由的完整性"""
        router = TopicRouter()
        
        routes = router.route_table.list_routes()
        
        # 应该包含所有默认路由
        route_types = [r["type"] for r in routes]
        assert "intelligence" in route_types
        assert "content" in route_types
        assert "security" in route_types
        
        # 每个路由应该有必要的字段
        for route in routes:
            assert "type" in route
            assert "chat_id" in route
            assert "description" in route
            assert "enabled" in route
