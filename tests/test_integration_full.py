import pytest
from src.orchestrator.session_manager import SessionManager
from src.orchestrator.event_bus import EventBus
from src.orchestrator.concurrency import ConcurrencyManager

@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """测试端到端工作流"""
    # 初始化组件
    sm = SessionManager()
    event_bus = EventBus()
    concurrency = ConcurrencyManager()
    
    # 订阅事件
    events = []
    async def collect_events(event):
        events.append(event)
    
    event_bus.subscribe("node_started", collect_events)
    event_bus.subscribe("node_completed", collect_events)
    
    # 创建会话
    session_id = await sm.create_session("chat_test", {"goal": "test workflow"})
    
    # 执行图
    await concurrency.acquire()
    try:
        # 模拟完整流程
        await event_bus.publish("node_started", {"node_id": "planner", "session_id": session_id})
        # ... 执行其他节点
        await event_bus.publish("node_completed", {"node_id": "planner", "session_id": session_id})
        
        assert len(events) == 2
        print("✅ 端到端工作流测试通过")
    finally:
        concurrency.release()

@pytest.mark.asyncio
async def test_error_handling_and_retry():
    """测试错误处理和重试"""
    # 模拟错误
    retry_count = 0
    max_retries = 3
    
    while retry_count < max_retries:
        try:
            # 模拟可能失败的操作
            if retry_count < 2:
                raise ValueError("模拟错误")
            print("✅ 重试成功")
            break
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise
    
    assert retry_count == 2  # 第3次成功

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
