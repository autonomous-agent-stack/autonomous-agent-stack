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

from autoresearch.agent_protocol.models import DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.api.dependencies import (
    get_approval_store_service,
    get_autoresearch_planner_service,
    get_capability_provider_registry,
    get_claude_agent_service,
    get_openclaw_compat_service,
    get_panel_access_service,
    get_panel_audit_service,
    get_telegram_notifier_service,
)
from autoresearch.api.main import app
from autoresearch.core.adapters import CapabilityProviderDescriptorRead, CapabilityProviderRegistry
from autoresearch.core.adapters.contracts import CapabilityDomain
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.panel_access import PanelAccessService, assert_safe_bind_host
from autoresearch.core.services.panel_audit import PanelAuditService
from autoresearch.shared.autoresearch_planner_contract import AutoResearchPlanRead, AutoResearchPlannerRequest
from autoresearch.shared.models import (
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    OpenClawSessionCreateRequest,
    OpenClawSessionRead,
    PanelAuditLogRead,
)
from autoresearch.shared.store import SQLiteModelRepository


class StubTelegramNotifier:
    def __init__(self) -> None:
        self.messages: list[dict[str, object]] = []
        self.manual_events: list[dict[str, str]] = []
        self.status_events: list[dict[str, str]] = []

    @property
    def enabled(self) -> bool:
        return True

    def send_message(
        self,
        *,
        chat_id: str,
        text: str,
        disable_web_page_preview: bool = True,
        reply_markup: dict[str, object] | None = None,
    ) -> bool:
        self.messages.append(
            {
                "chat_id": chat_id,
                "text": text,
                "disable_web_page_preview": disable_web_page_preview,
                "reply_markup": reply_markup,
            }
        )
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


class _StubCapabilityProvider:
    def __init__(self, provider_id: str, domain: CapabilityDomain, display_name: str) -> None:
        self._descriptor = CapabilityProviderDescriptorRead(
            provider_id=provider_id,
            domain=domain,
            display_name=display_name,
            capabilities=["stub"],
            metadata={"stub": True},
        )

    def describe(self) -> CapabilityProviderDescriptorRead:
        return self._descriptor


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _successful_run_summary(job: JobSpec) -> RunSummary:
    return RunSummary(
        run_id=job.run_id,
        final_status="ready_for_promotion",
        driver_result=DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status="succeeded",
            summary="panel dispatch completed",
            changed_paths=list(job.policy.allowed_paths),
            recommended_action="promote",
        ),
        validation=ValidationReport(run_id=job.run_id, passed=True),
        promotion_patch_uri="/tmp/panel-dispatch.patch",
    )


@pytest.fixture
def panel_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "panel-security.sqlite3"
    planner_repo_root = tmp_path / "planner-repo"
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
    approval_service = ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="approval_requests_panel_it",
            model_cls=ApprovalRequestRead,
        )
    )
    capability_registry = CapabilityProviderRegistry()
    capability_registry.register(_StubCapabilityProvider("apple-calendar", CapabilityDomain.CALENDAR, "Apple Calendar"))
    capability_registry.register(_StubCapabilityProvider("openclaw-skills", CapabilityDomain.SKILL, "OpenClaw Skills"))
    planner_service = AutoResearchPlannerService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="autoresearch_plans_panel_it",
            model_cls=AutoResearchPlanRead,
        ),
        repo_root=planner_repo_root,
        dispatch_runner=_successful_run_summary,
    )
    notifier = StubTelegramNotifier()

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service
    app.dependency_overrides[get_panel_access_service] = lambda: panel_access
    app.dependency_overrides[get_panel_audit_service] = lambda: panel_audit
    app.dependency_overrides[get_approval_store_service] = lambda: approval_service
    app.dependency_overrides[get_autoresearch_planner_service] = lambda: planner_service
    app.dependency_overrides[get_capability_provider_registry] = lambda: capability_registry
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier

    with TestClient(app) as client:
        setattr(client, "_openclaw", openclaw_service)
        setattr(client, "_claude", claude_service)
        setattr(client, "_panel_access", panel_access)
        setattr(client, "_approval_store", approval_service)
        setattr(client, "_planner", planner_service)
        setattr(client, "_planner_repo_root", planner_repo_root)
        setattr(client, "_capability_registry", capability_registry)
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


def test_panel_view_contains_capability_section(panel_client: TestClient) -> None:
    response = panel_client.get("/api/v1/panel/view")

    assert response.status_code == 200
    assert "能力概览" in response.text
    assert "capability_providers" in response.text
    assert "待审批" in response.text
    assert "pending_approvals" in response.text
    assert "AutoResearch Plans" in response.text
    assert "pending_autoresearch_plans" in response.text


def test_panel_state_is_scoped_by_telegram_uid(panel_client: TestClient) -> None:
    openclaw = getattr(panel_client, "_openclaw")
    claude = getattr(panel_client, "_claude")
    panel_access = getattr(panel_client, "_panel_access")
    approval_store = getattr(panel_client, "_approval_store")

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
    approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Approve UID A branch",
            telegram_uid="10001",
            session_id=session_uid_a.session_id,
            agent_run_id=run_uid_a.agent_run_id,
        )
    )
    approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Approve UID B branch",
            telegram_uid="20002",
            session_id=session_uid_b.session_id,
            agent_run_id=run_uid_b.agent_run_id,
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
    assert [item["provider_id"] for item in payload["capability_providers"]] == [
        "apple-calendar",
        "openclaw-skills",
    ]
    assert len(payload["pending_approvals"]) == 1
    assert payload["pending_approvals"][0]["telegram_uid"] == "10001"
    assert payload["pending_approvals"][0]["agent_run_id"] == run_uid_a.agent_run_id

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
    assert cancelled.json()["status"] == "cancelled"

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


def test_panel_approval_actions_are_scoped_and_audited(panel_client: TestClient) -> None:
    panel_access = getattr(panel_client, "_panel_access")
    approval_store = getattr(panel_client, "_approval_store")
    notifier = getattr(panel_client, "_notifier")

    owned = approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Approve owned branch",
            telegram_uid="9527",
            session_id="oc_owned",
            agent_run_id="run_owned",
        )
    )
    foreign = approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Approve foreign branch",
            telegram_uid="9528",
            session_id="oc_foreign",
            agent_run_id="run_foreign",
        )
    )

    token = _token_from_magic_link(panel_access.create_magic_link("9527").url)
    headers = {"x-autoresearch-panel-token": token}

    approvals = panel_client.get("/api/v1/panel/approvals", headers=headers)
    assert approvals.status_code == 200
    payload = approvals.json()
    assert len(payload) == 1
    assert payload[0]["approval_id"] == owned.approval_id

    approved = panel_client.post(
        f"/api/v1/panel/approvals/{owned.approval_id}/approve",
        headers=headers,
        json={"note": "approved via panel", "metadata": {}},
    )
    assert approved.status_code == 200
    approved_payload = approved.json()
    assert approved_payload["status"] == "approved"
    assert approved_payload["decided_by"] == "9527"

    forbidden = panel_client.post(
        f"/api/v1/panel/approvals/{foreign.approval_id}/reject",
        headers=headers,
        json={"note": "not mine", "metadata": {}},
    )
    assert forbidden.status_code == 403

    audit = panel_client.get("/api/v1/panel/audit/logs?limit=20", headers=headers)
    assert audit.status_code == 200
    audit_payload = audit.json()
    assert audit_payload[0]["action"] == "approve"
    assert audit_payload[0]["target_type"] == "approval_request"
    assert audit_payload[0]["target_id"] == owned.approval_id

    assert any(event["action"] == "approve" for event in notifier.manual_events)


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


def test_panel_lists_and_dispatches_autoresearch_plans(panel_client: TestClient) -> None:
    panel_access = getattr(panel_client, "_panel_access")
    planner = getattr(panel_client, "_planner")
    planner_repo_root = getattr(panel_client, "_planner_repo_root")
    notifier = getattr(panel_client, "_notifier")

    _write(
        planner_repo_root / "src" / "autoresearch" / "core" / "services" / "panel_target.py",
        "\n".join(
            [
                "def panel_target() -> bool:",
                "    # FIXME: add regression coverage for panel dispatch",
                "    return True",
                "",
            ]
        ),
    )
    plan = planner.create(AutoResearchPlannerRequest(telegram_uid="9527"))

    token = _token_from_magic_link(panel_access.create_magic_link("9527").url)
    headers = {"x-autoresearch-panel-token": token}

    state = panel_client.get("/api/v1/panel/state", headers=headers)
    assert state.status_code == 200
    pending_plans = state.json()["pending_autoresearch_plans"]
    assert len(pending_plans) == 1
    assert pending_plans[0]["plan_id"] == plan.plan_id
    assert pending_plans[0]["selected_candidate"]["source_path"] == (
        "src/autoresearch/core/services/panel_target.py"
    )

    dispatch = panel_client.post(
        f"/api/v1/panel/autoresearch/plans/{plan.plan_id}/dispatch",
        headers=headers,
        json={"note": "ship it", "metadata": {"source": "panel-test"}},
    )
    assert dispatch.status_code == 200
    assert dispatch.json()["dispatch_status"] == "dispatching"

    stored = planner.get(plan.plan_id)
    assert stored is not None
    assert stored.dispatch_status.value == "dispatched"
    assert stored.run_summary is not None
    assert stored.run_summary.final_status == "ready_for_promotion"

    refreshed = panel_client.get("/api/v1/panel/state", headers=headers)
    assert refreshed.status_code == 200
    assert refreshed.json()["pending_autoresearch_plans"] == []

    audit = panel_client.get("/api/v1/panel/audit/logs?limit=20", headers=headers)
    assert audit.status_code == 200
    assert any(item["action"] == "dispatch" for item in audit.json())

    assert any("[AutoResearch Dispatch]" in str(message["text"]) for message in notifier.messages)
    assert any(message["chat_id"] == "9527" for message in notifier.messages)


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
