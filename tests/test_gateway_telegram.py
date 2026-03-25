from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_claude_agent_service, get_openclaw_compat_service
from autoresearch.api.main import app
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import ClaudeAgentRunRead, OpenClawSessionRead
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def telegram_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "telegram-gateway.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_gateway_it",
            model_cls=OpenClawSessionRead,
        )
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_gateway_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        repo_root=tmp_path,
        max_agents=10,
        max_depth=3,
    )

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_telegram_webhook_routes_to_openclaw_and_agents(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('tg-agent-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 1001,
            "message": {
                "message_id": 77,
                "text": "给我一条口红营销文案",
                "chat": {"id": 9527},
                "from": {"username": "alice"},
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["chat_id"] == "9527"
    assert payload["session_id"] is not None
    assert payload["agent_run_id"] is not None

    finalized = None
    for _ in range(20):
        fetched = telegram_client.get(f"/api/v1/openclaw/agents/{payload['agent_run_id']}")
        assert fetched.status_code == 200
        finalized = fetched.json()
        if finalized["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert finalized is not None
    assert finalized["status"] == "completed"
    assert "tg-agent-ok" in (finalized.get("stdout_preview") or "")

    session = telegram_client.get(f"/api/v1/openclaw/sessions/{payload['session_id']}")
    assert session.status_code == 200
    session_payload = session.json()
    assert session_payload["external_id"] == "9527"
    assert any(event["role"] == "user" for event in session_payload["events"])
    assert any("agent queued" in event["content"] for event in session_payload["events"])


def test_telegram_webhook_secret_token_guard(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "secret-123")
    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 2001,
            "message": {
                "message_id": 88,
                "text": "hello",
                "chat": {"id": 10086},
            },
        },
    )
    assert response.status_code == 401

    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('token-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")
    ok_response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        headers={"x-telegram-bot-api-secret-token": "secret-123"},
        json={
            "update_id": 2002,
            "message": {
                "message_id": 89,
                "text": "hello with secret",
                "chat": {"id": 10086},
            },
        },
    )
    assert ok_response.status_code == 200
    assert ok_response.json()["accepted"] is True
