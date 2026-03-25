"""
测试 Telegram 网关功能

测试覆盖：
- 文本消息接收和解析
- 命令处理
- 会话创建和复用
- 重复消息检测
- 会话过期和清理
- 消息到 OpenClaw event 的转换
- 错误处理
"""

import pytest
import time
from src.autoresearch.api.routers.gateway_telegram import (
    TelegramGateway,
    TelegramMessage,
    TelegramCommand,
    SessionContext,
    MessageProcessingResult,
    MessageType,
    ErrorType,
    create_test_update
)


# ============================================
# 测试数据构造辅助函数
# ============================================

def make_text_update(text: str, chat_id: int = 123, user_id: int = 456, message_id: int = 1) -> dict:
    """创建文本消息 update"""
    return create_test_update(text, chat_id, user_id, "testuser", message_id)


def make_command_update(command: str, chat_id: int = 123, user_id: int = 456, message_id: int = 1) -> dict:
    """创建命令消息 update"""
    return create_test_update(command, chat_id, user_id, "testuser", message_id)


# ============================================
# 测试 TelegramMessage
# ============================================

class TestTelegramMessage:
    """测试 TelegramMessage 类"""

    def test_from_telegram_update_text(self):
        """测试从 update 创建文本消息"""
        update = make_text_update("Hello, world!")

        message = TelegramMessage.from_telegram_update(update)

        assert message is not None
        assert message.text == "Hello, world!"
        assert message.chat_id == 123
        assert message.user_id == 456
        assert message.username == "testuser"
        assert message.message_id == 1
        assert message.message_type == MessageType.TEXT
        assert message.is_bot is False

    def test_from_telegram_update_command(self):
        """测试从 update 创建命令消息"""
        update = make_command_update("/help")

        message = TelegramMessage.from_telegram_update(update)

        assert message is not None
        assert message.text == "/help"
        assert message.message_type == MessageType.COMMAND

    def test_from_telegram_update_no_text(self):
        """测试没有文本的 update"""
        update = {"message": {"chat": {"id": 123}, "from": {"id": 456}}}

        message = TelegramMessage.from_telegram_update(update)

        assert message is None

    def test_to_dict(self):
        """测试转换为字典"""
        update = make_text_update("Test")
        message = TelegramMessage.from_telegram_update(update)

        message_dict = message.to_dict()

        assert isinstance(message_dict, dict)
        assert message_dict["text"] == "Test"
        assert message_dict["chat_id"] == 123
        assert message_dict["message_type"] == "text"

    def test_get_content_hash(self):
        """测试内容哈希生成"""
        message1 = TelegramMessage(
            text="Hello",
            chat_id=123,
            user_id=456
        )

        message2 = TelegramMessage(
            text="Hello",
            chat_id=123,
            user_id=456
        )

        message3 = TelegramMessage(
            text="Hello",
            chat_id=999,
            user_id=456
        )

        # 相同的消息应该有相同的哈希
        assert message1.get_content_hash() == message2.get_content_hash()

        # 不同 chat_id 的消息应该有不同的哈希
        assert message1.get_content_hash() != message3.get_content_hash()


# ============================================
# 测试 TelegramCommand
# ============================================

class TestTelegramCommand:
    """测试 TelegramCommand 类"""

    def test_from_telegram_update_simple_command(self):
        """测试简单命令解析"""
        update = make_command_update("/help")

        command = TelegramCommand.from_telegram_update(update)

        assert command is not None
        assert command.command == "/help"
        assert command.args == ""
        assert command.raw_text == "/help"
        assert command.chat_id == 123
        assert command.user_id == 456

    def test_from_telegram_update_command_with_args(self):
        """测试带参数的命令解析"""
        update = make_command_update("/search python tutorial")

        command = TelegramCommand.from_telegram_update(update)

        assert command is not None
        assert command.command == "/search"
        assert command.args == "python tutorial"
        assert command.raw_text == "/search python tutorial"

    def test_from_telegram_update_command_with_bot_mention(self):
        """测试带机器人提及的命令解析"""
        update = make_command_update("/start@mybot")

        command = TelegramCommand.from_telegram_update(update)

        assert command is not None
        assert command.command == "/start"
        assert command.args == ""

    def test_from_telegram_update_non_command(self):
        """测试非命令文本"""
        update = make_text_update("Hello")

        command = TelegramCommand.from_telegram_update(update)

        assert command is None

    def test_to_dict(self):
        """测试转换为字典"""
        update = make_command_update("/help")
        command = TelegramCommand.from_telegram_update(update)

        command_dict = command.to_dict()

        assert isinstance(command_dict, dict)
        assert command_dict["command"] == "/help"
        assert command_dict["chat_id"] == 123


# ============================================
# 测试 SessionContext
# ============================================

class TestSessionContext:
    """测试 SessionContext 类"""

    def test_initialization(self):
        """测试初始化"""
        session = SessionContext(
            chat_id=123,
            session_id="test_session",
            user_id=456,
            username="testuser"
        )

        assert session.chat_id == 123
        assert session.session_id == "test_session"
        assert session.user_id == 456
        assert session.username == "testuser"
        assert session.message_count == 0

    def test_update_activity(self):
        """测试更新活动时间"""
        session = SessionContext(
            chat_id=123,
            session_id="test_session",
            user_id=456
        )

        initial_count = session.message_count
        session.update_activity()

        assert session.message_count == initial_count + 1
        assert session.last_active > 0

    def test_is_expired(self):
        """测试过期检查"""
        # 创建一个刚创建的会话，不应该过期
        session = SessionContext(
            chat_id=123,
            session_id="test_session",
            user_id=456
        )

        assert session.is_expired(ttl_seconds=3600) is False

    def test_is_expired_old_session(self):
        """测试过期检查（旧会话）"""
        session = SessionContext(
            chat_id=123,
            session_id="test_session",
            user_id=456
        )

        # 模拟会话在 2 小时前创建
        session.last_active = int(time.time()) - 7200

        assert session.is_expired(ttl_seconds=3600) is True

    def test_to_dict(self):
        """测试转换为字典"""
        session = SessionContext(
            chat_id=123,
            session_id="test_session",
            user_id=456,
            username="testuser"
        )

        session_dict = session.to_dict()

        assert isinstance(session_dict, dict)
        assert session_dict["chat_id"] == 123
        assert session_dict["session_id"] == "test_session"
        assert session_dict["user_id"] == 456


# ============================================
# 测试 TelegramGateway - 文本消息处理
# ============================================

class TestTelegramGatewayTextMessages:
    """测试 TelegramGateway 文本消息处理"""

    def test_handle_text_message(self):
        """测试处理文本消息"""
        gateway = TelegramGateway()
        update = make_text_update("Hello, world!")

        result = gateway.handle_webhook_update(update)

        assert result.success is True
        assert result.session_id is not None
        assert result.error is None
        assert result.processing_time_ms >= 0  # 可能是 0（执行太快）
        assert isinstance(result.metadata, dict)

        # 验证会话已创建
        session = gateway.get_session(123)
        assert session is not None
        assert session.message_count == 1

    def test_handle_text_message_creates_session(self):
        """测试文本消息创建会话"""
        gateway = TelegramGateway()
        update = make_text_update("Test message")

        result = gateway.handle_webhook_update(update)

        assert result.success is True

        # 验证会话
        session = gateway.get_session(123)
        assert session is not None
        assert session.chat_id == 123
        assert session.user_id == 456
        assert session.message_count == 1

    def test_handle_text_message_reuses_session(self):
        """测试文本消息复用会话"""
        gateway = TelegramGateway()

        # 发送第一条消息
        update1 = make_text_update("First message")
        result1 = gateway.handle_webhook_update(update1)

        session_id_1 = result1.session_id

        # 发送第二条消息（同一聊天）
        update2 = make_text_update("Second message", chat_id=123, message_id=2)
        result2 = gateway.handle_webhook_update(update2)

        session_id_2 = result2.session_id

        # 应该复用同一个会话
        assert session_id_1 == session_id_2

        # 验证会话消息计数
        session = gateway.get_session(123)
        assert session.message_count == 2

    def test_handle_text_message_different_chats(self):
        """测试不同聊天创建不同会话"""
        gateway = TelegramGateway()

        # 聊天 1
        update1 = make_text_update("Message 1", chat_id=123)
        result1 = gateway.handle_webhook_update(update1)

        # 聊天 2
        update2 = make_text_update("Message 2", chat_id=789)
        result2 = gateway.handle_webhook_update(update2)

        # 应该创建不同的会话
        assert result1.session_id != result2.session_id

        # 验证两个会话都存在
        assert gateway.get_session(123) is not None
        assert gateway.get_session(789) is not None

    def test_message_to_event_conversion(self):
        """测试消息到 event 的转换"""
        gateway = TelegramGateway()
        update = make_text_update("Test message")

        result = gateway.handle_webhook_update(update)

        assert result.success is True

        # 检查 metadata 中的 event
        event = result.metadata.get("event")
        assert event is not None
        assert event["type"] == "message"
        assert event["channel"] == "telegram"
        assert event["content"]["text"] == "Test message"
        assert event["content"]["message_type"] == "text"
        assert event["chat_id"] == 123
        assert event["user_id"] == 456

    def test_handle_empty_text(self):
        """测试处理空文本"""
        gateway = TelegramGateway()
        update = {"message": {"text": "", "chat": {"id": 123}, "from": {"id": 456}}}

        result = gateway.handle_webhook_update(update)

        # 没有有效文本，应该失败
        assert result.success is False
        assert result.error is not None


# ============================================
# 测试 TelegramGateway - 命令处理
# ============================================

class TestTelegramGatewayCommands:
    """测试 TelegramGateway 命令处理"""

    def test_handle_start_command(self):
        """测试处理 /start 命令"""
        gateway = TelegramGateway()
        update = make_command_update("/start")

        result = gateway.handle_webhook_update(update)

        assert result.success is True
        assert result.session_id is not None
        assert result.response_text is not None
        assert "Welcome" in result.response_text

    def test_handle_help_command(self):
        """测试处理 /help 命令"""
        gateway = TelegramGateway()
        update = make_command_update("/help")

        result = gateway.handle_webhook_update(update)

        assert result.success is True
        assert result.response_text is not None
        assert "commands" in result.response_text.lower()

    def test_handle_reset_command(self):
        """测试处理 /reset 命令"""
        gateway = TelegramGateway()

        # 创建一个会话
        update1 = make_text_update("First", chat_id=123)
        result1 = gateway.handle_webhook_update(update1)
        old_session_id = result1.session_id

        # 短暂延迟确保不同时间戳
        time.sleep(0.01)

        # 发送 /reset
        update2 = make_command_update("/reset", chat_id=123, message_id=2)
        result2 = gateway.handle_webhook_update(update2)
        new_session_id = result2.session_id

        # 应该创建新会话
        assert old_session_id != new_session_id
        assert "reset" in result2.response_text.lower()

    def test_handle_status_command(self):
        """测试处理 /status 命令"""
        gateway = TelegramGateway()

        # 发送几条消息
        update1 = make_text_update("Message 1", chat_id=123)
        gateway.handle_webhook_update(update1)

        update2 = make_text_update("Message 2", chat_id=123, message_id=2)
        gateway.handle_webhook_update(update2)

        # 发送 /status
        update3 = make_command_update("/status", chat_id=123, message_id=3)
        result3 = gateway.handle_webhook_update(update3)

        assert result3.success is True
        assert "Session active" in result3.response_text
        assert "2" in result3.response_text  # 消息计数

    def test_handle_about_command(self):
        """测试处理 /about 命令"""
        gateway = TelegramGateway()
        update = make_command_update("/about")

        result = gateway.handle_webhook_update(update)

        assert result.success is True
        assert result.response_text is not None

    def test_handle_invalid_command(self):
        """测试处理无效命令"""
        gateway = TelegramGateway()
        update = make_command_update("/invalidcommand")

        result = gateway.handle_webhook_update(update)

        assert result.success is False
        assert result.error is not None
        assert result.error_type == ErrorType.INVALID_COMMAND

    def test_command_to_event_conversion(self):
        """测试命令到 event 的转换"""
        gateway = TelegramGateway()
        update = make_command_update("/help")

        result = gateway.handle_webhook_update(update)

        assert result.success is True

        # 检查 metadata 中的 event
        event = result.metadata.get("event")
        assert event is not None
        assert event["type"] == "command"
        assert event["channel"] == "telegram"
        assert event["content"]["command"] == "/help"
        assert event["content"]["args"] == ""


# ============================================
# 测试 TelegramGateway - 重复消息检测
# ============================================

class TestTelegramGatewayDuplicateDetection:
    """测试 TelegramGateway 重复消息检测"""

    def test_detect_duplicate_message(self):
        """测试重复消息检测"""
        gateway = TelegramGateway()

        # 发送第一条消息
        update1 = make_text_update("Hello", chat_id=123, message_id=1)
        result1 = gateway.handle_webhook_update(update1)

        # 立即发送相同的消息
        update2 = make_text_update("Hello", chat_id=123, message_id=2)
        result2 = gateway.handle_webhook_update(update2)

        # 第一条应该成功
        assert result1.success is True

        # 第二条应该被检测为重复
        assert result2.success is False
        assert result2.error is not None
        assert result2.error_type == ErrorType.DUPLICATE

    def test_duplicate_after_window(self):
        """测试超过时间窗口后不认为是重复"""
        gateway = TelegramGateway(duplicate_window_seconds=1)

        # 发送第一条消息
        update1 = make_text_update("Hello", chat_id=123, message_id=1)
        result1 = gateway.handle_webhook_update(update1)

        # 等待超过时间窗口
        time.sleep(1.5)

        # 发送相同的消息
        update2 = make_text_update("Hello", chat_id=123, message_id=2)
        result2 = gateway.handle_webhook_update(update2)

        # 两条都应该成功
        assert result1.success is True
        assert result2.success is True

    def test_different_chat_not_duplicate(self):
        """测试不同聊天的相同文本不算重复"""
        gateway = TelegramGateway()

        # 聊天 1
        update1 = make_text_update("Hello", chat_id=123, message_id=1)
        result1 = gateway.handle_webhook_update(update1)

        # 聊天 2
        update2 = make_text_update("Hello", chat_id=789, message_id=2)
        result2 = gateway.handle_webhook_update(update2)

        # 两条都应该成功（不同聊天）
        assert result1.success is True
        assert result2.success is True


# ============================================
# 测试 TelegramGateway - 会话管理
# ============================================

class TestTelegramGatewaySessionManagement:
    """测试 TelegramGateway 会话管理"""

    def test_session_expiration(self):
        """测试会话过期"""
        gateway = TelegramGateway(session_ttl_seconds=2)

        # 创建会话
        update1 = make_text_update("Message 1", chat_id=123)
        result1 = gateway.handle_webhook_update(update1)
        old_session_id = result1.session_id

        # 等待会话过期
        time.sleep(2.5)

        # 发送新消息，应该创建新会话
        update2 = make_text_update("Message 2", chat_id=123, message_id=2)
        result2 = gateway.handle_webhook_update(update2)
        new_session_id = result2.session_id

        # 应该创建新会话
        assert old_session_id != new_session_id

    def test_get_session(self):
        """测试获取会话"""
        gateway = TelegramGateway()

        # 发送消息创建会话
        update = make_text_update("Test", chat_id=123)
        gateway.handle_webhook_update(update)

        # 获取会话
        session = gateway.get_session(123)

        assert session is not None
        assert session.chat_id == 123

    def test_get_nonexistent_session(self):
        """测试获取不存在的会话"""
        gateway = TelegramGateway()

        session = gateway.get_session(999)

        assert session is None

    def test_get_all_sessions(self):
        """测试获取所有会话"""
        gateway = TelegramGateway()

        # 创建多个会话
        gateway.handle_webhook_update(make_text_update("Msg 1", chat_id=123))
        gateway.handle_webhook_update(make_text_update("Msg 2", chat_id=456))
        gateway.handle_webhook_update(make_text_update("Msg 3", chat_id=789))

        all_sessions = gateway.get_all_sessions()

        assert len(all_sessions) == 3
        assert 123 in all_sessions
        assert 456 in all_sessions
        assert 789 in all_sessions

    def test_cleanup_expired_sessions(self):
        """测试清理过期会话"""
        gateway = TelegramGateway(session_ttl_seconds=1)

        # 创建会话
        gateway.handle_webhook_update(make_text_update("Msg 1", chat_id=123))
        gateway.handle_webhook_update(make_text_update("Msg 2", chat_id=456))

        # 等待过期
        time.sleep(1.5)

        # 创建新会话（触发自动清理）
        gateway.handle_webhook_update(make_text_update("Msg 3", chat_id=789))

        # 手动清理
        cleaned = gateway.cleanup_expired_sessions()

        # 应该清理了 2 个过期会话
        assert cleaned == 2

        # 只剩新会话
        all_sessions = gateway.get_all_sessions()
        assert len(all_sessions) == 1
        assert 789 in all_sessions


# ============================================
# 测试 TelegramGateway - 统计信息
# ============================================

class TestTelegramGatewayStats:
    """测试 TelegramGateway 统计信息"""

    def test_get_stats_initial(self):
        """测试初始统计信息"""
        gateway = TelegramGateway()

        stats = gateway.get_stats()

        assert stats["active_sessions"] == 0
        assert stats["total_messages"] == 0
        assert stats["cached_duplicate_hashes"] == 0

    def test_get_stats_after_messages(self):
        """测试发送消息后的统计信息"""
        gateway = TelegramGateway()

        # 发送消息
        gateway.handle_webhook_update(make_text_update("Msg 1", chat_id=123))
        gateway.handle_webhook_update(make_text_update("Msg 2", chat_id=123, message_id=2))
        gateway.handle_webhook_update(make_text_update("Msg 3", chat_id=456))

        stats = gateway.get_stats()

        assert stats["active_sessions"] == 2  # 2 个聊天
        assert stats["total_messages"] == 3

    def test_stats_config(self):
        """测试统计信息包含配置"""
        gateway = TelegramGateway(
            session_ttl_seconds=1800,
            duplicate_window_seconds=10
        )

        stats = gateway.get_stats()

        assert stats["session_ttl_seconds"] == 1800
        assert stats["duplicate_window_seconds"] == 10


# ============================================
# 测试边界情况和错误处理
# ============================================

class TestTelegramGatewayEdgeCases:
    """测试 TelegramGateway 边界情况"""

    def test_handle_invalid_update_format(self):
        """测试处理无效的 update 格式"""
        gateway = TelegramGateway()
        update = {"invalid": "data"}

        result = gateway.handle_webhook_update(update)

        assert result.success is False
        assert result.error is not None

    def test_handle_missing_chat_id(self):
        """测试处理缺失 chat_id 的情况"""
        gateway = TelegramGateway()
        update = {
            "message": {
                "text": "Hello",
                "from": {"id": 456},
                "message_id": 1
            }
        }

        result = gateway.handle_webhook_update(update)

        # 应该能够处理（chat_id 默认为 0）
        # 但会创建一个 session_id 为 0 的会话
        assert result is not None

    def test_long_message_handling(self):
        """测试处理长消息"""
        gateway = TelegramGateway()

        long_text = "A" * 5000
        update = make_text_update(long_text)

        result = gateway.handle_webhook_update(update)

        assert result.success is True
        assert result.session_id is not None

    def test_special_characters_in_message(self):
        """测试消息中的特殊字符"""
        gateway = TelegramGateway()

        special_text = "Hello 🤖! @user #tag http://example.com\nNew line"
        update = make_text_update(special_text)

        result = gateway.handle_webhook_update(update)

        assert result.success is True
        assert result.metadata["event"]["content"]["text"] == special_text

    def test_unicode_message(self):
        """测试 Unicode 消息"""
        gateway = TelegramGateway()

        unicode_text = "你好 世界 🌍 Привет مرحبا"
        update = make_text_update(unicode_text)

        result = gateway.handle_webhook_update(update)

        assert result.success is True
        assert result.metadata["event"]["content"]["text"] == unicode_text


# ============================================
# 测试 MessageProcessingResult
# ============================================

class TestMessageProcessingResult:
    """测试 MessageProcessingResult 类"""

    def test_successful_result(self):
        """测试成功结果"""
        result = MessageProcessingResult(
            success=True,
            session_id="test_session",
            response_text="Hello!",
            processing_time_ms=100
        )

        assert result.success is True
        assert result.session_id == "test_session"
        assert result.response_text == "Hello!"
        assert result.processing_time_ms == 100
        assert result.error is None

    def test_failed_result(self):
        """测试失败结果"""
        result = MessageProcessingResult(
            success=False,
            error="Test error",
            error_type=ErrorType.PARSE_ERROR,
            processing_time_ms=50
        )

        assert result.success is False
        assert result.error == "Test error"
        assert result.error_type == ErrorType.PARSE_ERROR
        assert result.session_id is None

    def test_to_dict(self):
        """测试转换为字典"""
        result = MessageProcessingResult(
            success=True,
            session_id="test_session",
            response_text="Hello",
            processing_time_ms=100,
            metadata={"key": "value"}
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["session_id"] == "test_session"
        assert result_dict["response_text"] == "Hello"
        assert result_dict["processing_time_ms"] == 100
        assert result_dict["metadata"]["key"] == "value"


# ============================================
# 集成测试
# ============================================

class TestTelegramGatewayIntegration:
    """集成测试 - 模拟真实使用场景"""

    def test_conversation_flow(self):
        """测试完整的对话流程"""
        gateway = TelegramGateway()

        # 1. 用户发送 /start
        result1 = gateway.handle_webhook_update(make_command_update("/start", chat_id=123))
        assert result1.success is True
        session_id = result1.session_id

        # 2. 用户发送文本消息
        result2 = gateway.handle_webhook_update(make_text_update("Hello", chat_id=123, message_id=2))
        assert result2.success is True
        assert result2.session_id == session_id  # 同一会话

        # 3. 用户发送 /help
        result3 = gateway.handle_webhook_update(make_command_update("/help", chat_id=123, message_id=3))
        assert result3.success is True
        assert result3.session_id == session_id  # 同一会话

        # 4. 用户发送更多消息
        result4 = gateway.handle_webhook_update(make_text_update("How are you?", chat_id=123, message_id=4))
        result5 = gateway.handle_webhook_update(make_text_update("Tell me a joke", chat_id=123, message_id=5))

        assert result4.success is True
        assert result5.success is True

        # 验证会话统计
        session = gateway.get_session(123)
        assert session.message_count == 5

    def test_multiple_concurrent_chats(self):
        """测试多个并发对话"""
        gateway = TelegramGateway()

        # 用户 1 开始对话
        result1a = gateway.handle_webhook_update(make_text_update("Hi", chat_id=111, user_id=1111))
        result1b = gateway.handle_webhook_update(make_text_update("How are you?", chat_id=111, user_id=1111, message_id=2))

        # 用户 2 开始对话
        result2a = gateway.handle_webhook_update(make_text_update("Hello", chat_id=222, user_id=2222))
        result2b = gateway.handle_webhook_update(make_text_update("What's up?", chat_id=222, user_id=2222, message_id=2))

        # 用户 3 开始对话
        result3a = gateway.handle_webhook_update(make_text_update("Hey", chat_id=333, user_id=3333))
        result3b = gateway.handle_webhook_update(make_text_update("Help me", chat_id=333, user_id=3333, message_id=2))

        # 所有都应该成功
        assert result1a.success and result1b.success
        assert result2a.success and result2b.success
        assert result3a.success and result3b.success

        # 每个用户应该有自己的会话
        session1 = gateway.get_session(111)
        session2 = gateway.get_session(222)
        session3 = gateway.get_session(333)

        assert session1.session_id != session2.session_id
        assert session2.session_id != session3.session_id
        assert session1.session_id != session3.session_id

        # 每个会话应该有 2 条消息
        assert session1.message_count == 2
        assert session2.message_count == 2
        assert session3.message_count == 2

    def test_session_reset_mid_conversation(self):
        """测试对话中途重置会话"""
        gateway = TelegramGateway()

        # 开始对话
        result1 = gateway.handle_webhook_update(make_text_update("First message", chat_id=123))
        old_session_id = result1.session_id

        # 继续对话
        result2 = gateway.handle_webhook_update(make_text_update("Second message", chat_id=123, message_id=2))
        assert result2.session_id == old_session_id

        # 用户发送 /reset
        result3 = gateway.handle_webhook_update(make_command_update("/reset", chat_id=123, message_id=3))
        new_session_id = result3.session_id

        # 应该创建新会话
        assert old_session_id != new_session_id

        # 继续对话
        result4 = gateway.handle_webhook_update(make_text_update("New message", chat_id=123, message_id=4))
        assert result4.session_id == new_session_id

        # 旧会话不应该再存在
        old_session = gateway.get_session(123)
        assert old_session.session_id == new_session_id


# ============================================
# 运行测试
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
