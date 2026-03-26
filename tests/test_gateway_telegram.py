from __future__ import annotations

import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import (
    get_admin_config_service,
    get_claude_agent_service,
    get_openclaw_compat_service,
    get_panel_access_service,
    get_telegram_notifier_service,
)
from autoresearch.api.main import app
from autoresearch.api.routers import gateway_telegram
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.shared.models import (
    AdminAgentConfigRead,
    AdminChannelConfigRead,
    AdminConfigRevisionRead,
    ClaudeAgentRunRead,
    OpenClawSessionRead,
)
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
    admin_config_service = AdminConfigService(
        agent_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_agent_configs_gateway_it",
            model_cls=AdminAgentConfigRead,
        ),
        channel_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_channel_configs_gateway_it",
            model_cls=AdminChannelConfigRead,
        ),
        revision_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_config_revisions_gateway_it",
            model_cls=AdminConfigRevisionRead,
        ),
    )

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service
    app.dependency_overrides[get_admin_config_service] = lambda: admin_config_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_gateway_guards() -> None:
    gateway_telegram._SEEN_UPDATES.clear()
    gateway_telegram._CHAT_RATE_WINDOWS.clear()


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


def test_telegram_webhook_secret_required_in_production(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", raising=False)
    response = telegram_client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 2101,
            "message": {
                "message_id": 91,
                "text": "prod check",
                "chat": {"id": 10087},
            },
        },
    )
    assert response.status_code == 503


def test_telegram_webhook_replay_rejected(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('replay-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    payload = {
        "update_id": 2201,
        "message": {"message_id": 92, "text": "hello", "chat": {"id": 10088}},
    }
    first = telegram_client.post("/api/v1/gateway/telegram/webhook", json=payload)
    assert first.status_code == 200

    second = telegram_client.post("/api/v1/gateway/telegram/webhook", json=payload)
    assert second.status_code == 409


def test_telegram_webhook_rate_limit_rejected(
    telegram_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE",
        f"{sys.executable} -c \"print('rate-ok')\"",
    )
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", "false")

    chat_id = 10089
    for i in range(1, 32):
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 2300 + i,
                "message": {"message_id": 100 + i, "text": f"load-{i}", "chat": {"id": chat_id}},
            },
        )
        if i <= 30:
            assert response.status_code == 200
        else:
            assert response.status_code == 429


def test_telegram_status_query_returns_magic_link(
    telegram_client: TestClient,
) -> None:
    class StubNotifier:
        def __init__(self) -> None:
            self.status_events: list[dict[str, str]] = []

        @property
        def enabled(self) -> bool:
            return True

        def notify_status_magic_link(
            self,
            *,
            chat_id: str,
            summary_lines: list[str],
            magic_link_url: str | None,
            expires_at_iso: str | None,
            is_group_link: bool = False,
            mini_app_url: str | None = None,
        ) -> bool:
            self.status_events.append(
                {
                    "chat_id": chat_id,
                    "magic_link_url": magic_link_url or "",
                    "expires_at": expires_at_iso or "",
                    "summary": "\n".join(summary_lines),
                    "is_group_link": str(is_group_link),
                    "mini_app_url": mini_app_url or "",
                }
            )
            return True

        def notify_manual_action(self, *, chat_id: str, entry: object, run_status: str) -> bool:
            return True

    panel_access = PanelAccessService(
        secret="tg-panel-secret",
        base_url="https://panel.example.com/api/v1/panel/view",
    )
    notifier = StubNotifier()
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 3001,
                "message": {
                    "message_id": 90,
                    "text": "/status",
                    "chat": {"id": 9527},
                    "from": {"username": "alice"},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["accepted"] is True
        assert payload["agent_run_id"] is None
        link = payload["metadata"]["magic_link_url"]
        assert link.startswith("https://panel.example.com/api/v1/panel/view?")
        token = parse_qs(urlparse(link).query)["token"][0]
        claims = panel_access.verify_token(token)
        assert claims.telegram_uid == "9527"

        assert len(notifier.status_events) == 1
        assert notifier.status_events[0]["chat_id"] == "9527"
        assert notifier.status_events[0]["magic_link_url"] == link
    finally:
        app.dependency_overrides.pop(get_panel_access_service, None)
        app.dependency_overrides.pop(get_telegram_notifier_service, None)
