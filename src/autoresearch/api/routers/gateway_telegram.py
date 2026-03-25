"""
Telegram 文本消息网关

核心功能：
- 文本消息、命令解析和处理
- chat_id -> session 映射与复用
- 重复消息去重
- 错误处理和回复
- 消息到 OpenClaw session/event 的映射
- 结果回写

设计原则：
- 只处理文本和命令，不涉及媒体、按钮、文件
- 薄层封装，不碰 OpenClaw 核心调度
- 保持可追踪的结构化日志
"""

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any, Set
from pathlib import Path


# ============================================
# 枚举类型定义
# ============================================

class MessageType(Enum):
    """消息类型枚举"""
    TEXT = "text"
    COMMAND = "command"
    UNKNOWN = "unknown"


class MessageStatus(Enum):
    """消息处理状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorType(Enum):
    """错误类型枚举"""
    PARSE_ERROR = "parse_error"
    DUPLICATE = "duplicate_message"
    SESSION_ERROR = "session_error"
    INVALID_COMMAND = "invalid_command"
    UNKNOWN_ERROR = "unknown_error"


# ============================================
# 数据结构定义
# ============================================

@dataclass
class TelegramCommand:
    """Telegram 命令对象"""
    command: str  # 命令名称（如 /start, /help）
    args: str = ""  # 命令参数
    raw_text: str = ""  # 原始文本
    chat_id: int = 0
    user_id: int = 0
    username: Optional[str] = None
    message_id: int = 0
    timestamp: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_telegram_update(cls, update: Dict[str, Any]) -> Optional["TelegramCommand"]:
        """从 Telegram Update 对象创建命令对象

        Args:
            update: Telegram webhook update payload

        Returns:
            TelegramCommand 对象或 None（如果不是命令）
        """
        try:
            message = update.get("message", {})
            text = message.get("text", "")

            # 检查是否是命令（以 / 开头）
            if not text.startswith("/"):
                return None

            # 解析命令和参数
            parts = text.split(maxsplit=1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""

            # 解析 bot 用户名（如果有 @username 后缀）
            if "@" in command:
                command = command.split("@")[0]

            return cls(
                command=command,
                args=args,
                raw_text=text,
                chat_id=message.get("chat", {}).get("id", 0),
                user_id=message.get("from", {}).get("id", 0),
                username=message.get("from", {}).get("username"),
                message_id=message.get("message_id", 0),
                timestamp=int(time.time())
            )
        except Exception:
            return None


@dataclass
class TelegramMessage:
    """Telegram 文本消息对象"""
    text: str  # 消息文本
    chat_id: int  # 聊天ID
    user_id: int  # 用户ID
    username: Optional[str] = None  # 用户名
    message_id: int = 0  # 消息ID
    timestamp: int = 0  # 时间戳
    message_type: MessageType = MessageType.TEXT  # 消息类型
    is_bot: bool = False  # 是否机器人消息

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "text": self.text,
            "chat_id": self.chat_id,
            "user_id": self.user_id,
            "username": self.username,
            "message_id": self.message_id,
            "timestamp": self.timestamp,
            "message_type": self.message_type.value,
            "is_bot": self.is_bot
        }

    @classmethod
    def from_telegram_update(cls, update: Dict[str, Any]) -> Optional["TelegramMessage"]:
        """从 Telegram Update 对象创建消息对象

        Args:
            update: Telegram webhook update payload

        Returns:
            TelegramMessage 对象或 None（如果没有文本内容）
        """
        try:
            message = update.get("message", {})
            text = message.get("text", "")

            if not text:
                return None

            return cls(
                text=text,
                chat_id=message.get("chat", {}).get("id", 0),
                user_id=message.get("from", {}).get("id", 0),
                username=message.get("from", {}).get("username"),
                message_id=message.get("message_id", 0),
                timestamp=int(time.time()),
                message_type=MessageType.COMMAND if text.startswith("/") else MessageType.TEXT,
                is_bot=message.get("from", {}).get("is_bot", False)
            )
        except Exception:
            return None

    def get_content_hash(self) -> str:
        """获取消息内容的哈希值（用于去重）"""
        content = f"{self.chat_id}:{self.text}:{self.user_id}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class SessionContext:
    """会话上下文

    维护 chat_id 与 OpenClaw session 的映射关系
    """
    chat_id: int  # Telegram chat_id
    session_id: str  # OpenClaw session_id
    user_id: int  # 用户ID
    username: Optional[str]
    created_at: int
    last_active: int
    message_count: int  # 该会话的消息计数

    def __init__(
        self,
        chat_id: int,
        session_id: str,
        user_id: int,
        username: Optional[str] = None,
        created_at: Optional[int] = None,
        last_active: Optional[int] = None,
        message_count: int = 0
    ):
        self.chat_id = chat_id
        self.session_id = session_id
        self.user_id = user_id
        self.username = username
        self.created_at = created_at if created_at is not None else int(time.time())
        self.last_active = last_active if last_active is not None else int(time.time())
        self.message_count = message_count

    def update_activity(self):
        """更新最后活跃时间"""
        self.last_active = int(time.time())
        self.message_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def is_expired(self, ttl_seconds: int = 3600) -> bool:
        """检查会话是否过期

        Args:
            ttl_seconds: 会话超时时间（秒），默认1小时

        Returns:
            是否过期
        """
        return (int(time.time()) - self.last_active) > ttl_seconds


@dataclass
class MessageProcessingResult:
    """消息处理结果"""
    success: bool
    session_id: Optional[str] = None
    error: Optional[str] = None
    error_type: Optional[ErrorType] = None
    response_text: Optional[str] = None
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "session_id": self.session_id,
            "error": self.error,
            "error_type": self.error_type.value if self.error_type else None,
            "response_text": self.response_text,
            "processing_time_ms": self.processing_time_ms,
            "metadata": self.metadata
        }


# ============================================
# 结构化日志记录器
# ============================================

class TelegramLogger:
    """Telegram 网关专用日志记录器"""

    def __init__(self, name: str = "TelegramGateway"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def _log(self, level: str, data: Dict[str, Any]) -> None:
        """记录结构化日志"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.upper(),
            "node": "telegram_gateway",
            **data
        }
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        log_func(json.dumps(log_entry, ensure_ascii=False))

    def info(self, **data) -> None:
        self._log("info", data)

    def warning(self, **data) -> None:
        self._log("warning", data)

    def error(self, **data) -> None:
        self._log("error", data)

    def debug(self, **data) -> None:
        self._log("debug", data)

    def log_message_received(
        self,
        message: TelegramMessage,
        is_duplicate: bool = False
    ) -> None:
        """记录接收到的消息

        Args:
            message: 消息对象
            is_duplicate: 是否重复消息
        """
        self.info(
            action="message_received",
            message_id=message.message_id,
            chat_id=message.chat_id,
            user_id=message.user_id,
            message_type=message.message_type.value,
            text_preview=message.text[:100] if message.text else "",
            text_length=len(message.text),
            is_duplicate=is_duplicate,
            username=message.username
        )

    def log_command_received(
        self,
        command: TelegramCommand
    ) -> None:
        """记录接收到的命令

        Args:
            command: 命令对象
        """
        self.info(
            action="command_received",
            command=command.command,
            args=command.args[:100] if command.args else "",
            chat_id=command.chat_id,
            user_id=command.user_id,
            message_id=command.message_id,
            username=command.username
        )

    def log_session_created(
        self,
        chat_id: int,
        session_id: str,
        user_id: int
    ) -> None:
        """记录会话创建

        Args:
            chat_id: Telegram chat_id
            session_id: OpenClaw session_id
            user_id: 用户ID
        """
        self.info(
            action="session_created",
            chat_id=chat_id,
            session_id=session_id,
            user_id=user_id
        )

    def log_session_reused(
        self,
        chat_id: int,
        session_id: str,
        message_count: int
    ) -> None:
        """记录会话复用

        Args:
            chat_id: Telegram chat_id
            session_id: OpenClaw session_id
            message_count: 该会话的消息计数
        """
        self.info(
            action="session_reused",
            chat_id=chat_id,
            session_id=session_id,
            message_count=message_count
        )

    def log_message_processed(
        self,
        result: MessageProcessingResult,
        message: TelegramMessage
    ) -> None:
        """记录消息处理完成

        Args:
            result: 处理结果
            message: 消息对象
        """
        self.info(
            action="message_processed",
            message_id=message.message_id,
            chat_id=message.chat_id,
            success=result.success,
            session_id=result.session_id,
            error=result.error,
            error_type=result.error_type.value if result.error_type else None,
            processing_time_ms=result.processing_time_ms
        )

    def log_error(
        self,
        error_type: ErrorType,
        error_message: str,
        **kwargs
    ) -> None:
        """记录错误

        Args:
            error_type: 错误类型
            error_message: 错误消息
            **kwargs: 其他上下文信息
        """
        self.error(
            action="error",
            error_type=error_type.value,
            error_message=error_message,
            **kwargs
        )


# ============================================
# Telegram 网关实现
# ============================================

class TelegramGateway:
    """Telegram 文本消息网关

    负责：
    - 接收和解析 Telegram webhook 文本消息
    - 维护 chat_id -> session 映射
    - 重复消息检测
    - 消息到 OpenClaw event 的转换
    - 处理结果回写
    """

    def __init__(
        self,
        session_ttl_seconds: int = 3600,
        duplicate_window_seconds: int = 5
    ):
        """初始化 Telegram 网关

        Args:
            session_ttl_seconds: 会话超时时间（秒），默认1小时
            duplicate_window_seconds: 重复消息检测窗口（秒），默认5秒
        """
        self.logger = TelegramLogger()

        # 会话存储：chat_id -> SessionContext
        self._sessions: Dict[int, SessionContext] = {}

        # 重复消息缓存：content_hash -> timestamp
        self._duplicate_cache: Dict[str, int] = {}

        # 配置
        self._session_ttl_seconds = session_ttl_seconds
        self._duplicate_window_seconds = duplicate_window_seconds

        self.logger.info(
            action="gateway_initialized",
            session_ttl_seconds=session_ttl_seconds,
            duplicate_window_seconds=duplicate_window_seconds
        )

    def handle_webhook_update(
        self,
        update: Dict[str, Any]
    ) -> MessageProcessingResult:
        """处理 Telegram webhook 更新

        Args:
            update: Telegram webhook update payload

        Returns:
            MessageProcessingResult 对象
        """
        start_time = time.time()

        try:
            # 解析消息
            message = TelegramMessage.from_telegram_update(update)

            if not message:
                # 可能是命令消息
                command = TelegramCommand.from_telegram_update(update)

                if command:
                    return self._handle_command(command, start_time)
                else:
                    # 无有效内容
                    return MessageProcessingResult(
                        success=False,
                        error="No text or command found in update",
                        error_type=ErrorType.PARSE_ERROR,
                        processing_time_ms=int((time.time() - start_time) * 1000)
                    )

            # 检查重复消息
            content_hash = message.get_content_hash()
            if self._is_duplicate(content_hash):
                self.logger.log_message_received(message, is_duplicate=True)

                return MessageProcessingResult(
                    success=False,
                    error="Duplicate message detected",
                    error_type=ErrorType.DUPLICATE,
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    metadata={"content_hash": content_hash}
                )

            # 记录接收到的消息
            self.logger.log_message_received(message, is_duplicate=False)

            # 缓存消息哈希
            self._cache_message_hash(content_hash)

            # 如果是命令，特殊处理
            if message.message_type == MessageType.COMMAND:
                command = TelegramCommand.from_telegram_update(update)
                if command:
                    return self._handle_command(command, start_time)

            # 获取或创建会话
            session = self._get_or_create_session(message)

            # 转换为 OpenClaw event 格式
            event = self._message_to_event(message, session.session_id)

            # 这里应该将 event 传递给 OpenClaw 核心调度器
            # 由于任务约束不碰核心调度，这里只做转换
            result = MessageProcessingResult(
                success=True,
                session_id=session.session_id,
                response_text=f"Message processed. Session: {session.session_id}",
                processing_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "event": event,
                    "message": message.to_dict(),
                    "session": session.to_dict()
                }
            )

            self.logger.log_message_processed(result, message)

            return result

        except Exception as e:
            self.logger.log_error(
                ErrorType.UNKNOWN_ERROR,
                str(e),
                update_preview=str(update)[:200]
            )

            return MessageProcessingResult(
                success=False,
                error=str(e),
                error_type=ErrorType.UNKNOWN_ERROR,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

    def _handle_command(
        self,
        command: TelegramCommand,
        start_time: float
    ) -> MessageProcessingResult:
        """处理命令

        Args:
            command: 命令对象
            start_time: 开始时间戳

        Returns:
            MessageProcessingResult 对象
        """
        self.logger.log_command_received(command)

        try:
            # 获取或创建会话
            session = self._get_or_create_session_from_command(command)

            # 验证命令
            if not self._is_valid_command(command.command):
                return MessageProcessingResult(
                    success=False,
                    error=f"Unknown command: {command.command}",
                    error_type=ErrorType.INVALID_COMMAND,
                    session_id=session.session_id,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                )

            # 转换为 OpenClaw event 格式
            event = self._command_to_event(command, session.session_id)

            # 处理命令
            response = self._process_command(command)

            result = MessageProcessingResult(
                success=True,
                session_id=session.session_id,
                response_text=response,
                processing_time_ms=int((time.time() - start_time) * 1000),
                metadata={
                    "event": event,
                    "command": command.to_dict(),
                    "session": session.to_dict()
                }
            )

            self.logger.log_message_processed(
                result,
                TelegramMessage(
                    text=command.raw_text,
                    chat_id=command.chat_id,
                    user_id=command.user_id,
                    username=command.username,
                    message_id=command.message_id,
                    timestamp=command.timestamp,
                    message_type=MessageType.COMMAND
                )
            )

            return result

        except Exception as e:
            self.logger.log_error(
                ErrorType.UNKNOWN_ERROR,
                str(e),
                command=command.command,
                chat_id=command.chat_id
            )

            return MessageProcessingResult(
                success=False,
                error=str(e),
                error_type=ErrorType.UNKNOWN_ERROR,
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

    def _get_or_create_session(
        self,
        message: TelegramMessage
    ) -> SessionContext:
        """获取或创建会话

        Args:
            message: 消息对象

        Returns:
            SessionContext 对象
        """
        chat_id = message.chat_id

        # 检查是否已有会话
        if chat_id in self._sessions:
            session = self._sessions[chat_id]

            # 检查会话是否过期
            if session.is_expired(self._session_ttl_seconds):
                # 创建新会话
                self._sessions.pop(chat_id)
                return self._create_new_session(message)

            # 复用现有会话
            session.update_activity()
            self.logger.log_session_reused(
                chat_id,
                session.session_id,
                session.message_count
            )
            return session

        # 创建新会话
        return self._create_new_session(message)

    def _get_or_create_session_from_command(
        self,
        command: TelegramCommand
    ) -> SessionContext:
        """从命令获取或创建会话

        Args:
            command: 命令对象

        Returns:
            SessionContext 对象
        """
        chat_id = command.chat_id

        # 检查是否已有会话
        if chat_id in self._sessions:
            session = self._sessions[chat_id]

            # /start 和 /reset 命令创建新会话
            if command.command in ["/start", "/reset"]:
                self._sessions.pop(chat_id)
                return self._create_new_session_from_command(command)

            # 检查会话是否过期
            if session.is_expired(self._session_ttl_seconds):
                self._sessions.pop(chat_id)
                return self._create_new_session_from_command(command)

            # 复用现有会话
            session.update_activity()
            self.logger.log_session_reused(
                chat_id,
                session.session_id,
                session.message_count
            )
            return session

        # 创建新会话
        return self._create_new_session_from_command(command)

    def _create_new_session(
        self,
        message: TelegramMessage
    ) -> SessionContext:
        """创建新会话

        Args:
            message: 消息对象

        Returns:
            SessionContext 对象
        """
        session_id = f"tg_{message.chat_id}_{int(time.time())}"

        session = SessionContext(
            chat_id=message.chat_id,
            session_id=session_id,
            user_id=message.user_id,
            username=message.username
        )

        self._sessions[message.chat_id] = session

        # 递增消息计数
        session.update_activity()

        self.logger.log_session_created(
            message.chat_id,
            session_id,
            message.user_id
        )

        return session

    def _create_new_session_from_command(
        self,
        command: TelegramCommand
    ) -> SessionContext:
        """从命令创建新会话

        Args:
            command: 命令对象

        Returns:
            SessionContext 对象
        """
        session_id = f"tg_{command.chat_id}_{int(time.time())}"

        session = SessionContext(
            chat_id=command.chat_id,
            session_id=session_id,
            user_id=command.user_id,
            username=command.username
        )

        self._sessions[command.chat_id] = session

        # 递增消息计数
        session.update_activity()

        self.logger.log_session_created(
            command.chat_id,
            session_id,
            command.user_id
        )

        return session

    def _is_duplicate(self, content_hash: str) -> bool:
        """检查是否重复消息

        Args:
            content_hash: 内容哈希

        Returns:
            是否重复
        """
        if content_hash not in self._duplicate_cache:
            return False

        # 检查是否在时间窗口内
        cached_time = self._duplicate_cache[content_hash]
        return (int(time.time()) - cached_time) < self._duplicate_window_seconds

    def _cache_message_hash(self, content_hash: str):
        """缓存消息哈希

        Args:
            content_hash: 内容哈希
        """
        self._duplicate_cache[content_hash] = int(time.time())

        # 定期清理过期缓存
        self._cleanup_duplicate_cache()

    def _cleanup_duplicate_cache(self):
        """清理过期的重复消息缓存"""
        current_time = int(time.time())
        expired_hashes = [
            h for h, t in self._duplicate_cache.items()
            if (current_time - t) > self._duplicate_window_seconds
        ]

        for h in expired_hashes:
            del self._duplicate_cache[h]

    def _is_valid_command(self, command: str) -> bool:
        """验证命令是否有效

        Args:
            command: 命令字符串

        Returns:
            是否有效
        """
        valid_commands = [
            "/start",
            "/help",
            "/reset",
            "/status",
            "/about"
        ]

        return command in valid_commands

    def _process_command(self, command: TelegramCommand) -> str:
        """处理命令并返回响应文本

        Args:
            command: 命令对象

        Returns:
            响应文本
        """
        # 获取当前会话的消息计数
        session = self._sessions.get(command.chat_id)
        message_count = session.message_count if session else 0

        command_handlers = {
            "/start": "Welcome! I'm ready to help. Send me a message to get started.",
            "/help": "Available commands: /start, /help, /reset, /status, /about",
            "/reset": "Session reset. Starting a new conversation.",
            "/status": f"Session active. Messages processed in this session: {message_count}",
            "/about": "I'm an AI assistant powered by OpenClaw. Send me text messages to interact!"
        }

        return command_handlers.get(
            command.command,
            f"Unknown command: {command.command}. Use /help for available commands."
        )

    def _message_to_event(
        self,
        message: TelegramMessage,
        session_id: str
    ) -> Dict[str, Any]:
        """将消息转换为 OpenClaw event 格式

        Args:
            message: 消息对象
            session_id: 会话ID

        Returns:
            OpenClaw event 字典
        """
        return {
            "type": "message",
            "channel": "telegram",
            "session_id": session_id,
            "chat_id": message.chat_id,
            "user_id": message.user_id,
            "username": message.username,
            "message_id": message.message_id,
            "timestamp": message.timestamp,
            "content": {
                "text": message.text,
                "message_type": message.message_type.value
            },
            "metadata": {
                "is_bot": message.is_bot
            }
        }

    def _command_to_event(
        self,
        command: TelegramCommand,
        session_id: str
    ) -> Dict[str, Any]:
        """将命令转换为 OpenClaw event 格式

        Args:
            command: 命令对象
            session_id: 会话ID

        Returns:
            OpenClaw event 字典
        """
        return {
            "type": "command",
            "channel": "telegram",
            "session_id": session_id,
            "chat_id": command.chat_id,
            "user_id": command.user_id,
            "username": command.username,
            "message_id": command.message_id,
            "timestamp": command.timestamp,
            "content": {
                "command": command.command,
                "args": command.args,
                "raw_text": command.raw_text
            }
        }

    def get_session(self, chat_id: int) -> Optional[SessionContext]:
        """获取指定聊天ID的会话

        Args:
            chat_id: 聊天ID

        Returns:
            SessionContext 对象或 None
        """
        return self._sessions.get(chat_id)

    def get_all_sessions(self) -> Dict[int, SessionContext]:
        """获取所有会话

        Returns:
            会话字典
        """
        return self._sessions.copy()

    def cleanup_expired_sessions(self) -> int:
        """清理过期的会话

        Returns:
            清理的会话数量
        """
        expired_chats = [
            chat_id
            for chat_id, session in self._sessions.items()
            if session.is_expired(self._session_ttl_seconds)
        ]

        for chat_id in expired_chats:
            del self._sessions[chat_id]

        if expired_chats:
            self.logger.info(
                action="expired_sessions_cleaned",
                count=len(expired_chats),
                expired_chat_ids=expired_chats
            )

        return len(expired_chats)

    def get_stats(self) -> Dict[str, Any]:
        """获取网关统计信息

        Returns:
            统计信息字典
        """
        active_sessions = len(self._sessions)
        total_messages = sum(s.message_count for s in self._sessions.values())
        cached_hashes = len(self._duplicate_cache)

        return {
            "active_sessions": active_sessions,
            "total_messages": total_messages,
            "cached_duplicate_hashes": cached_hashes,
            "session_ttl_seconds": self._session_ttl_seconds,
            "duplicate_window_seconds": self._duplicate_window_seconds
        }


# ============================================
# 测试辅助函数
# ============================================

def create_test_update(
    text: str,
    chat_id: int = 123456789,
    user_id: int = 987654321,
    username: str = "testuser",
    message_id: int = 1
) -> Dict[str, Any]:
    """创建测试用的 Telegram update 对象

    Args:
        text: 消息文本
        chat_id: 聊天ID
        user_id: 用户ID
        username: 用户名
        message_id: 消息ID

    Returns:
        Telegram update 字典
    """
    return {
        "update_id": message_id,
        "message": {
            "message_id": message_id,
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test",
                "username": username
            },
            "chat": {
                "id": chat_id,
                "first_name": "Test",
                "username": username,
                "type": "private"
            },
            "date": int(time.time()),
            "text": text
        }
    }


# ============================================
# 命令行接口
# ============================================

def main():
    """命令行测试接口"""
    import argparse

    parser = argparse.ArgumentParser(description="Telegram Gateway Test")
    parser.add_argument("--test", action="store_true", help="Run tests")
    parser.add_argument("--stats", action="store_true", help="Show stats")

    args = parser.parse_args()

    gateway = TelegramGateway()

    if args.test:
        print("\n" + "="*60)
        print("运行 Telegram Gateway 测试")
        print("="*60)

        # 测试文本消息
        update = create_test_update("Hello, world!")
        result = gateway.handle_webhook_update(update)
        print(f"\n文本消息测试结果:")
        print(f"  成功: {result.success}")
        print(f"  Session ID: {result.session_id}")
        print(f"  响应: {result.response_text}")

        # 测试命令
        update = create_test_update("/help")
        result = gateway.handle_webhook_update(update)
        print(f"\n命令测试结果:")
        print(f"  成功: {result.success}")
        print(f"  响应: {result.response_text}")

        # 测试重复消息
        update = create_test_update("Hello, world!")
        result = gateway.handle_webhook_update(update)
        print(f"\n重复消息测试结果:")
        print(f"  成功: {result.success}")
        print(f"  错误: {result.error}")

    if args.stats:
        stats = gateway.get_stats()
        print(f"\n网关统计信息:")
        print(f"  活跃会话: {stats['active_sessions']}")
        print(f"  总消息数: {stats['total_messages']}")
        print(f"  缓存的哈希: {stats['cached_duplicate_hashes']}")


if __name__ == "__main__":
    main()
