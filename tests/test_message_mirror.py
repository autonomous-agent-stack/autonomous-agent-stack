"""Tests for gateway.message_mirror — MessageMirror formatting, stats, batch."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.message_mirror import MessageMirror


def _make_message(**overrides) -> dict:
    defaults = {
        "chat_id": -100123,
        "thread_id": 10,
        "message_id": 42,
        "text": "Hello world",
        "sender_id": 999,
    }
    defaults.update(overrides)
    return defaults


class TestMessageMirrorInit:
    def test_init_without_bot(self) -> None:
        mirror = MessageMirror()
        assert mirror.bot is None
        assert mirror.mirror_count == 0

    def test_init_with_bot(self) -> None:
        bot = MagicMock()
        mirror = MessageMirror(bot=bot)
        assert mirror.bot is bot


class TestBuildMirrorText:
    def test_full_message(self) -> None:
        mirror = MessageMirror()
        msg = _make_message(text="Test content", sender_id=123, message_id=7)
        text = mirror._build_mirror_text(msg)
        assert "#7" in text
        assert "123" in text
        assert "Test content" in text

    def test_missing_fields_use_defaults(self) -> None:
        mirror = MessageMirror()
        text = mirror._build_mirror_text({})
        assert "Unknown" in text
        assert "N/A" in text
        assert "Main" in text

    def test_mirror_header_format(self) -> None:
        mirror = MessageMirror()
        text = mirror._build_mirror_text(_make_message())
        assert "镜像消息" in text
        assert "发送者" in text
        assert "来源话题" in text


class TestMirrorToBackup:
    @pytest.mark.asyncio
    async def test_mirror_without_bot_uses_mock_id(self) -> None:
        mirror = MessageMirror()
        result = await mirror.mirror_to_backup(_make_message(), backup_chat_id=-200, backup_thread_id=20)
        assert result["status"] == "success"
        assert isinstance(result["backup_message_id"], int)
        assert result["mirror_count"] == 1

    @pytest.mark.asyncio
    async def test_mirror_increments_count(self) -> None:
        mirror = MessageMirror()
        await mirror.mirror_to_backup(_make_message(), -200, 20)
        await mirror.mirror_to_backup(_make_message(), -200, 20)
        assert mirror.mirror_count == 2

    @pytest.mark.asyncio
    async def test_mirror_with_bot(self) -> None:
        mock_msg = MagicMock()
        mock_msg.message_id = 888
        bot = MagicMock()
        bot.send_message = AsyncMock(return_value=mock_msg)
        mirror = MessageMirror(bot=bot)
        result = await mirror.mirror_to_backup(_make_message(), -200, 20)
        assert result["status"] == "success"
        assert result["backup_message_id"] == 888
        bot.send_message.assert_called_once()


class TestBatchMirror:
    @pytest.mark.asyncio
    async def test_batch_success(self) -> None:
        mirror = MessageMirror()
        messages = [_make_message(message_id=i) for i in range(3)]
        result = await mirror.batch_mirror(messages, backup_chat_id=-200, backup_thread_id=20)
        assert result["status"] == "success"
        assert result["success_count"] == 3
        assert result["failed_count"] == 0
        assert len(result["results"]) == 3

    @pytest.mark.asyncio
    async def test_batch_empty(self) -> None:
        mirror = MessageMirror()
        result = await mirror.batch_mirror([], backup_chat_id=-200, backup_thread_id=20)
        assert result["status"] == "success"
        assert result["success_count"] == 0

    @pytest.mark.asyncio
    async def test_batch_partial_failure(self) -> None:
        mirror = MessageMirror()
        # Force an error on the second call by corrupting _build_mirror_text
        call_count = 0
        original_build = mirror._build_mirror_text

        def flaky_build(msg):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("forced error")
            return original_build(msg)

        mirror._build_mirror_text = flaky_build
        messages = [_make_message(message_id=i) for i in range(3)]
        result = await mirror.batch_mirror(messages, -200, 20)
        assert result["status"] == "partial"
        assert result["failed_count"] == 1
        assert result["success_count"] == 2


class TestGetMirrorStats:
    def test_initial_stats(self) -> None:
        mirror = MessageMirror()
        stats = mirror.get_mirror_stats()
        assert stats["total_mirrored"] == 0
        assert stats["bot_configured"] is False

    def test_stats_after_mirror(self) -> None:
        mirror = MessageMirror()
        mirror.mirror_count = 5
        stats = mirror.get_mirror_stats()
        assert stats["total_mirrored"] == 5

    def test_stats_with_bot(self) -> None:
        mirror = MessageMirror(bot=MagicMock())
        stats = mirror.get_mirror_stats()
        assert stats["bot_configured"] is True


class TestGenerateMockMessageId:
    def test_monotonic_ids(self) -> None:
        mirror = MessageMirror()
        id1 = mirror._generate_mock_message_id()
        id2 = mirror._generate_mock_message_id()
        assert id2 > id1
