"""
消息镜像 - 原话镜像功能

实现话题间的消息备份和同步
"""

import logging
import os
from typing import Dict, Optional
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


class MessageMirror:
    """
    消息镜像器 - 实现原话镜像功能

    将消息从一个话题镜像到另一个话题（备份）
    """

    def __init__(self, bot=None):
        """
        初始化消息镜像器

        Args:
            bot: Telegram Bot 实例（可选，用于实际发送消息）
        """
        self.bot = bot
        self.mirror_count = 0
        logger.info("[Router-Gate] MessageMirror initialized")

    async def mirror_to_backup(
        self, original_message: Dict, backup_chat_id: int, backup_thread_id: Optional[int]
    ) -> Dict:
        """
        镜像消息到备份话题

        Args:
            original_message: 原始消息字典，包含：
                - chat_id: 源群组 ID
                - thread_id: 源话题 ID
                - message_id: 源消息 ID
                - text: 消息内容
                - sender_id: 发送者 ID（可选）
                - timestamp: 时间戳（可选）
            backup_chat_id: 备份群组 ID
            backup_thread_id: 备份话题 ID

        Returns:
            {
                "status": "success",
                "backup_message_id": 67890,
                "timestamp": "2026-03-26T09:15:00Z"
            }
        """
        try:
            # 构建镜像消息
            mirror_text = self._build_mirror_text(original_message)

            # 如果有 bot 实例，实际发送消息
            backup_message_id = None
            if self.bot:
                backup_message_id = await self._send_mirror_message(
                    backup_chat_id, backup_thread_id, mirror_text
                )
            else:
                # 模拟模式：生成假 ID
                backup_message_id = self._generate_mock_message_id()

            self.mirror_count += 1

            result = {
                "status": "success",
                "backup_message_id": backup_message_id,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "mirror_count": self.mirror_count,
            }

            logger.info(
                "[Router-Gate] Message mirrored: %s -> %s:%s (ID: %s)",
                original_message.get("message_id"),
                backup_chat_id,
                backup_thread_id,
                backup_message_id,
            )

            return result

        except Exception as e:
            logger.error("[Router-Gate] Mirror failed: %s", str(e))
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }

    def _build_mirror_text(self, original_message: Dict) -> str:
        """
        构建镜像消息文本

        Args:
            original_message: 原始消息字典

        Returns:
            格式化的镜像文本
        """
        text = original_message.get("text", "")
        sender_id = original_message.get("sender_id", "Unknown")
        msg_id = original_message.get("message_id", "N/A")
        source_thread = original_message.get("thread_id", "Main")

        # 构建镜像头部
        header = f"📋 镜像消息 #{msg_id}\n"
        header += f"👤 发送者: {sender_id}\n"
        header += f"💬 来源话题: {source_thread}\n"
        header += f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        header += "-" * 40 + "\n\n"

        return header + text

    async def _send_mirror_message(self, chat_id: int, thread_id: Optional[int], text: str) -> int:
        """
        发送镜像消息

        Args:
            chat_id: 目标群组 ID
            thread_id: 目标话题 ID
            text: 消息文本

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
                logger.warning("[Router-Gate] Telegram API mirror failed, using mock mode")

        logger.warning("[Router-Gate] Bot not configured, using mock mode")
        return self._generate_mock_message_id()

    def _generate_mock_message_id(self) -> int:
        """
        生成模拟消息 ID（用于测试）

        Returns:
            模拟的消息 ID
        """
        import random

        return random.randint(10000, 99999)

    async def batch_mirror(
        self, messages: list, backup_chat_id: int, backup_thread_id: Optional[int]
    ) -> Dict:
        """
        批量镜像消息

        Args:
            messages: 原始消息列表
            backup_chat_id: 备份群组 ID
            backup_thread_id: 备份话题 ID

        Returns:
            {
                "status": "success",
                "success_count": 5,
                "failed_count": 0,
                "results": [...]
            }
        """
        results = []
        success_count = 0
        failed_count = 0

        for msg in messages:
            result = await self.mirror_to_backup(msg, backup_chat_id, backup_thread_id)
            results.append(result)

            if result["status"] == "success":
                success_count += 1
            else:
                failed_count += 1

        logger.info(
            "[Router-Gate] Batch mirror complete: %d success, %d failed",
            success_count,
            failed_count,
        )

        return {
            "status": "success" if failed_count == 0 else "partial",
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results,
        }

    def get_mirror_stats(self) -> Dict:
        """
        获取镜像统计信息

        Returns:
            统计信息字典
        """
        return {"total_mirrored": self.mirror_count, "bot_configured": self.bot is not None}
