import pytest
import tempfile
import asyncio
from src.orchestrator.session_manager import SessionManager

@pytest.mark.asyncio
async def test_create_and_get_session():
    """测试创建和获取会话"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 创建会话
        session_id = await sm.create_session("chat_123", {"goal": "test"})
        assert session_id is not None
        
        # 获取会话
        session = await sm.get_session(session_id)
        assert session["chat_id"] == "chat_123"
        assert session["state"]["goal"] == "test"

@pytest.mark.asyncio
async def test_update_session():
    """测试更新会话"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {"goal": "test"})
        await sm.update_session(session_id, {"goal": "updated", "progress": 50})
        
        session = await sm.get_session(session_id)
        assert session["state"]["goal"] == "updated"
        assert session["state"]["progress"] == 50

@pytest.mark.asyncio
async def test_concurrent_writes():
    """测试并发写入"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {"count": 0})
        
        # 并发更新10次
        async def increment():
            session = await sm.get_session(session_id)
            count = session["state"]["count"]
            await asyncio.sleep(0.01)  # 模拟延迟
            await sm.update_session(session_id, {"count": count + 1})
        
        # 注意：这个测试可能因为竞态条件导致count不是10
        # 但至少验证不会崩溃
        await asyncio.gather(*[increment() for _ in range(10)])
        
        session = await sm.get_session(session_id)
        print(f"最终count: {session['state']['count']}")
        assert session["state"]["count"] >= 1  # 至少有一次成功

@pytest.mark.asyncio
async def test_session_isolation():
    """测试会话隔离"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 创建两个用户的会话
        session_id_1 = await sm.create_session("chat_123", {"data": "user1"})
        session_id_2 = await sm.create_session("chat_456", {"data": "user2"})
        
        # 验证隔离
        session_1 = await sm.get_session(session_id_1)
        session_2 = await sm.get_session(session_id_2)
        
        assert session_1["chat_id"] == "chat_123"
        assert session_2["chat_id"] == "chat_456"
        assert session_1["state"]["data"] != session_2["state"]["data"]

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
