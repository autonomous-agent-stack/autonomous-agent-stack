"""Message Bus - OpenSage 架构通信核心"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class MessageType(Enum):
    """消息类型枚举"""
    TASK = "task"
    RESULT = "result"
    ERROR = "error"
    CONTROL = "control"
    HEARTBEAT = "heartbeat"
    SHUTDOWN = "shutdown"


@dataclass
class Message:
    """消息数据结构
    
    遵循 OpenSage 消息协议
    """
    type: MessageType
    sender: str
    receiver: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = field(default_factory=lambda: f"msg_{datetime.now().timestamp()}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
        }


class MessageBus:
    """消息总线
    
    实现 OpenSage 异步消息传递机制
    """
    
    def __init__(self):
        self._subscribers: Dict[str, Set[Callable]] = defaultdict(set)
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
    async def start(self):
        """启动消息总线"""
        if self._running:
            return
            
        self._running = True
        self._tasks.append(asyncio.create_task(self._process_messages()))
        
    async def stop(self):
        """停止消息总线"""
        self._running = False
        
        # 发送关闭消息
        await self.publish(Message(
            type=MessageType.SHUTDOWN,
            sender="system",
            receiver="all",
            payload={"reason": "Bus shutting down"}
        ))
        
        # 等待所有任务完成
        for task in self._tasks:
            task.cancel()
            
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
    async def publish(self, message: Message):
        """发布消息"""
        await self._message_queue.put(message)
        
    async def subscribe(
        self,
        topic: str,
        handler: Callable[[Message], None]
    ):
        """订阅主题
        
        Args:
            topic: 订阅主题（如 "task.*", "result.agent_1"）
            handler: 消息处理函数
        """
        self._subscribers[topic].add(handler)
        
    async def unsubscribe(
        self,
        topic: str,
        handler: Callable[[Message], None]
    ):
        """取消订阅"""
        self._subscribers[topic].discard(handler)
        
    async def _process_messages(self):
        """处理消息循环"""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )
                
                # 分发消息给订阅者
                await self._dispatch(message)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # 记录错误但继续运行
                print(f"[MessageBus] Error processing message: {e}")
                
    async def _dispatch(self, message: Message):
        """分发消息给订阅者"""
        # 精确匹配
        if message.receiver in self._subscribers:
            for handler in self._subscribers[message.receiver]:
                try:
                    await handler(message)
                except Exception as e:
                    print(f"[MessageBus] Handler error: {e}")
                    
        # 通配符匹配
        for topic, handlers in self._subscribers.items():
            if "*" in topic:
                # 简单通配符匹配
                prefix = topic.replace("*", "")
                if message.receiver.startswith(prefix):
                    for handler in handlers:
                        try:
                            await handler(message)
                        except Exception as e:
                            print(f"[MessageBus] Handler error: {e}")
                            
        # 广播给 "all"
        if "all" in self._subscribers:
            for handler in self._subscribers["all"]:
                try:
                    await handler(message)
                except Exception as e:
                    print(f"[MessageBus] Handler error: {e}")
