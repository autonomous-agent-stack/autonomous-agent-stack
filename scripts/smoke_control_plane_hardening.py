#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
from typing import Any
from urllib.parse import parse_qs, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from fastapi.testclient import TestClient

from autoresearch.agent_protocol.models import DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.api import dependencies
from autoresearch.api.main import app
from autoresearch.api.routers import gateway_telegram
from autoresearch.core.adapters import CapabilityProviderRegistry
from autoresearch.core.services.admin_auth import AdminAuthService
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.agent_audit_trail import AgentAuditTrailService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.panel_audit import PanelAuditService
from autoresearch.shared.models import PromotionDiffStats, PromotionResult, utc_now
from autoresearch.shared.store import InMemoryRepository


class _StubTelegramNotifier:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

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

    def notify_manual_action(self, **_: object) -> bool:
        return True


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_patch(repo_root: Path, *, run_id: str, changed_paths: list[str]) -> Path:
    patch_dir = repo_root / ".masfactory_runtime" / "smokes" / run_id / "artifacts"
    patch_dir.mkdir(parents=True, exist_ok=True)
    patch_path = patch_dir / "promotion.patch"
    changed_path = changed_paths[0] if changed_paths else "src/demo.py"
    patch_path.write_text(
        "\n".join(
            [
                f"diff --git a/{changed_path} b/{changed_path}",
                f"--- a/{changed_path}",
                f"+++ b/{changed_path}",
                "@@ -1 +1 @@",
                "+CONTROL_PLANE_SMOKE = True",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return patch_path


def _planner_dispatch_runner_factory(repo_root: Path):
    def _dispatch_runner(job: JobSpec) -> RunSummary:
        changed_paths = list(job.policy.allowed_paths) or ["src/autoresearch/core/services/control_plane_target.py"]
        patch_path = _write_patch(repo_root, run_id=job.run_id, changed_paths=changed_paths)
        return RunSummary(
            run_id=job.run_id,
            final_status="ready_for_promotion",
            driver_result=DriverResult(
                run_id=job.run_id,
                agent_id=job.agent_id,
                status="succeeded",
                summary="planner fallback lane completed",
                changed_paths=changed_paths,
                recommended_action="promote",
            ),
            validation=ValidationReport(run_id=job.run_id, passed=True),
            promotion_patch_uri=str(patch_path),
        )

    return _dispatch_runner


def _manager_dispatch_runner_factory(repo_root: Path):
    def _dispatch_runner(job: JobSpec) -> RunSummary:
        changed_paths = list(job.policy.allowed_paths) or ["src/autoresearch/api/routers/admin.py"]
        patch_path = _write_patch(repo_root, run_id=job.run_id, changed_paths=changed_paths)
        promotion = PromotionResult(
            run_id=job.run_id,
            success=True,
            mode="draft_pr",
            pr_url=f"https://example.invalid/pr/{job.run_id[-6:]}",
            changed_files=changed_paths,
            diff_stats=PromotionDiffStats(files_changed=len(changed_paths), insertions=12, deletions=2),
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        return RunSummary(
            run_id=job.run_id,
            final_status="ready_for_promotion",
            driver_result=DriverResult(
                run_id=job.run_id,
                agent_id=job.agent_id,
                status="succeeded",
                summary="manager smoke dispatch completed",
                changed_paths=changed_paths,
                recommended_action="promote",
            ),
            validation=ValidationReport(run_id=job.run_id, passed=True),
            promotion_patch_uri=str(patch_path),
            promotion=promotion,
        )

    return _dispatch_runner


def _extract_panel_token(url: str) -> str:
    parsed = urlparse(url)
    return parse_qs(parsed.query)["token"][0]


def _build_services(repo_root: Path) -> dict[str, object]:
    notifier = _StubTelegramNotifier()
    openclaw_service = OpenClawCompatService(repository=InMemoryRepository())
    claude_service = ClaudeAgentService(
        repository=InMemoryRepository(),
        openclaw_service=openclaw_service,
        repo_root=repo_root,
        max_agents=10,
        max_depth=3,
    )
    planner_service = AutoResearchPlannerService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
        dispatch_runner=_planner_dispatch_runner_factory(repo_root),
    )
    manager_service = ManagerAgentService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
        dispatch_runner=_manager_dispatch_runner_factory(repo_root),
    )
    audit_service = AgentAuditTrailService(
        repo_root=repo_root,
        planner_service=planner_service,
        manager_service=manager_service,
        agent_service=claude_service,
    )
    panel_access = PanelAccessService(
        secret="panel-secret",
        telegram_bot_token="123456:TEST_BOT_TOKEN",
        telegram_init_data_max_age_seconds=900,
        base_url="https://panel.example/api/v1/panel/view",
        mini_app_url="https://panel.example/api/v1/panel/view",
        allowed_uids={"10001"},
    )
    panel_audit = PanelAuditService(repository=InMemoryRepository())
    approval_store = ApprovalStoreService(repository=InMemoryRepository())
    openclaw_memory = OpenClawMemoryService(repository=InMemoryRepository(), openclaw_service=openclaw_service)
    admin_config = AdminConfigService(
        agent_repository=InMemoryRepository(),
        channel_repository=InMemoryRepository(),
        revision_repository=InMemoryRepository(),
    )
    admin_auth = AdminAuthService(secret="admin-smoke-secret", bootstrap_key="bootstrap-smoke-key")
    capability_registry = CapabilityProviderRegistry()
    return {
        "notifier": notifier,
        "openclaw_service": openclaw_service,
        "claude_service": claude_service,
        "planner_service": planner_service,
        "manager_service": manager_service,
        "audit_service": audit_service,
        "panel_access": panel_access,
        "panel_audit": panel_audit,
        "approval_store": approval_store,
        "openclaw_memory": openclaw_memory,
        "admin_config": admin_config,
        "admin_auth": admin_auth,
        "capability_registry": capability_registry,
    }


def _install_overrides(services: dict[str, object]) -> None:
    app.dependency_overrides[dependencies.get_telegram_notifier_service] = lambda: services["notifier"]
    app.dependency_overrides[dependencies.get_openclaw_compat_service] = lambda: services["openclaw_service"]
    app.dependency_overrides[dependencies.get_claude_agent_service] = lambda: services["claude_service"]
    app.dependency_overrides[dependencies.get_autoresearch_planner_service] = lambda: services["planner_service"]
    app.dependency_overrides[dependencies.get_manager_agent_service] = lambda: services["manager_service"]
    app.dependency_overrides[dependencies.get_panel_access_service] = lambda: services["panel_access"]
    app.dependency_overrides[dependencies.get_panel_audit_service] = lambda: services["panel_audit"]
    app.dependency_overrides[dependencies.get_approval_store_service] = lambda: services["approval_store"]
    app.dependency_overrides[dependencies.get_openclaw_memory_service] = lambda: services["openclaw_memory"]
    app.dependency_overrides[dependencies.get_admin_config_service] = lambda: services["admin_config"]
    app.dependency_overrides[dependencies.get_admin_auth_service] = lambda: services["admin_auth"]
    app.dependency_overrides[dependencies.get_agent_audit_trail_service] = lambda: services["audit_service"]
    app.dependency_overrides[dependencies.get_capability_provider_registry] = lambda: services["capability_registry"]


def _run_planner_panel_smoke(client: TestClient, services: dict[str, object], repo_root: Path) -> dict[str, Any]:
    _write(
        repo_root / "src" / "autoresearch" / "core" / "services" / "control_plane_target.py",
        "\n".join(
            [
                "def control_plane_target() -> bool:",
                "    # FIXME: cover the remote fallback control-plane flow",
                "    return True",
                "",
            ]
        ),
    )

    create_response = client.post(
        "/api/v1/autoresearch/plans",
        json={
            "goal": "Smoke the offline control plane fallback path.",
            "telegram_uid": "10001",
            "metadata": {
                "runtime_mode": "night",
                "remote_available": False,
            },
        },
    )
    assert create_response.status_code == 202, create_response.text
    plan_payload = create_response.json()
    plan_id = plan_payload["plan_id"]

    panel_access = services["panel_access"]
    assert isinstance(panel_access, PanelAccessService)
    token = _extract_panel_token(panel_access.create_magic_link("10001").url)
    headers = {"x-autoresearch-panel-token": token}

    state_before = client.get("/api/v1/panel/state", headers=headers)
    assert state_before.status_code == 200, state_before.text
    pending_plans = state_before.json()["pending_autoresearch_plans"]
    assert len(pending_plans) == 1
    assert pending_plans[0]["plan_id"] == plan_id

    dispatch_response = client.post(
        f"/api/v1/panel/autoresearch/plans/{plan_id}/dispatch",
        headers=headers,
        json={"note": "smoke dispatch", "metadata": {"source": "smoke"}},
    )
    assert dispatch_response.status_code == 200, dispatch_response.text
    queued_payload = dispatch_response.json()
    assert queued_payload["dispatch_status"] == "dispatching"
    assert queued_payload["dispatch_run"]["status"] == "queued"
    assert queued_payload["dispatch_run"]["requested_lane"] == "remote"
    assert queued_payload["dispatch_run"]["lane"] == "local"

    plan_after = client.get(f"/api/v1/autoresearch/plans/{plan_id}")
    assert plan_after.status_code == 200, plan_after.text
    dispatched_payload = plan_after.json()
    assert dispatched_payload["dispatch_status"] == "dispatched"
    assert dispatched_payload["dispatch_run"]["requested_lane"] == "remote"
    assert dispatched_payload["dispatch_run"]["lane"] == "local"
    assert dispatched_payload["dispatch_run"]["status"] == "succeeded"
    assert dispatched_payload["dispatch_run"]["fallback_reason"]
    assert dispatched_payload["run_summary"]["final_status"] == "ready_for_promotion"
    assert dispatched_payload["dispatch_error"] is None

    summary_relpath = dispatched_payload["dispatch_run"]["artifact_paths"]["summary"]
    summary_path = repo_root / summary_relpath
    assert summary_path.exists(), summary_path

    state_after = client.get("/api/v1/panel/state", headers=headers)
    assert state_after.status_code == 200, state_after.text
    assert state_after.json()["pending_autoresearch_plans"] == []

    notifier = services["notifier"]
    assert isinstance(notifier, _StubTelegramNotifier)
    dispatch_messages = [
        message for message in notifier.messages if "[AutoResearch Dispatch]" in str(message["text"])
    ]
    assert dispatch_messages, notifier.messages
    latest_dispatch_message = str(dispatch_messages[-1]["text"])
    assert "- lane: local" in latest_dispatch_message
    assert "- remote_status: succeeded" in latest_dispatch_message
    assert "- final_status: ready_for_promotion" in latest_dispatch_message

    return {
        "plan_id": plan_id,
        "requested_lane": dispatched_payload["dispatch_run"]["requested_lane"],
        "lane": dispatched_payload["dispatch_run"]["lane"],
        "remote_status": dispatched_payload["dispatch_run"]["status"],
        "dispatch_status": dispatched_payload["dispatch_status"],
        "final_status": dispatched_payload["run_summary"]["final_status"],
        "fallback_reason": dispatched_payload["dispatch_run"]["fallback_reason"],
        "summary_artifact": summary_relpath,
    }


def _run_gateway_regression_smoke(client: TestClient, services: dict[str, object]) -> dict[str, Any]:
    gateway_telegram._SEEN_UPDATES.clear()
    gateway_telegram._CHAT_RATE_WINDOWS.clear()

    response = client.post(
        "/api/v1/gateway/telegram/webhook",
        json={
            "update_id": 99001,
            "message": {
                "message_id": 501,
                "text": "/task 为美妆品牌玛露开发 6g 遮瑕膏落地页",
                "chat": {"id": 10001, "type": "private"},
                "from": {"id": 10001, "username": "control-plane-smoke"},
            },
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["metadata"]["source"] == "telegram_manager_task"
    dispatch_id = payload["metadata"]["dispatch_id"]

    manager_service = services["manager_service"]
    assert isinstance(manager_service, ManagerAgentService)
    dispatch = manager_service.get_dispatch(dispatch_id)
    assert dispatch is not None
    assert dispatch.status.value == "completed"
    assert dispatch.run_summary is not None
    assert dispatch.run_summary.final_status == "ready_for_promotion"

    return {
        "dispatch_id": dispatch_id,
        "status": dispatch.status.value,
        "final_status": dispatch.run_summary.final_status,
    }


def _run_admin_audit_smoke(
    client: TestClient,
    services: dict[str, object],
    planner_result: dict[str, Any],
    gateway_result: dict[str, Any],
) -> dict[str, Any]:
    admin_auth = services["admin_auth"]
    assert isinstance(admin_auth, AdminAuthService)
    admin_token = admin_auth.issue_token(
        subject="control-plane-smoke",
        roles=["owner"],
        bootstrap_key="bootstrap-smoke-key",
        ttl_seconds=3600,
    ).token
    headers = {"authorization": f"Bearer {admin_token}"}

    snapshot_response = client.get("/api/v1/admin/audit-trail?limit=20", headers=headers)
    assert snapshot_response.status_code == 200, snapshot_response.text
    snapshot = snapshot_response.json()
    planner_item = next(item for item in snapshot["items"] if item["source"] == "autoresearch_plan")
    manager_item = next(item for item in snapshot["items"] if item["source"] == "manager_task")

    assert planner_item["status"] == planner_result["dispatch_status"]
    assert planner_item["final_status"] == planner_result["final_status"]
    assert planner_item["metadata"]["dispatch_requested_lane"] == planner_result["requested_lane"]
    assert planner_item["metadata"]["dispatch_lane"] == planner_result["lane"]
    assert planner_item["metadata"]["dispatch_remote_status"] == planner_result["remote_status"]
    assert planner_item["metadata"]["dispatch_fallback_reason"] == planner_result["fallback_reason"]
    assert manager_item["entry_id"].startswith("manager:")
    assert manager_item["final_status"] == gateway_result["final_status"]

    detail_response = client.get(
        f"/api/v1/admin/audit-trail/{planner_item['entry_id']}",
        headers=headers,
    )
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    raw_plan = detail["raw_record"]["autoresearch_plan"]
    assert raw_plan["dispatch_status"] == planner_result["dispatch_status"]
    assert raw_plan["dispatch_run"]["status"] == planner_result["remote_status"]
    assert raw_plan["dispatch_run"]["lane"] == planner_result["lane"]
    assert raw_plan["run_summary"]["final_status"] == planner_result["final_status"]

    return {
        "planner_entry_id": planner_item["entry_id"],
        "manager_entry_id": manager_item["entry_id"],
        "planner_dispatch_lane": planner_item["metadata"]["dispatch_lane"],
        "planner_remote_status": planner_item["metadata"]["dispatch_remote_status"],
    }


def _print_report(results: dict[str, Any]) -> None:
    print("control-plane-hardening smoke: PASS")
    print(
        "planner/panel: "
        f"plan={results['planner']['plan_id']} "
        f"requested={results['planner']['requested_lane']} "
        f"lane={results['planner']['lane']} "
        f"remote_status={results['planner']['remote_status']} "
        f"dispatch_status={results['planner']['dispatch_status']} "
        f"final_status={results['planner']['final_status']}"
    )
    print(
        "gateway/task: "
        f"dispatch={results['gateway']['dispatch_id']} "
        f"status={results['gateway']['status']} "
        f"final_status={results['gateway']['final_status']}"
    )
    print(
        "admin/audit: "
        f"planner_entry={results['admin']['planner_entry_id']} "
        f"manager_entry={results['admin']['manager_entry_id']} "
        f"dispatch_lane={results['admin']['planner_dispatch_lane']} "
        f"remote_status={results['admin']['planner_remote_status']}"
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="control-plane-smoke-") as temp_dir:
        repo_root = Path(temp_dir) / "repo"
        repo_root.mkdir(parents=True, exist_ok=True)
        services = _build_services(repo_root)
        _install_overrides(services)
        previous_allowed = os.environ.get("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS")
        os.environ["AUTORESEARCH_TELEGRAM_ALLOWED_UIDS"] = "10001"
        try:
            with TestClient(app) as client:
                planner_result = _run_planner_panel_smoke(client, services, repo_root)
                gateway_result = _run_gateway_regression_smoke(client, services)
                admin_result = _run_admin_audit_smoke(client, services, planner_result, gateway_result)
        finally:
            if previous_allowed is None:
                os.environ.pop("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", None)
            else:
                os.environ["AUTORESEARCH_TELEGRAM_ALLOWED_UIDS"] = previous_allowed
            app.dependency_overrides.clear()

    _print_report(
        {
            "planner": planner_result,
            "gateway": gateway_result,
            "admin": admin_result,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
