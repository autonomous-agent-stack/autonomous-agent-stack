"""
话题路由器 - 实现动态路由选择和消息分发
"""

import itertools
import logging
import os
from typing import ClassVar, Dict, Optional

import httpx
from .route_table import RouteTable
from .message_mirror import MessageMirror

logger = logging.getLogger(__name__)


class TopicRouter:
    """
    话题路由器 - 核心路由逻辑
    
    功能：
    1. 根据消息类型路由到指定话题
    2. 支持消息镜像到备份话题
    3. 动态路由选择
    """
    
    def __init__(self, bot=None, route_table: Optional[RouteTable] = None):
        """
        初始化路由器
        
        Args:
            bot: Telegram Bot 实例（可选）
            route_table: 路由表实例，如果为 None 则创建默认实例
        """
        self.bot = bot
        self.route_table = route_table or RouteTable()
        self.mirror = MessageMirror(bot=bot)
        
        self.route_count = 0
        logger.info("[Router-Gate] TopicRouter initialized")
    
    async def route_message(
        self,
        message_type: str,
        text: str,
        mirror: bool = False,
        sender_id: Optional[str] = None
    ) -> Dict:
        """
        路由消息到指定话题
        
        Args:
            message_type: 消息类型（intelligence/content/security）
            text: 消息内容
            mirror: 是否镜像到备份话题
            sender_id: 发送者 ID（可选）
            
        Returns:
            {
                "status": "success",
                "chat_id": -100xxx,
                "thread_id": 10,
                "message_id": 12345,
                "mirrored": true,
                "backup_message_id": 67890
            }
        """
        try:
            # 获取路由配置
            route = self.route_table.get_route(message_type)
            
            if not route:
                return {
                    "status": "error",
                    "error": f"No route found for message type: {message_type}",
                    "message_type": message_type
                }
            
            chat_id = route["chat_id"]
            thread_id = route.get("thread_id")
            
            logger.info(
                "[Router-Gate] Routing message to: %s -> %s:%s",
                message_type,
                chat_id,
                thread_id or "main"
            )
            
            # 发送消息
            message_id = await self._send_message(chat_id, thread_id, text)
            
            result = {
                "status": "success",
                "message_type": message_type,
                "chat_id": chat_id,
                "thread_id": thread_id,
                "message_id": message_id,
                "mirrored": False
            }
            
            # 如果需要镜像
            if mirror:
                backup_route = self.route_table.get_backup_route(message_type)
                
                if backup_route:
                    logger.info(
                        "[Router-Gate] Mirror enabled, backing up to: %s",
                        backup_route["thread_id"]
                    )
                    
                    # 构建原始消息字典
                    original_message = {
                        "chat_id": chat_id,
                        "thread_id": thread_id,
                        "message_id": message_id,
                        "text": text,
                        "sender_id": sender_id or "Unknown"
                    }
                    
                    # 执行镜像
                    mirror_result = await self.mirror.mirror_to_backup(
                        original_message,
                        backup_route["chat_id"],
                        backup_route["thread_id"]
                    )
                    
                    result["mirrored"] = True
                    result["backup_message_id"] = mirror_result.get("backup_message_id")
                    result["backup_thread_id"] = backup_route["thread_id"]
                else:
                    logger.warning("[Router-Gate] No backup route available for: %s", message_type)
            
            self.route_count += 1
            return result
            
        except Exception as e:
            logger.error("[Router-Gate] Route failed: %s", str(e))
            return {
                "status": "error",
                "error": str(e),
                "message_type": message_type
            }
    
    async def mirror_message(
        self,
        source_chat_id: int,
        source_thread_id: Optional[int],
        target_chat_id: int,
        target_thread_id: Optional[int],
        text: str
    ) -> Dict:
        """
        原话镜像功能 - 手动指定源和目标
        
        Args:
            source_chat_id: 源群组 ID
            source_thread_id: 源话题 ID
            target_chat_id: 目标群组 ID
            target_thread_id: 目标话题 ID
            text: 消息内容
            
        Returns:
            {
                "status": "success",
                "target_message_id": 12345
            }
        """
        try:
            logger.info(
                "[Router-Gate] Manual mirror: %s:%s -> %s:%s",
                source_chat_id,
                source_thread_id or "main",
                target_chat_id,
                target_thread_id or "main"
            )
            
            # 构建原始消息
            original_message = {
                "chat_id": source_chat_id,
                "thread_id": source_thread_id,
                "message_id": 0,  # 手动镜像没有原始消息 ID
                "text": text,
                "sender_id": "Manual"
            }
            
            # 执行镜像
            result = await self.mirror.mirror_to_backup(
                original_message,
                target_chat_id,
                target_thread_id
            )
            
            return result
            
        except Exception as e:
            logger.error("[Router-Gate] Manual mirror failed: %s", str(e))
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _send_message(
        self,
        chat_id: int,
        thread_id: Optional[int],
        text: str
    ) -> int:
        """
        发送消息到指定话题
        
        Args:
            chat_id: 群组 ID
            thread_id: 话题 ID（None 表示主群组）
            text: 消息内容
            
        Returns:
            发送的消息 ID
        """
        if self.bot is not None and hasattr(self.bot, "send_message"):
            message = await self.bot.send_message(
                chat_id=chat_id,
                message_thread_id=thread_id,
                text=text,
            )
            return int(getattr(message, "message_id", 0)) or self._generate_mock_message_id()

        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if token:
            endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
            payload: Dict[str, object] = {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": True,
            }
            if thread_id is not None:
                payload["message_thread_id"] = thread_id
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(endpoint, json=payload)
                    response.raise_for_status()
                data = response.json()
                if data.get("ok"):
                    result = data.get("result") or {}
                    return int(result.get("message_id", self._generate_mock_message_id()))
            except (httpx.HTTPError, ValueError):
                logger.warning("[Router-Gate] Telegram API send failed, fallback to mock mode")

        mock_id = self._generate_mock_message_id()
        logger.debug(
            "[Router-Gate] Mock sent to %s:%s -> message_id: %s",
            chat_id,
            thread_id or "main",
            mock_id
        )
        return mock_id

    _mock_id_counter: ClassVar[itertools.count] = itertools.count(1000)

    @classmethod
    def _generate_mock_message_id(cls) -> int:
        return next(cls._mock_id_counter)
    
    async def broadcast_message(
        self,
        text: str,
        message_types: list = None
    ) -> Dict:
        """
        广播消息到多个话题
        
        Args:
            text: 消息内容
            message_types: 消息类型列表，如果为 None 则广播到所有启用的路由
            
        Returns:
            {
                "status": "success",
                "sent_count": 3,
                "results": [...]
            }
        """
        if message_types is None:
            # 广播到所有启用的路由
            message_types = [
                route["type"]
                for route in self.route_table.list_routes()
                if route.get("enabled", True)
            ]
        
        results = []
        sent_count = 0
        
        for msg_type in message_types:
            result = await self.route_message(msg_type, text, mirror=False)
            results.append(result)
            
            if result["status"] == "success":
                sent_count += 1
        
        logger.info(
            "[Router-Gate] Broadcast complete: %d/%d sent",
            sent_count,
            len(message_types)
        )
        
        return {
            "status": "success",
            "sent_count": sent_count,
            "total_count": len(message_types),
            "results": results
        }
    
    def get_router_stats(self) -> Dict:
        """
        获取路由器统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "total_routed": self.route_count,
            "available_routes": len(self.route_table.list_routes()),
            "mirror_stats": self.mirror.get_mirror_stats()
        }
    
    def add_route(self, message_type: str, chat_id: int, thread_id: Optional[int], 
                  description: str = "") -> bool:
        """
        添加新路由（代理方法）
        
        Args:
            message_type: 消息类型标识
            chat_id: 目标群组 ID
            thread_id: 话题 ID
            description: 路由描述
            
        Returns:
            是否添加成功
        """
        return self.route_table.add_route(message_type, chat_id, thread_id, description)
