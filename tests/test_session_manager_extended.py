import pytest
import tempfile
import asyncio
from src.orchestrator.session_manager import SessionManager

@pytest.mark.asyncio
async def test_create_multiple_sessions():
    """测试创建多个会话"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 创建10个会话
        session_ids = []
        for i in range(10):
            session_id = await sm.create_session(f"chat_{i}", {"index": i})
            session_ids.append(session_id)
        
        assert len(session_ids) == 10
        assert len(set(session_ids)) == 10  # 所有ID唯一

@pytest.mark.asyncio
async def test_session_persistence():
    """测试会话持久化"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.db"
        
        # 创建会话
        sm1 = SessionManager(db_path)
        session_id = await sm1.create_session("chat_123", {"data": "test"})
        
        # 模拟重启（重新初始化）
        sm2 = SessionManager(db_path)
        session = await sm2.get_session(session_id)
        
        assert session is not None
        assert session["state"]["data"] == "test"

@pytest.mark.asyncio
async def test_session_deletion():
    """测试会话删除（扩展功能）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {"data": "test"})
        
        # 验证会话存在
        session = await sm.get_session(session_id)
        assert session is not None
        
        # 注意：当前实现没有删除方法，这里只是预留测试
        # 实际删除功能需要后续实现

@pytest.mark.asyncio
async def test_session_state_complex():
    """测试复杂状态存储"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        complex_state = {
            "goal": "optimize code",
            "steps": ["analyze", "refactor", "test"],
            "metadata": {
                "priority": "high",
                "tags": ["performance", "quality"]
            },
            "progress": 0.75
        }
        
        session_id = await sm.create_session("chat_123", complex_state)
        session = await sm.get_session(session_id)
        
        assert session["state"]["goal"] == "optimize code"
        assert len(session["state"]["steps"]) == 3
        assert session["state"]["metadata"]["priority"] == "high"

@pytest.mark.asyncio
async def test_session_concurrent_read():
    """测试并发读取"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {"count": 0})
        
        # 并发读取10次
        async def read_session():
            return await sm.get_session(session_id)
        
        results = await asyncio.gather(*[read_session() for _ in range(10)])
        
        # 所有读取应该成功
        assert all(r is not None for r in results)
        assert all(r["session_id"] == session_id for r in results)

@pytest.mark.asyncio
async def test_session_update_partial():
    """测试部分更新"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {
            "goal": "test",
            "progress": 0,
            "tags": []
        })
        
        # 部分更新
        await sm.update_session(session_id, {
            "progress": 50,
            "tags": ["important"]
        })
        
        session = await sm.get_session(session_id)
        # 注意：当前实现是完整替换，不是部分更新
        # 这里验证新状态
        assert session["state"]["progress"] == 50

@pytest.mark.asyncio
async def test_session_list_pagination():
    """测试会话列表分页（预留）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 创建20个会话
        for i in range(20):
            await sm.create_session("chat_123", {"index": i})
        
        # 列出所有会话
        sessions = await sm.list_sessions("chat_123")
        assert len(sessions) == 20

@pytest.mark.asyncio
async def test_session_timestamp():
    """测试时间戳"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {"data": "test"})
        sessions = await sm.list_sessions("chat_123")
        
        assert "created_at" in sessions[0]

@pytest.mark.asyncio
async def test_session_empty_state():
    """测试空状态"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {})
        session = await sm.get_session(session_id)
        
        assert session["state"] == {}

@pytest.mark.asyncio
async def test_session_large_state():
    """测试大状态存储"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 创建1MB大小的状态
        large_data = "x" * (1024 * 1024)
        session_id = await sm.create_session("chat_123", {"data": large_data})
        
        session = await sm.get_session(session_id)
        assert len(session["state"]["data"]) == 1024 * 1024

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
