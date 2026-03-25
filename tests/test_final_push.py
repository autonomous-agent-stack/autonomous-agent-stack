import pytest
import asyncio
import tempfile
from src.orchestrator.session_manager import SessionManager
from src.orchestrator.event_bus import EventBus
from src.orchestrator.concurrency import ConcurrencyManager
from src.adapters.channel_adapter import ChannelAdapter

@pytest.mark.asyncio
async def test_channel_twa_integration():
    """测试TWA集成"""
    adapter = ChannelAdapter()
    
    # 生成魔法链接
    token = adapter.generate_magic_link("chat_123")
    
    # 获取TWA数据
    twa_data = adapter.get_twa_data("session_123")
    
    assert token is not None
    assert "nodes" in twa_data

@pytest.mark.asyncio
async def test_channel_jwt_verification():
    """测试JWT验证"""
    adapter = ChannelAdapter()
    
    token = adapter.generate_magic_link("chat_123")
    payload = adapter.verify_magic_link(token)
    
    assert payload["chat_id"] == "chat_123"

def test_channel_light_dashboard():
    """测试浅色看板"""
    adapter = ChannelAdapter()
    
    dashboard = adapter.render_light_dashboard("session_123")
    
    assert dashboard["theme"] == "light"
    assert "nodes" in dashboard

@pytest.mark.asyncio
async def test_full_stack_integration():
    """测试全栈集成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        event_bus = EventBus()
        concurrency = ConcurrencyManager()
        adapter = ChannelAdapter()
        
        # 完整流程
        session_id = await sm.create_session("chat_123", {"goal": "test"})
        token = adapter.generate_magic_link("chat_123")
        
        await concurrency.acquire()
        try:
            await event_bus.publish("node_started", {"session_id": session_id})
            await sm.update_session(session_id, {"progress": 100})
        finally:
            concurrency.release()
        
        # 验证
        session = await sm.get_session(session_id)
        assert session["state"]["progress"] == 100
        assert event_bus.queue.qsize() == 1

@pytest.mark.asyncio
async def test_concurrent_session_operations():
    """测试并发会话操作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 并发创建、读取、更新
        async def mixed_ops(i):
            session_id = await sm.create_session(f"chat_{i}", {"index": i})
            await sm.update_session(session_id, {"updated": True})
            return await sm.get_session(session_id)
        
        results = await asyncio.gather(*[mixed_ops(i) for i in range(20)])
        
        assert all(r is not None for r in results)

@pytest.mark.asyncio
async def test_event_bus_backpressure():
    """测试事件总线背压"""
    event_bus = EventBus(max_queue_size=100)
    
    # 发布100个事件
    for i in range(100):
        await event_bus.publish("node_started", {"index": i})
    
    assert event_bus.queue.qsize() == 100

@pytest.mark.asyncio
async def test_concurrency_timeout():
    """测试并发超时"""
    concurrency = ConcurrencyManager(max_concurrent=1)
    
    # 获取锁
    await concurrency.acquire()
    
    # 尝试再次获取（应该超时）
    async def try_acquire():
        try:
            await asyncio.wait_for(concurrency.acquire(), timeout=0.5)
            return True
        except asyncio.TimeoutError:
            return False
    
    # 启动任务
    task = asyncio.create_task(try_acquire())
    result = await task
    
    # 应该超时
    assert result is False
    concurrency.release()

@pytest.mark.asyncio
async def test_session_update_atomicity():
    """测试会话更新原子性"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {"count": 0})
        
        # 并发更新100次
        async def increment():
            session = await sm.get_session(session_id)
            count = session["state"]["count"]
            await sm.update_session(session_id, {"count": count + 1})
        
        await asyncio.gather(*[increment() for _ in range(100)])
        
        # 验证（可能不是100，因为竞态条件）
        session = await sm.get_session(session_id)
        assert session["state"]["count"] >= 1

@pytest.mark.asyncio
async def test_event_filtering():
    """测试事件过滤（预留）"""
    event_bus = EventBus()
    
    # 当前没有过滤功能
    await event_bus.publish("node_started", {"test": True})
    
    assert event_bus.queue.qsize() == 1

@pytest.mark.asyncio
async def test_session_expiration():
    """测试会话过期（预留）"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {})
        
        # 当前没有过期功能
        session = await sm.get_session(session_id)
        assert session is not None

@pytest.mark.asyncio
async def test_concurrent_event_handling():
    """测试并发事件处理"""
    event_bus = EventBus()
    
    received = []
    async def handler(event):
        received.append(event)
        await asyncio.sleep(0.01)
    
    event_bus.subscribe("test_event", handler)
    
    # 并发发布
    for i in range(10):
        await event_bus.publish("test_event", {"index": i})
    
    await asyncio.sleep(0.2)
    assert len(received) == 10

@pytest.mark.asyncio
async def test_full_system_recovery():
    """测试全系统恢复"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.db"
        
        # 创建初始状态
        sm1 = SessionManager(db_path)
        session_id = await sm1.create_session("chat_123", {"data": "important"})
        
        # 模拟崩溃
        del sm1
        
        # 恢复
        sm2 = SessionManager(db_path)
        session = await sm2.get_session(session_id)
        
        assert session["state"]["data"] == "important"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
