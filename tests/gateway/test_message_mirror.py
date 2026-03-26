"""
MessageMirror 测试用例

测试消息镜像功能
"""

import pytest
import sys
import os
import asyncio

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.gateway.message_mirror import MessageMirror


class TestMessageMirror:
    """MessageMirror 测试类"""
    
    def test_initialization(self):
        """测试初始化"""
        mirror = MessageMirror()
        
        assert mirror.bot is None
        assert mirror.mirror_count == 0
    
    def test_initialization_with_bot(self):
        """测试使用 bot 初始化"""
        mock_bot = "mock_bot"
        mirror = MessageMirror(bot=mock_bot)
        
        assert mirror.bot == mock_bot
    
    @pytest.mark.asyncio
    async def test_mirror_to_backup_success(self):
        """测试成功镜像消息"""
        mirror = MessageMirror()
        
        original_message = {
            "chat_id": -1001234567890,
            "thread_id": 10,
            "message_id": 12345,
            "text": "测试消息内容",
            "sender_id": "user_123"
        }
        
        result = await mirror.mirror_to_backup(
            original_message,
            -1001234567890,
            110
        )
        
        assert result["status"] == "success"
        assert "backup_message_id" in result
        assert result["backup_message_id"] >= 10000
        assert mirror.mirror_count == 1
    
    @pytest.mark.asyncio
    async def test_mirror_to_backup_without_sender(self):
        """测试缺少发送者信息的镜像"""
        mirror = MessageMirror()
        
        original_message = {
            "chat_id": -1001234567890,
            "thread_id": 10,
            "message_id": 12345,
            "text": "测试消息"
        }
        
        result = await mirror.mirror_to_backup(
            original_message,
            -1001234567890,
            110
        )
        
        assert result["status"] == "success"
        assert mirror.mirror_count == 1
    
    @pytest.mark.asyncio
    async def test_mirror_to_backup_without_thread(self):
        """测试镜像到无话题 ID 的群组"""
        mirror = MessageMirror()
        
        original_message = {
            "chat_id": -1009876543210,
            "thread_id": None,
            "message_id": 12345,
            "text": "主群组消息",
            "sender_id": "user_123"
        }
        
        result = await mirror.mirror_to_backup(
            original_message,
            -1009876543210,
            None
        )
        
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_build_mirror_text(self):
        """测试构建镜像文本"""
        mirror = MessageMirror()
        
        original_message = {
            "chat_id": -1001234567890,
            "thread_id": 10,
            "message_id": 12345,
            "text": "这是原始消息内容",
            "sender_id": "user_123"
        }
        
        mirror_text = mirror._build_mirror_text(original_message)
        
        assert "📋 镜像消息 #12345" in mirror_text
        assert "👤 发送者: user_123" in mirror_text
        assert "💬 来源话题: 10" in mirror_text
        assert "这是原始消息内容" in mirror_text
    
    @pytest.mark.asyncio
    async def test_batch_mirror_success(self):
        """测试批量镜像"""
        mirror = MessageMirror()
        
        messages = [
            {
                "chat_id": -1001234567890,
                "thread_id": 10,
                "message_id": i,
                "text": f"消息 {i}",
                "sender_id": "user_123"
            }
            for i in range(1, 6)
        ]
        
        result = await mirror.batch_mirror(
            messages,
            -1001234567890,
            110
        )
        
        assert result["status"] == "success"
        assert result["success_count"] == 5
        assert result["failed_count"] == 0
        assert len(result["results"]) == 5
        assert mirror.mirror_count == 5
    
    @pytest.mark.asyncio
    async def test_batch_mirror_empty_list(self):
        """测试批量空消息列表"""
        mirror = MessageMirror()
        
        result = await mirror.batch_mirror([], -1001234567890, 110)
        
        assert result["status"] == "success"
        assert result["success_count"] == 0
        assert result["failed_count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_mirror_stats(self):
        """测试获取镜像统计"""
        mirror = MessageMirror()
        
        stats = mirror.get_mirror_stats()
        
        assert stats["total_mirrored"] == 0
        assert stats["bot_configured"] is False
        
        # 执行一次镜像后再检查
        await mirror.mirror_to_backup(
            {
                "chat_id": -1001234567890,
                "thread_id": 10,
                "message_id": 1,
                "text": "测试"
            },
            -1001234567890,
            110
        )
        
        stats = mirror.get_mirror_stats()
        assert stats["total_mirrored"] == 1
    
    @pytest.mark.asyncio
    async def test_generate_mock_message_id(self):
        """测试生成模拟消息 ID"""
        mirror = MessageMirror()
        
        mock_id = mirror._generate_mock_message_id()
        
        assert isinstance(mock_id, int)
        assert 10000 <= mock_id <= 99999
    
    def test_get_mirror_stats_with_bot(self):
        """测试带 bot 的镜像统计"""
        mock_bot = "mock_bot"
        mirror = MessageMirror(bot=mock_bot)
        
        stats = mirror.get_mirror_stats()
        
        assert stats["bot_configured"] is True
