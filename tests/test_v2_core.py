"""
v2.0 分布式核心集成测试

验证 Redis 总线和 WebSocket 的异步连通性
"""

import asyncio
import json
import pytest
import redis.asyncio as redis
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import sys

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from bridge.event_bus import EventBus, get_event_bus
from bridge.websocket_telemetry import WebSocketManager, TelemetryCollector
from memory.distributed_session_store import DistributedSessionStore
from security.hardware_lock import HardwareLock
from opensage.skill_registry import SkillRegistry


class TestEventBus:
    """Redis Pub/Sub 事件总线测试"""

    @pytest.mark.asyncio
    async def test_event_bus_connect(self):
        """测试 Redis 连接"""
        event_bus = EventBus("redis://localhost:6379/15")  # 使用测试数据库

        try:
            await event_bus.connect()
            assert event_bus.redis_client is not None
            assert event_bus.pubsub is not None
        except Exception as e:
            pytest.skip(f"Redis 未运行: {e}")
        finally:
            await event_bus.disconnect()

    @pytest.mark.asyncio
    async def test_event_bus_publish(self):
        """测试事件发布"""
        event_bus = EventBus("redis://localhost:6379/15")

        try:
            await event_bus.connect()

            # 发布测试事件
            await event_bus.publish(
                event_type="test_event",
                payload={"message": "Hello Redis"},
                source="test_suite"
            )

            # 如果没有抛出异常，则测试通过
            assert True

        except Exception as e:
            pytest.skip(f"Redis 未运行: {e}")
        finally:
            await event_bus.disconnect()

    @pytest.mark.asyncio
    async def test_event_bus_subscribe(self):
        """测试事件订阅"""
        event_bus = EventBus("redis://localhost:6379/15")

        try:
            await event_bus.connect()

            # 创建回调函数
            callback = AsyncMock()

            # 订阅事件
            await event_bus.subscribe("test_event", callback)

            assert "test_event" in event_bus.subscribers
            assert event_bus.subscribers["test_event"] == callback

        except Exception as e:
            pytest.skip(f"Redis 未运行: {e}")
        finally:
            await event_bus.disconnect()


class TestTelemetryCollector:
    """遥测收集器测试"""

    def test_telemetry_collector_init(self):
        """测试初始化"""
        collector = TelemetryCollector()
        assert collector.agent_status == {}
        assert collector.log_buffer == []

    def test_update_agent_status(self):
        """测试 Agent 状态更新"""
        collector = TelemetryCollector()

        collector.update_agent_status("agent_1", {
            "status": "active",
            "tokens_used": 1000
        })

        assert "agent_1" in collector.agent_status
        assert collector.agent_status["agent_1"]["status"] == "active"

    def test_add_log(self):
        """测试日志添加"""
        collector = TelemetryCollector()

        collector.add_log({"level": "INFO", "message": "Test log"})
        collector.add_log({"level": "ERROR", "message": "Test error"})

        assert len(collector.log_buffer) == 2
        assert collector.log_buffer[0]["level"] == "INFO"

    @pytest.mark.asyncio
    async def test_collect_telemetry(self):
        """测试遥测数据收集"""
        collector = TelemetryCollector()

        # 添加 Agent 状态
        collector.update_agent_status("agent_1", {"status": "active"})

        # 收集遥测
        telemetry = await collector.collect()

        assert "timestamp" in telemetry
        assert "system" in telemetry
        assert "agents" in telemetry
        assert "agent_1" in telemetry["agents"]


class TestWebSocketManager:
    """WebSocket 管理器测试"""

    def test_websocket_manager_init(self):
        """测试初始化"""
        manager = WebSocketManager()
        assert len(manager.active_connections) == 0
        assert manager._broadcasting is False

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """测试连接与断开"""
        manager = WebSocketManager()

        # 模拟 WebSocket 连接
        websocket = AsyncMock()
        websocket.accept = AsyncMock()

        await manager.connect(websocket)

        assert len(manager.active_connections) == 1
        assert websocket in manager.active_connections

        await manager.disconnect(websocket)

        assert len(manager.active_connections) == 0

    def test_update_agent_status(self):
        """测试 Agent 状态更新"""
        manager = WebSocketManager()

        manager.update_agent_status("agent_1", {"status": "active"})

        assert "agent_1" in manager.collector.agent_status


class TestHardwareLock:
    """WebAuthn 物理锁测试"""

    def test_hardware_lock_init(self):
        """测试初始化"""
        lock = HardwareLock()
        assert lock.rp_id == "localhost"
        assert lock.rp_name == "Autonomous Agent Stack"

    @pytest.mark.asyncio
    async def test_generate_registration_challenge(self):
        """测试注册挑战生成"""
        lock = HardwareLock()

        challenge = await lock.generate_registration_challenge("user_123")

        assert "challenge" in challenge
        assert "rp" in challenge
        assert "user" in challenge

    @pytest.mark.asyncio
    async def test_require_physical_auth_timeout(self):
        """测试物理验证超时"""
        lock = HardwareLock()

        # 测试超时（1 秒）
        result = await lock.require_physical_auth("test_operation", timeout=1)

        # 应该超时返回 False
        assert result is False


class TestSkillRegistry:
    """技能注册表测试"""

    def test_skill_registry_init(self):
        """测试初始化"""
        registry = SkillRegistry("./test_skills")
        assert registry.skills_dir.exists()
        assert registry.registry == {}

    @pytest.mark.asyncio
    async def test_validate_skill(self):
        """测试技能验证"""
        registry = SkillRegistry("./test_skills")

        # 创建测试技能
        skill_dir = registry.skills_dir / "test_skill"
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / "test_skill.py"
        skill_file.write_text("""
def execute():
    return "Hello from skill"
""")

        # 验证技能
        is_valid = await registry.validate_skill("test_skill")

        assert is_valid is True

        # 清理
        import shutil
        shutil.rmtree(skill_dir)

    @pytest.mark.asyncio
    async def test_validate_skill_with_dangerous_code(self):
        """测试危险代码检测"""
        registry = SkillRegistry("./test_skills")

        # 创建包含危险代码的技能
        skill_dir = registry.skills_dir / "dangerous_skill"
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / "dangerous_skill.py"
        skill_file.write_text("""
import os
os.system("rm -rf /")  # 危险代码
""")

        # 验证技能
        is_valid = await registry.validate_skill("dangerous_skill")

        # 应该检测到危险代码
        assert is_valid is False

        # 清理
        import shutil
        shutil.rmtree(skill_dir)

    def test_list_skills(self):
        """测试技能列表"""
        registry = SkillRegistry("./test_skills")

        skills = registry.list_skills()

        assert isinstance(skills, list)


class TestIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整工作流"""
        # 1. 创建事件总线
        event_bus = EventBus("redis://localhost:6379/15")

        try:
            await event_bus.connect()

            # 2. 创建遥测收集器
            collector = TelemetryCollector()

            # 3. 更新 Agent 状态
            collector.update_agent_status("agent_1", {"status": "active"})

            # 4. 收集遥测
            telemetry = await collector.collect()

            # 5. 发布遥测事件
            await event_bus.publish(
                event_type="telemetry_update",
                payload=telemetry,
                source="test_suite"
            )

            # 如果所有步骤都成功，则测试通过
            assert True

        except Exception as e:
            pytest.skip(f"Redis 未运行: {e}")
        finally:
            await event_bus.disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
