from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.agent_protocol.models import DriverMetrics, DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.api.dependencies import (
    get_admin_auth_service,
    get_admin_config_service,
    get_agent_audit_trail_service,
    get_approval_store_service,
    get_autoresearch_planner_service,
    get_capability_provider_registry,
    get_claude_agent_service,
    get_manager_agent_service,
    get_openclaw_compat_service,
)
from autoresearch.api.main import app
from autoresearch.core.adapters import CapabilityProviderDescriptorRead, CapabilityProviderRegistry
from autoresearch.core.adapters.contracts import CapabilityDomain
from autoresearch.core.services.admin_auth import AdminAuthService
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.admin_secrets import AdminSecretCipher
from autoresearch.core.services.agent_audit_trail import AgentAuditTrailService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.autoresearch_planner_contract import AutoResearchPlannerRequest
from autoresearch.shared.manager_agent_contract import ManagerDispatchRequest
from autoresearch.shared.models import (
    AdminAgentConfigRead,
    AdminChannelConfigRead,
    AdminConfigRevisionRead,
    AdminSecretRecordRead,
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    OpenClawSessionRead,
)
from autoresearch.shared.store import InMemoryRepository, SQLiteModelRepository


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


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _successful_run_summary(job: JobSpec) -> RunSummary:
    patch_path = Path("/tmp") / f"{job.run_id}.patch"
    patch_path.write_text(
        "\n".join(
            [
                "diff --git a/src/demo.py b/src/demo.py",
                "--- a/src/demo.py",
                "+++ b/src/demo.py",
                "@@ -1 +1 @@",
                "+VALUE = 'READY_FOR_PROMOTION'",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return RunSummary(
        run_id=job.run_id,
        final_status="ready_for_promotion",
        driver_result=DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status="succeeded",
            summary="admin audit flow completed successfully",
            changed_paths=list(job.policy.allowed_paths),
            metrics=DriverMetrics(
                duration_ms=1800,
                steps=3,
                commands=2,
                first_progress_ms=300,
                first_scoped_write_ms=900,
                first_state_heartbeat_ms=300,
            ),
            recommended_action="promote",
        ),
        validation=ValidationReport(run_id=job.run_id, passed=True),
        promotion_patch_uri=str(patch_path),
    )


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
    planner_service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=tmp_path,
        dispatch_runner=_successful_run_summary,
    )
    manager_service = ManagerAgentService(
        repository=InMemoryRepository(),
        repo_root=tmp_path,
        dispatch_runner=_successful_run_summary,
    )
    audit_trail_service = AgentAuditTrailService(
        repo_root=tmp_path,
        planner_service=planner_service,
        manager_service=manager_service,
        agent_service=claude_service,
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
    app.dependency_overrides[get_autoresearch_planner_service] = lambda: planner_service
    app.dependency_overrides[get_manager_agent_service] = lambda: manager_service
    app.dependency_overrides[get_agent_audit_trail_service] = lambda: audit_trail_service
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
        setattr(client, "_planner_service", planner_service)
        setattr(client, "_manager_service", manager_service)
        setattr(client, "_claude_service", claude_service)
        setattr(client, "_repo_root", tmp_path)
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
    denied_audit = admin_client.get("/api/v1/admin/audit-trail")
    assert denied_audit.status_code == 401
    if existing is not None:
        admin_client.headers["authorization"] = existing


def test_admin_view_contains_capability_inventory_section(admin_client: TestClient) -> None:
    response = admin_client.get("/api/v1/admin/view")

    assert response.status_code == 200
    assert "Capability Inventory" in response.text
    assert "Agent Audit Trail" in response.text
    assert "Approval Queue" in response.text
    assert "Managed Skill Queue" in response.text
    assert "/api/v1/admin/audit-trail" in response.text
    assert "loadAuditDetail" in response.text
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


def test_admin_audit_trail_lists_recent_worker_activity(admin_client: TestClient) -> None:
    repo_root: Path = getattr(admin_client, "_repo_root")
    planner_service: AutoResearchPlannerService = getattr(admin_client, "_planner_service")
    manager_service: ManagerAgentService = getattr(admin_client, "_manager_service")
    claude_service: ClaudeAgentService = getattr(admin_client, "_claude_service")

    _write(
        repo_root / "src" / "autoresearch" / "core" / "services" / "audit_target.py",
        "def collect_audit_events() -> bool:\n    # FIXME: add audit timeline regression coverage\n    return True\n",
    )
    _write(repo_root / "tests" / "test_audit_target.py", "def test_collect_audit_events():\n    assert True\n")
    _write(repo_root / "panel" / "app.tsx", "export const App = () => null;\n")
    _write(repo_root / "src" / "autoresearch" / "api" / "routers" / "admin.py", "router = object()\n")
    _write(repo_root / "src" / "autoresearch" / "api" / "routers" / "panel.py", "router = object()\n")
    _write(repo_root / "tests" / "test_panel_security.py", "def test_panel_ok():\n    assert True\n")
    _write(repo_root / "tests" / "test_admin_managed_skills.py", "def test_admin_ok():\n    assert True\n")

    plan = planner_service.create(
        AutoResearchPlannerRequest(goal="Find the next audit trail hardening task.")
    )
    planner_service.request_dispatch(plan.plan_id, requested_by="admin-ui")
    planner_service.execute_dispatch(plan.plan_id)

    dispatch = manager_service.create_dispatch(
        ManagerDispatchRequest(
            prompt="在 Admin Panel 里加一个带图表的智能体行为审计大屏。",
            auto_dispatch=False,
        )
    )
    manager_service.execute_dispatch(dispatch.dispatch_id)

    claude_service.create(
        ClaudeAgentCreateRequest(
            task_name="audit reviewer",
            prompt="Inspect the latest worker execution traces.",
            command_override=[sys.executable, "-c", "print('audit-review')"],
            append_prompt=False,
            metadata={
                "allowed_paths": ["src/autoresearch/api/routers/admin.py"],
                "changed_paths": ["src/autoresearch/api/routers/admin.py"],
            },
        )
    )

    runtime_summary_path = (
        repo_root / ".masfactory_runtime" / "smokes" / "audit-smoke" / "artifacts" / "chain_summary.json"
    )
    runtime_summary_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_patch_path = runtime_summary_path.parent / "promotion.patch"
    runtime_patch_path.write_text(
        "\n".join(
            [
                "diff --git a/src/autoresearch/api/routers/admin.py b/src/autoresearch/api/routers/admin.py",
                "--- a/src/autoresearch/api/routers/admin.py",
                "+++ b/src/autoresearch/api/routers/admin.py",
                "@@ -1 +1 @@",
                "+AUDIT_TRAIL = True",
                "",
            ]
        ),
        encoding="utf-8",
    )
    runtime_summary_path.write_text(
        json.dumps(
            {
                "run_id": "runtime-audit-001",
                "status": "ready_for_promotion",
                "task": "Rebuild audit trail timeline",
                "isolated_workspace": "/tmp/audit-runtime",
                "driver_result": {
                    "agent_id": "openhands",
                    "summary": "runtime artifact captured successfully",
                    "changed_paths": ["src/autoresearch/api/routers/admin.py"],
                    "metrics": {
                        "duration_ms": 2400,
                        "first_progress_ms": 700,
                        "first_scoped_write_ms": 1100,
                        "first_state_heartbeat_ms": 700,
                    },
                },
                "promotion": {
                    "changed_files": ["src/autoresearch/api/routers/admin.py"],
                    "diff_stats": {"files_changed": 1},
                    "patch_uri": str(runtime_patch_path),
                },
            }
        ),
        encoding="utf-8",
    )

    failed_runtime_path = (
        repo_root / "logs" / "audit" / "openhands" / "jobs" / "audit-failed-001" / "chain_summary.json"
    )
    failed_runtime_path.parent.mkdir(parents=True, exist_ok=True)
    failed_patch_path = failed_runtime_path.parent / "promotion.patch"
    failed_patch_path.write_text(
        "\n".join(
            [
                "diff --git a/src/autoresearch/core/services/agent_audit_trail.py b/src/autoresearch/core/services/agent_audit_trail.py",
                "--- a/src/autoresearch/core/services/agent_audit_trail.py",
                "+++ b/src/autoresearch/core/services/agent_audit_trail.py",
                "@@ -1 +1 @@",
                "+BROKEN = True",
                "",
            ]
        ),
        encoding="utf-8",
    )
    failed_runtime_path.write_text(
        json.dumps(
            {
                "run_id": "runtime-audit-failed-001",
                "status": "failed",
                "task": "Patch audit trail filters",
                "error": "validation command failed",
                "traceback": "Traceback (most recent call last):\\nValueError: missing token",
                "artifacts": {"promotion_patch": str(failed_patch_path)},
                "driver_result": {
                    "agent_id": "openhands",
                    "summary": "worker failed during validation",
                    "changed_paths": ["src/autoresearch/core/services/agent_audit_trail.py"],
                    "metrics": {
                        "duration_ms": 3200,
                        "first_progress_ms": 600,
                        "first_scoped_write_ms": 1600,
                        "first_state_heartbeat_ms": 600,
                    },
                    "error": "pytest exited with code 1",
                },
            }
        ),
        encoding="utf-8",
    )

    response = admin_client.get("/api/v1/admin/audit-trail?limit=20")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stats"]["total"] >= 5
    assert payload["stats"]["queued"] >= 1
    assert payload["stats"]["succeeded"] >= 2
    assert payload["stats"]["failed"] >= 1
    sources = {item["source"] for item in payload["items"]}
    assert {"manager_task", "autoresearch_plan", "claude_agent", "runtime_artifact"} <= sources

    planner_item = next(item for item in payload["items"] if item["source"] == "autoresearch_plan")
    assert planner_item["final_status"] == "ready_for_promotion"
    assert planner_item["status"] == "dispatched"
    assert "tests/test_audit_target.py" in planner_item["scope_paths"]
    assert planner_item["first_progress_ms"] == 300
    assert planner_item["first_scoped_write_ms"] == 900
    assert planner_item["first_state_heartbeat_ms"] == 300

    manager_backend = next(
        item
        for item in payload["items"]
        if item["source"] == "manager_task" and item["metadata"]["stage"] == "backend"
    )
    assert manager_backend["final_status"] == "ready_for_promotion"
    assert "src/autoresearch/api/routers/admin.py" in manager_backend["scope_paths"]

    runtime_item = next(
        item
        for item in payload["items"]
        if item["source"] == "runtime_artifact" and item["run_id"] == "runtime-audit-001"
    )
    assert runtime_item["isolated_workspace"] == "/tmp/audit-runtime"
    assert runtime_item["patch_uri"] == str(runtime_patch_path)
    assert runtime_item["agent_role"] == "worker"
    assert runtime_item["first_progress_ms"] == 700
    assert runtime_item["first_scoped_write_ms"] == 1100
    assert runtime_item["first_state_heartbeat_ms"] == 700

    detail_response = admin_client.get(f"/api/v1/admin/audit-trail/{planner_item['entry_id']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["input_prompt"] == "Find the next audit trail hardening task."
    assert detail_payload["job_spec"]["task"] != ""
    assert "diff --git" in detail_payload["patch_text"]
    assert detail_payload["patch_truncated"] is False
    assert detail_payload["entry"]["first_progress_ms"] == 300

    failed_response = admin_client.get("/api/v1/admin/audit-trail?limit=20&status_filter=failed&agent_role=worker")
    assert failed_response.status_code == 200
    failed_items = failed_response.json()["items"]
    assert len(failed_items) == 1
    assert failed_items[0]["run_id"] == "runtime-audit-failed-001"

    failed_detail = admin_client.get(f"/api/v1/admin/audit-trail/{failed_items[0]['entry_id']}")
    assert failed_detail.status_code == 200
    failed_detail_payload = failed_detail.json()
    assert failed_detail_payload["error_reason"] == "validation command failed"
    assert "Traceback" in (failed_detail_payload["traceback"] or "")
    assert "diff --git" in failed_detail_payload["patch_text"]
    assert failed_detail_payload["entry"]["first_progress_ms"] == 600


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
