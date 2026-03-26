"""
Event Bus - Redis Pub/Sub 全局事件总线

支持跨多台 M1 宿主机的 Agent 状态同步
"""

import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """事件对象"""
    event_type: str
    payload: Dict[str, Any]
    source: str
    timestamp: float


class EventBus:
    """Redis Pub/Sub 事件总线"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.subscribers: Dict[str, Callable] = {}
        self._running = False

    async def connect(self):
        """连接 Redis"""
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            await self.pubsub.subscribe("agent_events")
            logger.info(f"[EventBus] ✅ Redis 连接成功: {self.redis_url}")
        except Exception as e:
            logger.error(f"[EventBus] ❌ Redis 连接失败: {e}")
            raise

    async def disconnect(self):
        """断开连接"""
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
        logger.info("[EventBus] 🔌 已断开连接")

    async def publish(self, event_type: str, payload: Dict[str, Any], source: str = "unknown"):
        """发布事件"""
        if not self.redis_client:
            raise RuntimeError("EventBus 未连接")

        event = {
            "event_type": event_type,
            "payload": payload,
            "source": source,
            "timestamp": asyncio.get_event_loop().time()
        }

        try:
            await self.redis_client.publish("agent_events", json.dumps(event))
            logger.debug(f"[EventBus] 📡 事件已发布: {event_type}")
        except Exception as e:
            logger.error(f"[EventBus] ❌ 发布失败: {e}")
            raise

    async def subscribe(self, event_type: str, callback: Callable):
        """订阅事件"""
        self.subscribers[event_type] = callback
        logger.info(f"[EventBus] 📥 已订阅: {event_type}")

    async def listen(self):
        """监听事件流"""
        if not self.pubsub:
            raise RuntimeError("EventBus 未连接")

        self._running = True
        logger.info("[EventBus] 👂 开始监听事件流...")

        try:
            async for message in self.pubsub.listen():
                if not self._running:
                    break

                if message["type"] == "message":
                    await self._handle_message(message)
        except asyncio.CancelledError:
            logger.info("[EventBus] ⏹️ 监听已停止")
        except Exception as e:
            logger.error(f"[EventBus] ❌ 监听错误: {e}")

    async def _handle_message(self, message: Dict):
        """处理消息"""
        try:
            event_data = json.loads(message["data"])
            event_type = event_data.get("event_type")

            if event_type in self.subscribers:
                callback = self.subscribers[event_type]
                await callback(event_data)
                logger.debug(f"[EventBus] ✅ 事件已处理: {event_type}")
        except Exception as e:
            logger.error(f"[EventBus] ❌ 消息处理失败: {e}")

    def stop(self):
        """停止监听"""
        self._running = False


# 单例实例
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取事件总线单例"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
