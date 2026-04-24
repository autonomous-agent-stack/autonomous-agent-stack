"""Integration tests for Telegram webhook edge cases.

Tests cover: edited messages, missing fields, non-text payloads,
malformed JSON structures, and graceful degradation paths.
"""
from __future__ import annotations

import sqlite3
import sys

import pytest
from fastapi.testclient import TestClient

from autoresearch.api import dependencies as api_dependencies
from autoresearch.api.routers import gateway_telegram
from autoresearch.api.settings import clear_settings_caches


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    clear_settings_caches()
    yield
    clear_settings_caches()


@pytest.fixture
def webhook_client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test_webhook_edge.db"
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")
    clear_settings_caches()

    from autoresearch.api.main import create_app

    app = create_app()
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestEditedMessage:
    """Webhook handles edited_message field same as message."""

    def test_edited_message_accepted(self, webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
            f"{sys.executable} -c \"print('edited-ok')\"",
        )

        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 7001,
                "edited_message": {
                    "message_id": 801,
                    "text": "edited text content",
                    "chat": {"id": 99001, "type": "private"},
                    "from": {"id": 99001, "username": "editor"},
                },
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True

    def test_edited_message_with_no_text_handled_gracefully(
        self, webhook_client: TestClient,
    ) -> None:
        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 7002,
                "edited_message": {
                    "message_id": 802,
                    "chat": {"id": 99002, "type": "private"},
                    "from": {"id": 99002},
                },
            },
        )

        assert response.status_code == 200


class TestMissingFields:
    """Webhook handles missing or empty fields gracefully."""

    def test_message_with_no_text_field(self, webhook_client: TestClient) -> None:
        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 7003,
                "message": {
                    "message_id": 803,
                    "chat": {"id": 99003, "type": "private"},
                    "from": {"id": 99003},
                },
            },
        )

        assert response.status_code == 200
        payload = response.json()
        # Messages without text are accepted (200) but may not be dispatched
        assert payload["accepted"] is True or payload.get("reason") is not None

    def test_message_with_no_from_field(self, webhook_client: TestClient) -> None:
        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 7004,
                "message": {
                    "message_id": 804,
                    "text": "no from field",
                    "chat": {"id": 99004, "type": "group"},
                },
            },
        )

        assert response.status_code == 200

    def test_message_with_empty_chat_id(self, webhook_client: TestClient) -> None:
        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 7005,
                "message": {
                    "message_id": 805,
                    "text": "empty chat",
                    "chat": {"id": None, "type": "private"},
                },
            },
        )

        assert response.status_code == 200

    def test_update_with_no_message_or_edited_message(
        self, webhook_client: TestClient,
    ) -> None:
        """Update with only update_id should be accepted but not processed."""
        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={"update_id": 7006},
        )

        assert response.status_code == 200


class TestNonTextMessages:
    """Webhook handles non-text message types (photos, stickers, etc.)."""

    def test_photo_message_without_caption(self, webhook_client: TestClient) -> None:
        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 7007,
                "message": {
                    "message_id": 807,
                    "photo": [
                        {"file_id": "abc123", "width": 320, "height": 240},
                    ],
                    "chat": {"id": 99007, "type": "private"},
                    "from": {"id": 99007},
                },
            },
        )

        assert response.status_code == 200

    def test_sticker_message(self, webhook_client: TestClient) -> None:
        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 7008,
                "message": {
                    "message_id": 808,
                    "sticker": {
                        "file_id": "stk123",
                        "width": 512,
                        "height": 512,
                        "emoji": "👍",
                    },
                    "chat": {"id": 99008, "type": "private"},
                    "from": {"id": 99008},
                },
            },
        )

        assert response.status_code == 200

    def test_photo_message_with_caption_routed(self, webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
            f"{sys.executable} -c \"print('photo-caption-ok')\"",
        )

        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 7009,
                "message": {
                    "message_id": 809,
                    "photo": [
                        {"file_id": "def456", "width": 800, "height": 600},
                    ],
                    "caption": "核对这张图的提成的excel",
                    "chat": {"id": 99009, "type": "private"},
                    "from": {"id": 99009},
                },
            },
        )

        assert response.status_code == 200


class TestMalformedPayload:
    """Webhook handles malformed or unexpected payloads."""

    def test_empty_json_object(self, webhook_client: TestClient) -> None:
        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={},
        )

        # Should accept (200) even with empty body
        assert response.status_code == 200

    def test_update_id_zero_accepted(self, webhook_client: TestClient) -> None:
        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 0,
                "message": {
                    "message_id": 0,
                    "text": "zero update_id",
                    "chat": {"id": 99010, "type": "private"},
                },
            },
        )

        assert response.status_code == 200

    def test_very_long_text_message(self, webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
            f"{sys.executable} -c \"print('long-ok')\"",
        )

        long_text = "很长的消息" * 1000  # ~5000 chars

        response = webhook_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 7011,
                "message": {
                    "message_id": 811,
                    "text": long_text,
                    "chat": {"id": 99011, "type": "private"},
                    "from": {"id": 99011},
                },
            },
        )

        assert response.status_code == 200


class TestGuardIntegration:
    """Test that guard functions work correctly with edge-case payloads."""

    @pytest.fixture(autouse=True)
    def _clear_guards(self) -> None:
        gateway_telegram._CHAT_RATE_WINDOWS.clear()  # type: ignore[attr-defined]
        yield
        gateway_telegram._CHAT_RATE_WINDOWS.clear()  # type: ignore[attr-defined]

    def test_replay_guard_rejects_duplicate_across_different_payloads(
        self, webhook_client: TestClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv(
            "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
            f"{sys.executable} -c \"print('replay-ok')\"",
        )

        update_id = 7020
        base_payload = {
            "update_id": update_id,
            "message": {
                "message_id": 820,
                "text": "first message",
                "chat": {"id": 99020, "type": "private"},
            },
        }

        first = webhook_client.post("/api/v1/gateway/telegram/webhook", json=base_payload)
        assert first.status_code == 200

        # Different text, same update_id → replay guard should reject
        second_payload = {
            "update_id": update_id,
            "message": {
                "message_id": 821,
                "text": "second message with same update_id",
                "chat": {"id": 99020, "type": "private"},
            },
        }
        second = webhook_client.post("/api/v1/gateway/telegram/webhook", json=second_payload)
        assert second.status_code == 409
