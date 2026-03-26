import asyncio
import json
from typing import Dict, Any, List, Callable
from datetime import datetime

class EventBus:
    """系统事件总线"""
    
    def __init__(self, max_queue_size: int = 1000):
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_types = [
            "node_started", "node_completed", "node_failed",
            "tool_generated", "tool_executed",
            "session_created", "session_cancelled",
            "error_occurred", "snapshot_saved", "rollback_triggered"
        ]
    
    async def publish(self, event_type: str, data: Dict[str, Any]):
        """发布事件"""
        if event_type not in self.event_types:
            raise ValueError(f"未知事件类型: {event_type}")
        
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        await self.queue.put(event)
        
        # 通知订阅者
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                maybe_coro = callback(event)
                if asyncio.iscoroutine(maybe_coro):
                    await maybe_coro

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        # 允许通过订阅注册扩展事件类型。
        if event_type not in self.event_types:
            self.event_types.append(event_type)
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    async def stream_sse(self):
        """SSE流式推送"""
        while True:
            event = await self.queue.get()
            yield f"data: {json.dumps(event)}\n\n"

# 测试
if __name__ == "__main__":
    async def test_event_bus():
        bus = EventBus()
        
        # 订阅事件
        async def on_node_started(event):
            print(f"收到事件: {event}")
        
        bus.subscribe("node_started", on_node_started)
        
        # 发布事件
        await bus.publish("node_started", {"node_id": "planner"})
        print("✅ Event Bus测试通过")
    
    asyncio.run(test_event_bus())
