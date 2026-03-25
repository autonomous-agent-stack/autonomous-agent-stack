import pytest
import asyncio
from src.orchestrator.event_bus import EventBus

@pytest.mark.asyncio
async def test_event_publish_subscribe():
    """测试事件发布订阅"""
    bus = EventBus()
    
    received = []
    async def handler(event):
        received.append(event)
    
    bus.subscribe("node_started", handler)
    await bus.publish("node_started", {"node_id": "test"})
    
    await asyncio.sleep(0.1)
    assert len(received) == 1
    assert received[0]["type"] == "node_started"

@pytest.mark.asyncio
async def test_event_multiple_subscribers():
    """测试多个订阅者"""
    bus = EventBus()
    
    received1 = []
    received2 = []
    
    async def handler1(event):
        received1.append(event)
    
    async def handler2(event):
        received2.append(event)
    
    bus.subscribe("node_started", handler1)
    bus.subscribe("node_started", handler2)
    
    await bus.publish("node_started", {"node_id": "test"})
    await asyncio.sleep(0.1)
    
    assert len(received1) == 1
    assert len(received2) == 1

@pytest.mark.asyncio
async def test_event_queue_size():
    """测试事件队列大小"""
    bus = EventBus(max_queue_size=100)
    
    # 发布100个事件
    for i in range(100):
        await bus.publish("node_started", {"index": i})
    
    # 队列应该有100个事件
    assert bus.queue.qsize() == 100

@pytest.mark.asyncio
async def test_event_types():
    """测试所有事件类型"""
    bus = EventBus()
    
    for event_type in bus.event_types:
        await bus.publish(event_type, {"test": True})
    
    assert bus.queue.qsize() == len(bus.event_types)

@pytest.mark.asyncio
async def test_event_invalid_type():
    """测试无效事件类型"""
    bus = EventBus()
    
    with pytest.raises(ValueError):
        await bus.publish("invalid_type", {})

@pytest.mark.asyncio
async def test_event_concurrent_publish():
    """测试并发发布"""
    bus = EventBus()
    
    async def publish_events(count):
        for i in range(count):
            await bus.publish("node_started", {"index": i})
    
    # 并发发布
    await asyncio.gather(*[publish_events(10) for _ in range(5)])
    
    assert bus.queue.qsize() == 50

@pytest.mark.asyncio
async def test_event_sse_stream():
    """测试SSE流"""
    bus = EventBus()
    
    # 发布一个事件
    await bus.publish("node_started", {"test": True})
    
    # 读取一个事件
    async def read_one():
        async for event in bus.stream_sse():
            return event
    
    event = await asyncio.wait_for(read_one(), timeout=1.0)
    assert "data:" in event
    assert "node_started" in event

@pytest.mark.asyncio
async def test_event_unsubscribe():
    """测试取消订阅（预留）"""
    bus = EventBus()
    
    # 当前实现没有取消订阅方法
    # 这里只是预留测试
    assert True

@pytest.mark.asyncio
async def test_event_priority():
    """测试事件优先级（预留）"""
    bus = EventBus()
    
    # 当前实现没有优先级
    # 这里只是预留测试
    assert True

@pytest.mark.asyncio
async def test_event_filter():
    """测试事件过滤（预留）"""
    bus = EventBus()
    
    # 当前实现没有事件过滤
    # 这里只是预留测试
    assert True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
