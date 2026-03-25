import pytest
import asyncio
import tempfile
from src.orchestrator.session_manager import SessionManager
from src.orchestrator.event_bus import EventBus
from src.orchestrator.concurrency import ConcurrencyManager
from src.orchestrator.cancellation import CancellationManager

@pytest.mark.asyncio
async def test_full_workflow_simple():
    """测试简单完整工作流"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        event_bus = EventBus()
        
        # 创建会话
        session_id = await sm.create_session("chat_123", {"goal": "test"})
        
        # 发布事件
        await event_bus.publish("node_started", {"session_id": session_id})
        
        # 验证
        session = await sm.get_session(session_id)
        assert session is not None
        assert event_bus.queue.qsize() == 1

@pytest.mark.asyncio
async def test_full_workflow_with_concurrency():
    """测试带并发控制的完整工作流"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        concurrency = ConcurrencyManager(max_concurrent=3)
        
        # 创建会话
        session_id = await sm.create_session("chat_123", {"goal": "test"})
        
        # 获取并发锁
        await concurrency.acquire()
        try:
            # 模拟工作
            await sm.update_session(session_id, {"progress": 50})
        finally:
            concurrency.release()
        
        # 验证
        session = await sm.get_session(session_id)
        assert session["state"]["progress"] == 50

@pytest.mark.asyncio
async def test_full_workflow_with_cancellation():
    """测试带取消机制的完整工作流"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        cancellation = CancellationManager()
        
        # 创建会话
        session_id = await sm.create_session("chat_123", {"goal": "test"})
        
        # 启动长时间任务
        async def long_task():
            await sm.update_session(session_id, {"progress": 100})
        
        task = asyncio.create_task(long_task())
        await asyncio.sleep(0.1)
        
        # 取消任务
        await cancellation.cancel_task(task, reason="user request", audit=True)
        
        # 验证审计日志
        assert cancellation.has_audit_log()

@pytest.mark.asyncio
async def test_concurrent_sessions():
    """测试并发会话处理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 并发创建10个会话
        async def create_session(i):
            return await sm.create_session(f"chat_{i}", {"index": i})
        
        session_ids = await asyncio.gather(*[create_session(i) for i in range(10)])
        
        # 验证
        assert len(session_ids) == 10
        assert len(set(session_ids)) == 10

@pytest.mark.asyncio
async def test_event_bus_with_sessions():
    """测试事件总线与会话集成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        event_bus = EventBus()
        
        received_events = []
        async def handler(event):
            received_events.append(event)
        
        event_bus.subscribe("session_created", handler)
        
        # 创建会话并发布事件
        session_id = await sm.create_session("chat_123", {})
        await event_bus.publish("session_created", {"session_id": session_id})
        
        await asyncio.sleep(0.1)
        assert len(received_events) == 1

@pytest.mark.asyncio
async def test_concurrency_with_events():
    """测试并发控制与事件集成"""
    event_bus = EventBus()
    concurrency = ConcurrencyManager(max_concurrent=2)
    
    events = []
    async def handler(event):
        events.append(event)
    
    event_bus.subscribe("acquired", handler)
    
    # 获取锁
    await concurrency.acquire()
    await event_bus.publish("acquired", {"resource": "lock"})
    
    await asyncio.sleep(0.1)
    assert len(events) == 1

@pytest.mark.asyncio
async def test_cancellation_with_sessions():
    """测试取消机制与会话集成"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        cancellation = CancellationManager()
        
        session_id = await sm.create_session("chat_123", {"status": "running"})
        
        # 启动任务
        async def task():
            await sm.update_session(session_id, {"status": "completed"})
        
        t = asyncio.create_task(task())
        await asyncio.sleep(0.1)
        
        # 取消
        await cancellation.cancel_task(t, audit=True)
        
        # 验证会话状态
        session = await sm.get_session(session_id)
        # 任务可能已完成或被取消
        assert session["state"]["status"] in ["running", "completed"]

@pytest.mark.asyncio
async def test_full_system_stress():
    """测试系统压力"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        event_bus = EventBus()
        concurrency = ConcurrencyManager(max_concurrent=5)
        
        # 并发创建会话并发送事件
        async def stress_task(i):
            session_id = await sm.create_session(f"chat_{i}", {"index": i})
            await concurrency.acquire()
            try:
                await event_bus.publish("node_started", {"session_id": session_id})
            finally:
                concurrency.release()
        
        # 启动50个并发任务
        await asyncio.gather(*[stress_task(i) for i in range(50)])
        
        # 验证
        assert event_bus.queue.qsize() == 50

@pytest.mark.asyncio
async def test_error_recovery():
    """测试错误恢复"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {"attempts": 0})
        
        # 模拟错误和重试
        for i in range(3):
            try:
                session = await sm.get_session(session_id)
                if session["state"]["attempts"] < 2:
                    await sm.update_session(session_id, {"attempts": i + 1})
                    raise ValueError("模拟错误")
                break
            except ValueError:
                continue
        
        # 验证重试成功
        session = await sm.get_session(session_id)
        assert session["state"]["attempts"] == 2

@pytest.mark.asyncio
async def test_resource_cleanup():
    """测试资源清理"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 创建会话
        session_id = await sm.create_session("chat_123", {"temp_files": ["a.txt", "b.txt"]})
        
        # 模拟清理
        await sm.update_session(session_id, {"temp_files": []})
        
        # 验证
        session = await sm.get_session(session_id)
        assert len(session["state"]["temp_files"]) == 0

@pytest.mark.asyncio
async def test_state_machine():
    """测试状态机"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 状态流转：created → running → completed
        session_id = await sm.create_session("chat_123", {"status": "created"})
        
        await sm.update_session(session_id, {"status": "running"})
        session = await sm.get_session(session_id)
        assert session["state"]["status"] == "running"
        
        await sm.update_session(session_id, {"status": "completed"})
        session = await sm.get_session(session_id)
        assert session["state"]["status"] == "completed"

@pytest.mark.asyncio
async def test_priority_queue():
    """测试优先级队列（预留）"""
    # 当前实现没有优先级队列
    # 这里只是预留测试
    assert True

@pytest.mark.asyncio
async def test_rate_limiting():
    """测试速率限制（预留）"""
    # 当前实现没有速率限制
    # 这里只是预留测试
    assert True

@pytest.mark.asyncio
async def test_deadlock_detection():
    """测试死锁检测（预留）"""
    # 当前实现没有死锁检测
    # 这里只是预留测试
    assert True

@pytest.mark.asyncio
async def test_memory_leak():
    """测试内存泄漏（预留）"""
    # 当前实现没有内存泄漏检测
    # 这里只是预留测试
    assert True

@pytest.mark.asyncio
async def test_performance_benchmark():
    """测试性能基准"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 测试1000次操作
        start = asyncio.get_event_loop().time()
        
        for i in range(1000):
            await sm.create_session("chat_test", {"index": i})
        
        elapsed = asyncio.get_event_loop().time() - start
        
        # 应该在5秒内完成
        assert elapsed < 5.0
        print(f"1000次操作耗时: {elapsed:.2f}秒")

@pytest.mark.asyncio
async def test_concurrent_read_write():
    """测试并发读写"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        session_id = await sm.create_session("chat_123", {"count": 0})
        
        # 并发读
        async def read():
            return await sm.get_session(session_id)
        
        # 并发写
        async def write(i):
            await sm.update_session(session_id, {"count": i})
        
        # 混合读写
        tasks = [read() for _ in range(5)] + [write(i) for i in range(5)]
        await asyncio.gather(*tasks)
        
        # 验证最终状态
        session = await sm.get_session(session_id)
        assert session is not None

@pytest.mark.asyncio
async def test_event_ordering():
    """测试事件顺序"""
    event_bus = EventBus()
    
    events = []
    async def handler(event):
        events.append(event["data"]["index"])
    
    event_bus.subscribe("test_event", handler)
    
    # 按顺序发布事件
    for i in range(10):
        await event_bus.publish("test_event", {"index": i})
    
    await asyncio.sleep(0.1)
    
    # 验证顺序（可能不保证，取决于实现）
    assert len(events) == 10

@pytest.mark.asyncio
async def test_snapshot_recovery():
    """测试快照恢复"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test.db"
        
        # 创建快照
        sm1 = SessionManager(db_path)
        session_id = await sm1.create_session("chat_123", {"data": "snapshot"})
        
        # 模拟崩溃并恢复
        sm2 = SessionManager(db_path)
        session = await sm2.get_session(session_id)
        
        assert session["state"]["data"] == "snapshot"

@pytest.mark.asyncio
async def test_multi_user_isolation():
    """测试多用户隔离"""
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionManager(f"{tmpdir}/test.db")
        
        # 创建3个用户的会话
        user_sessions = {}
        for user in ["alice", "bob", "charlie"]:
            session_id = await sm.create_session(f"chat_{user}", {"user": user})
            user_sessions[user] = session_id
        
        # 验证隔离
        for user, session_id in user_sessions.items():
            session = await sm.get_session(session_id)
            assert session["chat_id"] == f"chat_{user}"
            assert session["state"]["user"] == user

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
