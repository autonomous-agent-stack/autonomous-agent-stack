from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import (
    get_admin_auth_service,
    get_admin_config_service,
    get_approval_store_service,
    get_capability_provider_registry,
    get_claude_agent_service,
    get_openclaw_compat_service,
)
from autoresearch.api.main import app
from autoresearch.core.adapters import CapabilityProviderDescriptorRead, CapabilityProviderRegistry
from autoresearch.core.adapters.contracts import CapabilityDomain
from autoresearch.core.services.admin_auth import AdminAuthService
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.admin_secrets import AdminSecretCipher
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import (
    AdminAgentConfigRead,
    AdminChannelConfigRead,
    AdminConfigRevisionRead,
    AdminSecretRecordRead,
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ClaudeAgentRunRead,
    OpenClawSessionRead,
)
from autoresearch.shared.store import SQLiteModelRepository


class _StubCapabilityProvider:
    def __init__(self, *, provider_id: str, domain: CapabilityDomain, display_name: str) -> None:
        self._descriptor = CapabilityProviderDescriptorRead(
            provider_id=provider_id,
            domain=domain,
            display_name=display_name,
            capabilities=["stub"],
            metadata={"stub": True},
        )

    def describe(self) -> CapabilityProviderDescriptorRead:
        return self._descriptor


class _StubSkillProvider(_StubCapabilityProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_id="openclaw-skills",
            domain=CapabilityDomain.SKILL,
            display_name="OpenClaw Skills",
        )

    def list_skills(self):
        from autoresearch.core.adapters.contracts import SkillCatalogRead
        from autoresearch.shared.models import OpenClawSkillRead

        return SkillCatalogRead(
            provider_id="openclaw-skills",
            status="available",
            skills=[
                OpenClawSkillRead(
                    name="Daily Brief",
                    skill_key="daily_brief",
                    description="Generate a daily brief",
                    source="workspace",
                    base_dir="/tmp/skills/daily_brief",
                    file_path="/tmp/skills/daily_brief/SKILL.md",
                    metadata={"stub": True},
                )
            ],
        )

    def get_skill(self, skill_name: str):
        return None


class _StubMCPProvider(_StubCapabilityProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_id="mcp-context",
            domain=CapabilityDomain.MCP,
            display_name="MCP Context",
        )

    def list_tools(self):
        from autoresearch.core.adapters.contracts import MCPToolDescriptorRead

        return [MCPToolDescriptorRead(name="echo_tool", description="Echo payload", metadata={"stub": True})]

    async def call_tool(self, tool_name: str, params: dict[str, object]):
        return {"tool_name": tool_name, "params": params}


class _StubCalendarProvider(_StubCapabilityProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_id="apple-calendar",
            domain=CapabilityDomain.CALENDAR,
            display_name="Apple Calendar",
        )

    def query_events(self, query):
        return {}


@pytest.fixture
def admin_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "admin.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_admin_it",
            model_cls=OpenClawSessionRead,
        )
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_admin_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        repo_root=tmp_path,
        max_agents=10,
        max_depth=3,
    )
    admin_service = AdminConfigService(
        agent_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_agent_configs_it",
            model_cls=AdminAgentConfigRead,
        ),
        channel_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_channel_configs_it",
            model_cls=AdminChannelConfigRead,
        ),
        revision_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_config_revisions_it",
            model_cls=AdminConfigRevisionRead,
        ),
        secret_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="admin_secret_records_it",
            model_cls=AdminSecretRecordRead,
        ),
        secret_cipher=AdminSecretCipher(secret_key="test-secret-key"),
    )
    auth_service = AdminAuthService(
        secret="test-admin-jwt-secret",
        bootstrap_key="bootstrap-test-key",
    )
    approval_store = ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="approval_requests_admin_it",
            model_cls=ApprovalRequestRead,
        )
    )
    capability_registry = CapabilityProviderRegistry()
    capability_registry.register(_StubCalendarProvider())
    capability_registry.register(_StubSkillProvider())
    capability_registry.register(_StubMCPProvider())

    app.dependency_overrides[get_openclaw_compat_service] = lambda: openclaw_service
    app.dependency_overrides[get_claude_agent_service] = lambda: claude_service
    app.dependency_overrides[get_admin_config_service] = lambda: admin_service
    app.dependency_overrides[get_admin_auth_service] = lambda: auth_service
    app.dependency_overrides[get_approval_store_service] = lambda: approval_store
    app.dependency_overrides[get_capability_provider_registry] = lambda: capability_registry

    with TestClient(app) as client:
        token_response = client.post(
            "/api/v1/admin/auth/token",
            json={"subject": "test-owner", "roles": ["owner"], "ttl_seconds": 3600},
            headers={"x-admin-bootstrap-key": "bootstrap-test-key"},
        )
        assert token_response.status_code == 200
        token = token_response.json()["token"]
        client.headers.update({"authorization": f"Bearer {token}"})
        setattr(client, "_admin_service", admin_service)
        setattr(client, "_approval_store", approval_store)
        yield client

    app.dependency_overrides.clear()


def _wait_terminal(client: TestClient, agent_run_id: str, attempts: int = 40) -> dict[str, object]:
    finalized: dict[str, object] | None = None
    for _ in range(attempts):
        fetched = client.get(f"/api/v1/openclaw/agents/{agent_run_id}")
        assert fetched.status_code == 200
        finalized = fetched.json()
        if finalized["status"] in {"completed", "failed", "interrupted"}:
            break
        time.sleep(0.05)
    assert finalized is not None
    return finalized


def test_admin_requires_bearer_token(admin_client: TestClient) -> None:
    existing = admin_client.headers.pop("authorization", None)
    denied = admin_client.get("/api/v1/admin/agents")
    assert denied.status_code == 401
    denied_capabilities = admin_client.get("/api/v1/admin/capabilities")
    assert denied_capabilities.status_code == 401
    if existing is not None:
        admin_client.headers["authorization"] = existing


def test_admin_view_contains_capability_inventory_section(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/admin/view")

    assert response.status_code == 200
    assert "Capability Inventory" in response.text
    assert "Approval Queue" in response.text
    assert "Managed Skill Queue" in response.text
    assert "/api/v1/admin/capabilities" in response.text
    assert "/api/v1/admin/approvals" in response.text
    assert "/api/v1/admin/skills/status" in response.text


def test_admin_capability_snapshot_lists_provider_inventory(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/admin/capabilities")

    assert response.status_code == 200
    payload = response.json()
    assert [item["provider"]["provider_id"] for item in payload["providers"]] == [
        "apple-calendar",
        "mcp-context",
        "openclaw-skills",
    ]
    calendar_provider = payload["providers"][0]
    assert calendar_provider["supports_calendar_query"] is True
    assert calendar_provider["supports_github_search"] is False
    assert calendar_provider["skills"] == []
    mcp_provider = payload["providers"][1]
    assert mcp_provider["tools"][0]["name"] == "echo_tool"
    skill_provider = payload["providers"][2]
    assert skill_provider["skills"][0]["skill_key"] == "daily_brief"


def test_admin_approvals_list_and_resolve(admin_client: TestClient) -> None:
    approval_store = getattr(admin_client, "_approval_store")
    owned = approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Approve release branch",
            summary="Promote release/2026-03-28 after regression",
            telegram_uid="10001",
            session_id="oc_admin_a",
            agent_run_id="run_admin_a",
            source="git_policy",
        )
    )
    other = approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Reject unsigned skill",
            telegram_uid="10002",
            session_id="oc_admin_b",
            agent_run_id="run_admin_b",
            source="skill_registry",
        )
    )

    listed = admin_client.get("/api/v1/admin/approvals?status=pending&telegram_uid=10001")
    assert listed.status_code == 200
    listed_payload = listed.json()
    assert len(listed_payload) == 1
    assert listed_payload[0]["approval_id"] == owned.approval_id
    assert listed_payload[0]["status"] == "pending"

    approved = admin_client.post(
        f"/api/v1/admin/approvals/{owned.approval_id}/approve",
        json={"note": "approved via admin", "metadata": {}},
    )
    assert approved.status_code == 200
    approved_payload = approved.json()
    assert approved_payload["status"] == "approved"
    assert approved_payload["decided_by"] == "test-owner"
    assert approved_payload["decision_note"] == "approved via admin"
    assert approved_payload["metadata"]["resolved_via"] == "admin_api"

    rejected = admin_client.post(
        f"/api/v1/admin/approvals/{other.approval_id}/reject",
        json={"note": "reject via admin", "metadata": {"reason": "unsigned"}},
    )
    assert rejected.status_code == 200
    rejected_payload = rejected.json()
    assert rejected_payload["status"] == "rejected"
    assert rejected_payload["decided_by"] == "test-owner"
    assert rejected_payload["metadata"]["resolved_via"] == "admin_api"
    assert rejected_payload["metadata"]["reason"] == "unsigned"

    pending_after = admin_client.get("/api/v1/admin/approvals?status=pending")
    assert pending_after.status_code == 200
    assert pending_after.json() == []


def test_admin_agent_crud_history_rollback(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/v1/admin/agents",
        json={
            "name": "writer",
            "description": "copy writer",
            "task_name": "write-copy",
            "prompt_template": "Write concise ad copy",
            "default_timeout_seconds": 60,
            "default_generation_depth": 1,
            "default_env": {"A": "1"},
            "channel_bindings": ["telegram"],
            "enabled": True,
            "actor": "test-admin",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    agent_id = payload["agent_id"]
    assert payload["version"] == 1
    assert payload["status"] == "active"

    updated = admin_client.put(
        f"/api/v1/admin/agents/{agent_id}",
        json={
            "description": "copy writer v2",
            "metadata_updates": {"team": "growth"},
            "actor": "test-admin",
            "reason": "tune copy style",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["description"] == "copy writer v2"
    assert updated.json()["metadata"]["team"] == "growth"

    deactivated = admin_client.post(
        f"/api/v1/admin/agents/{agent_id}/deactivate",
        json={"actor": "test-admin", "reason": "maintenance"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    assert deactivated.json()["version"] == 3

    rolled = admin_client.post(
        f"/api/v1/admin/agents/{agent_id}/rollback",
        json={"version": 1, "actor": "test-admin", "reason": "restore baseline"},
    )
    assert rolled.status_code == 200
    assert rolled.json()["version"] == 4
    assert rolled.json()["status"] == "active"
    assert rolled.json()["description"] == "copy writer"

    history = admin_client.get(f"/api/v1/admin/agents/{agent_id}/history")
    assert history.status_code == 200
    actions = [item["action"] for item in history.json()]
    assert "create" in actions
    assert "update" in actions
    assert "deactivate" in actions
    assert "rollback" in actions


def test_admin_agent_launch_from_config(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/v1/admin/agents",
        json={
            "name": "runner",
            "task_name": "run-task",
            "prompt_template": "execute",
            "default_timeout_seconds": 20,
            "default_generation_depth": 1,
            "command_override": [sys.executable, "-c", "print('admin-run-ok')"],
            "append_prompt": False,
            "enabled": True,
            "actor": "test-admin",
        },
    )
    assert created.status_code == 201
    agent_id = created.json()["agent_id"]

    launched = admin_client.post(
        f"/api/v1/admin/agents/{agent_id}/launch",
        json={
            "metadata_updates": {"launch_source": "test"},
            "env_overrides": {"TEST_ENV": "1"},
        },
    )
    assert launched.status_code == 202
    launch_payload = launched.json()
    assert launch_payload["status"] == "queued"
    assert launch_payload["metadata"]["agent_config_id"] == agent_id

    finalized = _wait_terminal(admin_client, launch_payload["agent_run_id"], attempts=30)
    assert finalized["status"] == "completed"
    assert "admin-run-ok" in (finalized.get("stdout_preview") or "")


def test_admin_channel_crud_and_duplicate_key_guard(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/v1/admin/channels",
        json={
            "key": "telegram-main",
            "display_name": "Telegram Main",
            "provider": "telegram",
            "allowed_chat_ids": ["-10001"],
            "enabled": True,
            "actor": "test-admin",
        },
    )
    assert created.status_code == 201
    channel_id = created.json()["channel_id"]
    assert created.json()["version"] == 1

    duplicate = admin_client.post(
        "/api/v1/admin/channels",
        json={
            "key": "telegram-main",
            "display_name": "Telegram Backup",
            "provider": "telegram",
            "enabled": True,
            "actor": "test-admin",
        },
    )
    assert duplicate.status_code == 400
    assert "duplicate channel key" in duplicate.json()["detail"]

    updated = admin_client.put(
        f"/api/v1/admin/channels/{channel_id}",
        json={
            "display_name": "Telegram Main Updated",
            "allowed_user_ids": ["10086"],
            "metadata_updates": {"region": "cn"},
            "actor": "test-admin",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["display_name"] == "Telegram Main Updated"

    deactivated = admin_client.post(
        f"/api/v1/admin/channels/{channel_id}/deactivate",
        json={"actor": "test-admin"},
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"
    assert deactivated.json()["version"] == 3

    history = admin_client.get(f"/api/v1/admin/channels/{channel_id}/history")
    assert history.status_code == 200
    versions = sorted(item["version"] for item in history.json())
    assert versions == [1, 2, 3]


def test_admin_channel_secret_is_encrypted(admin_client: TestClient) -> None:
    created = admin_client.post(
        "/api/v1/admin/channels",
        json={
            "key": "telegram-secret",
            "display_name": "Telegram Secret",
            "provider": "telegram",
            "secret_value": "bot-token-plain",
            "enabled": True,
            "actor": "test-admin",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    channel_id = payload["channel_id"]
    assert payload["has_secret"] is True
    assert "secret_value" not in payload

    admin_service: AdminConfigService = getattr(admin_client, "_admin_service")
    resolved = admin_service.resolve_channel_secret(channel_id)
    assert resolved == "bot-token-plain"

    cleared = admin_client.put(
        f"/api/v1/admin/channels/{channel_id}",
        json={
            "clear_secret": True,
            "actor": "test-admin",
            "reason": "rotate",
        },
    )
    assert cleared.status_code == 200
    assert cleared.json()["has_secret"] is False


def test_admin_health_endpoint(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/admin/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}
