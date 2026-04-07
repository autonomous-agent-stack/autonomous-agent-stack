from __future__ import annotations

import sys

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.routers import gateway_telegram
from tests.test_gateway_telegram import clear_gateway_guards, telegram_client  # noqa: F401


def test_mainline_webhook_happy_path_with_secret_header(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "mainline-secret")
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('guard-happy-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        headers={"x-telegram-bot-api-secret-token": "mainline-secret"},
        json={
            "update_id": 4101,
            "message": {
                "message_id": 501,
                "text": "happy path",
                "chat": {"id": 88001, "type": "private"},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["agent_run_id"] is not None


def test_mainline_webhook_rejects_missing_secret_before_replay_guard(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "ordered-secret")

    events: list[str] = []
    original_validate = gateway_telegram._validate_secret_token
    original_guard = gateway_telegram._guard_webhook_replay_and_rate

    def wrapped_validate(raw_request) -> None:
        events.append("secret")
        return original_validate(raw_request)

    def wrapped_guard(update) -> None:
        events.append("guard")
        return original_guard(update)

    monkeypatch.setattr(gateway_telegram, "_validate_secret_token", wrapped_validate)
    monkeypatch.setattr(gateway_telegram, "_guard_webhook_replay_and_rate", wrapped_guard)

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 4102,
            "message": {
                "message_id": 502,
                "text": "missing secret",
                "chat": {"id": 88002, "type": "private"},
            },
        },
    )

    assert response.status_code == 401
    assert events == ["secret"]


def test_mainline_webhook_runs_secret_check_before_replay_guard_on_success(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "ordered-secret")
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('ordered-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    events: list[str] = []
    original_validate = gateway_telegram._validate_secret_token
    original_guard = gateway_telegram._guard_webhook_replay_and_rate

    def wrapped_validate(raw_request) -> None:
        events.append("secret")
        return original_validate(raw_request)

    def wrapped_guard(update) -> None:
        events.append("guard")
        return original_guard(update)

    monkeypatch.setattr(gateway_telegram, "_validate_secret_token", wrapped_validate)
    monkeypatch.setattr(gateway_telegram, "_guard_webhook_replay_and_rate", wrapped_guard)

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        headers={"x-telegram-bot-api-secret-token": "ordered-secret"},
        json={
            "update_id": 4103,
            "message": {
                "message_id": 503,
                "text": "ordered success",
                "chat": {"id": 88003, "type": "private"},
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert events[:2] == ["secret", "guard"]


def test_mainline_webhook_rejects_replayed_update_id(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "replay-secret")
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('replay-guard-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    headers = {"x-telegram-bot-api-secret-token": "replay-secret"}
    payload = {
        "update_id": 4104,
        "message": {
            "message_id": 504,
            "text": "replay check",
            "chat": {"id": 88004, "type": "private"},
        },
    }

    first = telegram_client.post("/api/v1/gateway/telegram/webhook", headers=headers, json=payload)
    second = telegram_client.post("/api/v1/gateway/telegram/webhook", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 409


def test_mainline_webhook_rejects_per_chat_rate_limit_overflow(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "rate-secret")
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('rate-guard-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    headers = {"x-telegram-bot-api-secret-token": "rate-secret"}
    chat_id = 88005

    for i in range(1, 32):
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            headers=headers,
            json={
                "update_id": 4200 + i,
                "message": {
                    "message_id": 600 + i,
                    "text": f"rate-{i}",
                    "chat": {"id": chat_id, "type": "private"},
                },
            },
        )

        if i <= 30:
            assert response.status_code == 200
        else:
            assert response.status_code == 429
