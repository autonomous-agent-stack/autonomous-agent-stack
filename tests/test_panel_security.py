from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from fastapi.testclient import TestClient
import pytest

from autoresearch.api.dependencies import (
    get_claude_agent_service,
    get_openclaw_compat_service,
    get_panel_access_service,
    get_panel_audit_service,
    get_telegram_notifier_service,
)
from autoresearch.api.main import app
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.panel_access import PanelAccessService, assert_safe_bind_host
from autoresearch.core.services.panel_audit import PanelAuditService
from autoresearch.shared.models import (
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    OpenClawSessionCreateRequest,
    OpenClawSessionRead,
    PanelAuditLogRead,
)
from autoresearch.shared.store import SQLiteModelRepository


class StubTelegramNotifier:
    def __init__(self) -> None:
        self.manual_events: list[dict[str, str]] = []
        self.status_events: list[dict[str, str]] = []

    @property
    def enabled(self) -> bool:
        return True

    def notify_manual_action(self, *, chat_id: str, entry: PanelAuditLogRead, run_status: str) -> bool:
        self.manual_events.append(
            {
                "chat_id": chat_id,
                "action": entry.action,
                "target_id": entry.target_id,
                "run_status": run_status,
            }
        )
        return True

    def notify_status_magic_link(
        self,
        *,
        chat_id: str,
        summary_lines: list[str],
        magic_link_url: str | None,
        expires_at_iso: str | None,
    ) -> bool:
        self.status_events.append(
            {
                "chat_id": chat_id,
                "magic_link_url": magic_link_url or "",
                "expires_at": expires_at_iso or "",
                "summary": "\n".join(summary_lines),
            }
        )
        return True


@pytest.fixture
def panel_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "panel-security.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_panel_it",
            model_cls=OpenClawSessionRead,
        )
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_panel_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        repo_root=tmp_path,
        max_agents=20,
        max_depth=3,
    )
    panel_access = PanelAccessService(
        secret="panel-secret",
        telegram_bot_token="123456:TEST_BOT_TOKEN",
        telegram_init_data_max_age_seconds=900,
        base_url="http://testserver/api/v1/panel/view",
    )
    panel_audit = PanelAuditService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="panel_audit_logs_panel_it",
            model_cls=PanelAuditLogRead,
        )
    )
    notifier = StubTelegramNotifier()

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_panel_audit_service] = lambda: panel_audit
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    with TestClient(app) as client:
        setattr(client, "_openclaw", openclaw_service)
        setattr(client, "_claude", claude_service)
        setattr(client, "_panel_access", panel_access)
        setattr(client, "_notifier", notifier)
        yield client

    app.dependency_overrides.clear()


def test_bind_host_guard_rejects_public_exposure() -> None:
    assert_safe_bind_host("127.0.0.1")
    assert_safe_bind_host("100.90.80.70")
    with pytest.raises(ValueError):
        assert_safe_bind_host("0.0.0.0")
    with pytest.raises(ValueError):
        assert_safe_bind_host("203.0.113.10")


def test_panel_state_requires_magic_link_token(panel_client: TestClient) -> None:
    response = panel_client.get("/api/v1/panel/state")
    assert response.status_code == 401


def test_panel_state_is_scoped_by_telegram_uid(panel_client: TestClient) -> None:
    openclaw = getattr(panel_client, "_openclaw")
    claude = getattr(panel_client, "_claude")
    panel_access = getattr(panel_client, "_panel_access")

    session_uid_a = openclaw.create_session(
        OpenClawSessionCreateRequest(channel="telegram", external_id="10001", title="uid-a")
    )
    run_uid_a = claude.create(
        ClaudeAgentCreateRequest(
            task_name="uid-a-task",
            prompt="hello-a",
            session_id=session_uid_a.session_id,
            command_override=[sys.executable, "-c", "print('a')"],
            append_prompt=False,
        )
    )

    session_uid_b = openclaw.create_session(
        OpenClawSessionCreateRequest(channel="telegram", external_id="20002", title="uid-b")
    )
    run_uid_b = claude.create(
        ClaudeAgentCreateRequest(
            task_name="uid-b-task",
            prompt="hello-b",
            session_id=session_uid_b.session_id,
            command_override=[sys.executable, "-c", "print('b')"],
            append_prompt=False,
        )
    )

    token = _token_from_magic_link(panel_access.create_magic_link("10001").url)
    scoped = panel_client.get(
        "/api/v1/panel/state",
        headers={"x-autoresearch-panel-token": token},
    )
    assert scoped.status_code == 200
    payload = scoped.json()
    assert payload["telegram_uid"] == "10001"
    assert all(session["external_id"] == "10001" for session in payload["sessions"])
    assert all(run["session_id"] == session_uid_a.session_id for run in payload["agent_runs"])
    assert any(run["agent_run_id"] == run_uid_a.agent_run_id for run in payload["agent_runs"])
    assert all(run["agent_run_id"] != run_uid_b.agent_run_id for run in payload["agent_runs"])

    forbidden = panel_client.get(
        f"/api/v1/panel/agents/{run_uid_b.agent_run_id}",
        headers={"x-autoresearch-panel-token": token},
    )
    assert forbidden.status_code == 403


def test_panel_cancel_retry_writes_audit_and_pushes_notify(panel_client: TestClient) -> None:
    openclaw = getattr(panel_client, "_openclaw")
    claude = getattr(panel_client, "_claude")
    panel_access = getattr(panel_client, "_panel_access")
    notifier = getattr(panel_client, "_notifier")

    session = openclaw.create_session(
        OpenClawSessionCreateRequest(channel="telegram", external_id="9527", title="manual-control")
    )
    run = claude.create(
        ClaudeAgentCreateRequest(
            task_name="to-cancel-and-retry",
            prompt="do it",
            session_id=session.session_id,
            command_override=[sys.executable, "-c", "print('retry-ok')"],
            append_prompt=False,
        )
    )
    token = _token_from_magic_link(panel_access.create_magic_link("9527").url)
    headers = {"x-autoresearch-panel-token": token}

    cancelled = panel_client.post(
        f"/api/v1/panel/agents/{run.agent_run_id}/cancel",
        headers=headers,
        json={"reason": "manual-stop"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "interrupted"

    retried = panel_client.post(
        f"/api/v1/panel/agents/{run.agent_run_id}/retry",
        headers=headers,
        json={"reason": "manual-retry", "metadata_updates": {"from_panel": True}},
    )
    assert retried.status_code == 202
    assert retried.json()["parent_agent_id"] == run.agent_run_id

    audit = panel_client.get("/api/v1/panel/audit/logs?limit=20", headers=headers)
    assert audit.status_code == 200
    actions = [item["action"] for item in audit.json()]
    assert "cancel" in actions
    assert "retry" in actions

    assert len(notifier.manual_events) >= 2
    assert {event["action"] for event in notifier.manual_events} >= {"cancel", "retry"}


def test_panel_state_supports_telegram_init_data_auth(panel_client: TestClient) -> None:
    openclaw = getattr(panel_client, "_openclaw")
    claude = getattr(panel_client, "_claude")

    session = openclaw.create_session(
        OpenClawSessionCreateRequest(channel="telegram", external_id="70001", title="twa-session")
    )
    claude.create(
        ClaudeAgentCreateRequest(
            task_name="twa-task",
            prompt="via mini app",
            session_id=session.session_id,
            command_override=[sys.executable, "-c", "print('ok')"],
            append_prompt=False,
        )
    )

    init_data = _build_telegram_init_data(
        bot_token="123456:TEST_BOT_TOKEN",
        telegram_uid="70001",
    )
    response = panel_client.get(
        "/api/v1/panel/state",
        headers={"x-telegram-init-data": init_data},
    )
    assert response.status_code == 200
    assert response.json()["telegram_uid"] == "70001"


def test_panel_rejects_tampered_telegram_init_data(panel_client: TestClient) -> None:
    init_data = _build_telegram_init_data(
        bot_token="123456:TEST_BOT_TOKEN",
        telegram_uid="70001",
    )
    tampered = init_data.replace("70001", "79999")
    response = panel_client.get(
        "/api/v1/panel/state",
        headers={"x-telegram-init-data": tampered},
    )
    assert response.status_code == 401


def _token_from_magic_link(url: str) -> str:
    parsed = urlparse(url)
    return parse_qs(parsed.query)["token"][0]


def _build_telegram_init_data(
    *,
    bot_token: str,
    telegram_uid: str,
    auth_date: int | None = None,
) -> str:
    payload = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": "AAEAAABBBBBCCCCCDDDD",
        "user": json.dumps(
            {"id": int(telegram_uid), "first_name": "Test", "username": f"user{telegram_uid}"},
            separators=(",", ":"),
            ensure_ascii=False,
        ),
    }
    data_check = "\n".join(f"{key}={value}" for key, value in sorted(payload.items(), key=lambda item: item[0]))
    secret = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    digest = hmac.new(secret, data_check.encode("utf-8"), hashlib.sha256).hexdigest()
    payload["hash"] = digest
    return urlencode(payload)
