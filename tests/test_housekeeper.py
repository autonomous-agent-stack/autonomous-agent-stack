from __future__ import annotations

import json
from pathlib import Path
import sys

from fastapi.testclient import TestClient

from autoresearch.agent_protocol.models import DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.api.dependencies import (
    get_agent_package_registry_service,
    get_approval_store_service,
    get_control_plane_service,
    get_linux_supervisor_service,
    get_manager_agent_service,
    get_openclaw_compat_service,
    get_openclaw_memory_service,
    get_personal_housekeeper_service,
    get_worker_registry_service,
)
from autoresearch.api.main import app
from autoresearch.core.services.agent_package_registry import AgentPackageRegistryService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.control_plane_service import ControlPlaneService
from autoresearch.core.services.linux_supervisor import LinuxSupervisorService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.personal_housekeeper import PersonalHousekeeperService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.housekeeper_contract import (
    HousekeeperBackendKind,
    WorkerAvailabilityStatus,
)
from autoresearch.shared.models import OpenClawMemoryRecordRead, OpenClawSessionRead
from autoresearch.shared.store import InMemoryRepository, SQLiteModelRepository


def _successful_run_summary(job: JobSpec) -> RunSummary:
    return RunSummary(
        run_id=job.run_id,
        final_status="ready_for_promotion",
        driver_result=DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status="succeeded",
            summary="software change completed",
            changed_paths=list(job.policy.allowed_paths),
            recommended_action="promote",
        ),
        validation=ValidationReport(run_id=job.run_id, passed=True),
        promotion_patch_uri="/tmp/housekeeper.patch",
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_agent_package_tree(repo_root: Path, *, linux_max_retry_count: int = 1) -> None:
    manifests = {
        "software-change": {
            "id": "software_change_agent_v0",
            "name": "Software Change Agent",
            "description": "Software changes through manager agent",
            "version": "0.1.0",
            "execution_backend": "manager_agent",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "required_capabilities": {
                "platform": ["linux"],
                "tools": ["tests"],
                "min_versions": {},
            },
            "supported_worker_types": ["linux", "openclaw"],
            "governance": {
                "risk_level": "high",
                "approval_rules": {
                    "requires_approval_for_write": True,
                    "requires_approval_for_delete": True,
                    "approval_threshold": 1,
                },
            },
            "failure_handling": {"fallback_strategy": "manual"},
            "execution": {"timeout_ms": 1000},
            "metadata": {
                "limits": {
                    "supported_scopes": [
                        "small_page_change",
                        "copy_or_config_edit",
                        "small_bug_fix",
                        "low_risk_scaffold",
                    ],
                    "clarification_markers": [
                        "新功能",
                        "feature",
                        "跨模块",
                        "cross-module",
                        "端到端",
                        "e2e",
                        "重构",
                        "refactor",
                        "schema",
                        "migration plan",
                        "multi-service",
                        "多服务",
                    ],
                    "rejection_markers": [
                        "全栈",
                        "full stack",
                        "数据库迁移",
                        "migration",
                        "schema migration",
                        "orm migration",
                        "ddl",
                        "依赖升级",
                        "upgrade",
                        "dependencies",
                        "upgrade dependency",
                        "架构升级",
                        "architecture change",
                        "architecture upgrade",
                        "大重构",
                        "large refactor",
                        "major refactor",
                        "自主审批",
                        "auto approve pr",
                        "approve pr",
                    ],
                }
            },
        },
        "linux-housekeeping": {
            "id": "linux_housekeeping_agent_v0",
            "name": "Linux Housekeeping Agent",
            "description": "Linux housekeeping through supervisor",
            "version": "0.1.0",
            "execution_backend": "linux_supervisor",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "required_capabilities": {
                "platform": ["linux"],
                "tools": ["shell"],
                "min_versions": {},
            },
            "supported_worker_types": ["linux"],
            "governance": {
                "risk_level": "medium",
                "approval_rules": {
                    "requires_approval_for_write": False,
                    "requires_approval_for_delete": False,
                    "approval_threshold": 0,
                },
                "permission_boundaries": {
                    "max_retry_count": linux_max_retry_count,
                },
            },
            "failure_handling": {"fallback_strategy": "manual"},
            "execution": {"timeout_ms": 1000},
        },
        "form-fill": {
            "id": "yingdao_form_fill_agent_v0",
            "name": "Yingdao Form Fill Agent",
            "description": "stub",
            "version": "0.1.0",
            "execution_backend": "win_yingdao",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "required_capabilities": {
                "platform": ["win_yingdao"],
                "tools": ["flow"],
                "min_versions": {},
            },
            "supported_worker_types": ["win_yingdao"],
            "governance": {
                "risk_level": "high",
                "approval_rules": {
                    "requires_approval_for_write": True,
                    "requires_approval_for_delete": True,
                    "approval_threshold": 1,
                },
            },
            "failure_handling": {"fallback_strategy": "manual"},
            "execution": {"timeout_ms": 1000},
        },
    }
    for folder, manifest in manifests.items():
        _write(
            repo_root
            / "agent-control-plane"
            / "packages"
            / "agent-packages"
            / folder
            / "manifest.json",
            json.dumps(manifest, ensure_ascii=False, indent=2),
        )


def _linux_builder(helper: Path):
    def build(task, run_dir: Path) -> list[str]:
        return [sys.executable, str(helper), str(run_dir), task.run_id]

    return build


def _linux_success_helper(path: Path) -> Path:
    _write(
        path,
        """from __future__ import annotations
import json
from pathlib import Path
import sys

run_dir = Path(sys.argv[1])
run_id = sys.argv[2]
run_dir.mkdir(parents=True, exist_ok=True)
(run_dir / "events.ndjson").write_text(json.dumps({"type": "attempt_started", "agent_id": "openhands"}) + "\\n", encoding="utf-8")
(run_dir / "progress.txt").write_text("ok\\n", encoding="utf-8")
summary = {
    "run_id": run_id,
    "final_status": "ready_for_promotion",
    "driver_result": {
        "run_id": run_id,
        "agent_id": "openhands",
        "attempt": 1,
        "status": "succeeded",
        "summary": "linux ok",
        "changed_paths": ["logs/sys.log"],
        "output_artifacts": [],
        "metrics": {},
        "recommended_action": "promote",
        "error": None
    },
    "validation": {"run_id": run_id, "passed": True, "checks": []},
    "promotion_patch_uri": None,
    "promotion_preflight": None,
    "promotion": None
}
(run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
""",
    )
    return path


def _linux_unknown_helper(path: Path) -> Path:
    _write(
        path,
        """from __future__ import annotations
import json
from pathlib import Path
import sys

run_dir = Path(sys.argv[1])
run_id = sys.argv[2]
run_dir.mkdir(parents=True, exist_ok=True)
(run_dir / "events.ndjson").write_text(json.dumps({"type": "attempt_started", "agent_id": "openhands"}) + "\\n", encoding="utf-8")
(run_dir / "progress.txt").write_text("unknown\\n", encoding="utf-8")
summary = {
    "run_id": run_id,
    "final_status": "blocked",
    "driver_result": {
        "run_id": run_id,
        "agent_id": "openhands",
        "attempt": 1,
        "status": "partial",
        "summary": "Agent could not determine outcome",
        "changed_paths": [],
        "output_artifacts": [],
        "metrics": {},
        "recommended_action": "human_review",
        "error": None
    },
    "validation": {"run_id": run_id, "passed": True, "checks": []},
    "promotion_patch_uri": None,
    "promotion_preflight": None,
    "promotion": None
}
(run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
""",
    )
    return path


def _linux_timeout_then_success_helper(path: Path) -> Path:
    _write(
        path,
        """from __future__ import annotations
import json
from pathlib import Path
import sys

run_dir = Path(sys.argv[1])
run_id = sys.argv[2]
task_root = run_dir.parent.parent
attempt_marker = task_root / "attempt-count.txt"
attempt = int(attempt_marker.read_text(encoding="utf-8")) + 1 if attempt_marker.exists() else 1
attempt_marker.write_text(str(attempt), encoding="utf-8")

run_dir.mkdir(parents=True, exist_ok=True)
(run_dir / "events.ndjson").write_text(json.dumps({"type": "attempt_started", "agent_id": "openhands", "attempt": attempt}) + "\\n", encoding="utf-8")

if attempt == 1:
    (run_dir / "progress.txt").write_text("timeout\\n", encoding="utf-8")
    summary = {
        "run_id": run_id,
        "final_status": "failed",
        "driver_result": {
            "run_id": run_id,
            "agent_id": "openhands",
            "attempt": attempt,
            "status": "timed_out",
            "summary": "Agent exceeded time limit",
            "changed_paths": [],
            "output_artifacts": [],
            "metrics": {},
            "recommended_action": "retry",
            "error": "timeout after 1800s"
        },
        "validation": {"run_id": run_id, "passed": False, "checks": []},
        "promotion_patch_uri": None,
        "promotion_preflight": None,
        "promotion": None
    }
else:
    (run_dir / "progress.txt").write_text("ok\\n", encoding="utf-8")
    summary = {
        "run_id": run_id,
        "final_status": "ready_for_promotion",
        "driver_result": {
            "run_id": run_id,
            "agent_id": "openhands",
            "attempt": attempt,
            "status": "succeeded",
            "summary": "linux ok after manual fallback approval",
            "changed_paths": ["logs/sys.log"],
            "output_artifacts": [],
            "metrics": {},
            "recommended_action": "promote",
            "error": None
        },
        "validation": {"run_id": run_id, "passed": True, "checks": []},
        "promotion_patch_uri": None,
        "promotion_preflight": None,
        "promotion": None
    }

(run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
""",
    )
    return path


def _build_services(repo_root: Path, db_path: Path, helper: Path):
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_housekeeper",
            model_cls=OpenClawSessionRead,
        )
    )
    memory_service = OpenClawMemoryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_memories_housekeeper",
            model_cls=OpenClawMemoryRecordRead,
        ),
        openclaw_service=openclaw_service,
    )
    manager_service = ManagerAgentService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
        dispatch_runner=_successful_run_summary,
    )
    linux_service = LinuxSupervisorService(
        repo_root=repo_root,
        runtime_root=repo_root / ".masfactory_runtime" / "linux-housekeeper",
        command_builder=_linux_builder(helper),
        poll_interval_sec=0.1,
        heartbeat_interval_sec=0.1,
    )
    package_registry = AgentPackageRegistryService(repo_root=repo_root)
    worker_registry = WorkerRegistryService(
        repo_root=repo_root, linux_runtime_root=linux_service.runtime_root
    )
    approval_service = ApprovalStoreService(repository=InMemoryRepository())
    control_plane_service = ControlPlaneService(
        repository=InMemoryRepository(),
        package_registry=package_registry,
        worker_registry=worker_registry,
        approval_store=approval_service,
        manager_service=manager_service,
        linux_supervisor_service=linux_service,
    )
    housekeeper_service = PersonalHousekeeperService(
        repository=InMemoryRepository(),
        openclaw_service=openclaw_service,
        openclaw_memory_service=memory_service,
        package_registry=package_registry,
        control_plane_service=control_plane_service,
    )
    return {
        "openclaw": openclaw_service,
        "memory": memory_service,
        "manager": manager_service,
        "linux": linux_service,
        "packages": package_registry,
        "workers": worker_registry,
        "approval": approval_service,
        "control": control_plane_service,
        "housekeeper": housekeeper_service,
    }


def test_agent_package_registry_loads_v0_manifests(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_agent_package_tree(repo_root)

    registry = AgentPackageRegistryService(repo_root=repo_root)
    packages = registry.list_packages()

    ids = {item.package_id for item in packages}
    assert "software_change_agent_v0" in ids
    assert "linux_housekeeping_agent_v0" in ids
    software = registry.get_package("software_change_agent_v0")
    assert software is not None
    assert software.execution_backend is HousekeeperBackendKind.MANAGER_AGENT


def test_worker_registry_exposes_openclaw_runtime_and_linux_worker(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    helper = _linux_success_helper(tmp_path / "linux_worker.py")
    linux_service = LinuxSupervisorService(
        repo_root=repo_root,
        runtime_root=repo_root / ".masfactory_runtime" / "linux-housekeeper",
        command_builder=_linux_builder(helper),
        poll_interval_sec=0.1,
        heartbeat_interval_sec=0.1,
    )
    registry = WorkerRegistryService(
        repo_root=repo_root, linux_runtime_root=linux_service.runtime_root
    )

    runtime_worker = registry.get_worker("openclaw_runtime")
    linux_worker = registry.get_worker("linux_housekeeper")

    assert runtime_worker is not None
    assert runtime_worker.backend_kind is HousekeeperBackendKind.OPENCLAW_RUNTIME
    assert runtime_worker.status is WorkerAvailabilityStatus.DEGRADED
    assert linux_worker is not None
    assert linux_worker.backend_kind is HousekeeperBackendKind.LINUX_SUPERVISOR


def test_housekeeper_api_creates_draft_then_control_plane_task_for_software_change(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper.sqlite3"
    helper = _linux_success_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)

    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_manager_agent_service] = lambda: services["manager"]
    app.dependency_overrides[get_linux_supervisor_service] = lambda: services["linux"]
    app.dependency_overrides[get_agent_package_registry_service] = lambda: services["packages"]
    app.dependency_overrides[get_worker_registry_service] = lambda: services["workers"]
    app.dependency_overrides[get_approval_store_service] = lambda: services["approval"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]

    with TestClient(app) as client:
        session = client.post(
            "/api/v1/openclaw/sessions",
            json={
                "channel": "api",
                "external_id": "sw-1",
                "title": "software",
                "scope": "personal",
                "session_key": "personal:sw-1",
                "assistant_id": "housekeeper",
                "actor": {"user_id": "42", "username": "owner", "role": "owner"},
                "metadata": {},
            },
        )
        assert session.status_code == 201
        session_id = session.json()["session_id"]

        remembered = client.post(
            f"/api/v1/openclaw/sessions/{session_id}/memory",
            json={"content": "常见任务是修页面和补测试"},
        )
        assert remembered.status_code == 201

        response = client.post(
            "/api/v1/openclaw/housekeeper/dispatch",
            json={
                "session_id": session_id,
                "message": "帮我修一个页面 bug，并补一组基础测试。",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["draft_id"] is not None
        assert payload["control_plane_task_id"] is not None
        assert payload["agent_package_id"] == "software_change_agent_v0"
        assert payload["status"] == "approval_required"
        assert payload["approval_id"] is not None
        assert services["manager"].list_dispatches() == []
        task_id = payload["task_id"]
        control_plane_task_id = payload["control_plane_task_id"]

        approved = client.post(
            f"/api/v1/openclaw/housekeeper/tasks/{task_id}/approve",
            json={"decided_by": "owner", "note": "go"},
        )
        assert approved.status_code == 200
        approved_payload = approved.json()
        assert approved_payload["status"] == "completed"
        assert approved_payload["backend_ref"] is not None

        control_task = client.get(f"/api/v1/control-plane/tasks/{control_plane_task_id}")
        assert control_task.status_code == 200
        assert control_task.json()["status"] == "completed"
        assert control_task.json()["agent_package_id"] == "software_change_agent_v0"
        assert len(services["manager"].list_dispatches()) == 1

    app.dependency_overrides.clear()


def test_housekeeper_api_dispatches_linux_task_without_approval(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper-linux.sqlite3"
    helper = _linux_success_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)

    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_manager_agent_service] = lambda: services["manager"]
    app.dependency_overrides[get_linux_supervisor_service] = lambda: services["linux"]
    app.dependency_overrides[get_agent_package_registry_service] = lambda: services["packages"]
    app.dependency_overrides[get_worker_registry_service] = lambda: services["workers"]
    app.dependency_overrides[get_approval_store_service] = lambda: services["approval"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]

    with TestClient(app) as client:
        session = client.post(
            "/api/v1/openclaw/sessions",
            json={"channel": "api", "title": "linux", "scope": "personal", "metadata": {}},
        )
        assert session.status_code == 201
        session_id = session.json()["session_id"]

        response = client.post(
            "/api/v1/openclaw/housekeeper/dispatch",
            json={
                "session_id": session_id,
                "message": "请巡检一下 Linux 服务状态并收集最近错误日志。",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["agent_package_id"] == "linux_housekeeping_agent_v0"
        assert payload["status"] == "completed"
        assert payload["approval_id"] is None
        assert payload["control_plane_task_id"] is not None

        workers = client.get("/api/v1/control-plane/workers")
        assert workers.status_code == 200
        assert any(item["worker_id"] == "openclaw_runtime" for item in workers.json())

    app.dependency_overrides.clear()


def test_housekeeper_post_run_needs_review_approval_completes_without_rerun(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper-linux-review.sqlite3"
    helper = _linux_unknown_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)

    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_manager_agent_service] = lambda: services["manager"]
    app.dependency_overrides[get_linux_supervisor_service] = lambda: services["linux"]
    app.dependency_overrides[get_agent_package_registry_service] = lambda: services["packages"]
    app.dependency_overrides[get_worker_registry_service] = lambda: services["workers"]
    app.dependency_overrides[get_approval_store_service] = lambda: services["approval"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]

    with TestClient(app) as client:
        session = client.post(
            "/api/v1/openclaw/sessions",
            json={"channel": "api", "title": "linux", "scope": "personal", "metadata": {}},
        )
        assert session.status_code == 201
        session_id = session.json()["session_id"]

        response = client.post(
            "/api/v1/openclaw/housekeeper/dispatch",
            json={
                "session_id": session_id,
                "message": "请巡检一下 Linux 服务状态并收集最近错误日志。",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "approval_required"
        assert payload["metadata"]["gate_action"] == "needs_review"
        assert payload["result_payload"]["gate_evaluation"]["gate_action"] == "needs_review"
        original_backend_ref = payload["backend_ref"]
        original_result_payload = payload["result_payload"]

        approved = client.post(
            f"/api/v1/openclaw/housekeeper/tasks/{payload['task_id']}/approve",
            json={"decided_by": "owner", "note": "accept after review"},
        )
        assert approved.status_code == 200
        approved_payload = approved.json()
        assert approved_payload["status"] == "completed"
        assert approved_payload["approval_status"] == "approved"
        assert approved_payload["backend_ref"] == original_backend_ref
        assert approved_payload["result_payload"] == original_result_payload
        assert (
            approved_payload["result_payload"]["gate_evaluation"]["gate_action"] == "needs_review"
        )
        assert approved_payload["result_payload"]["run_record"]["run_status"] == "needs_review"
        assert approved_payload["error"] is None

    app.dependency_overrides.clear()


def test_housekeeper_post_run_fallback_approval_reruns_linux_path(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper-linux-fallback.sqlite3"
    helper = _linux_timeout_then_success_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root, linux_max_retry_count=0)
    services = _build_services(repo_root, db_path, helper)

    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_manager_agent_service] = lambda: services["manager"]
    app.dependency_overrides[get_linux_supervisor_service] = lambda: services["linux"]
    app.dependency_overrides[get_agent_package_registry_service] = lambda: services["packages"]
    app.dependency_overrides[get_worker_registry_service] = lambda: services["workers"]
    app.dependency_overrides[get_approval_store_service] = lambda: services["approval"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]

    with TestClient(app) as client:
        session = client.post(
            "/api/v1/openclaw/sessions",
            json={"channel": "api", "title": "linux", "scope": "personal", "metadata": {}},
        )
        assert session.status_code == 201
        session_id = session.json()["session_id"]

        response = client.post(
            "/api/v1/openclaw/housekeeper/dispatch",
            json={
                "session_id": session_id,
                "message": "请巡检一下 Linux 服务状态并收集最近错误日志。",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "approval_required"
        assert payload["metadata"]["gate_action"] == "fallback"
        assert payload["result_payload"]["gate_evaluation"]["gate_action"] == "fallback"
        original_backend_ref = payload["backend_ref"]
        original_run_id = payload["result_payload"]["run_id"]

        approved = client.post(
            f"/api/v1/openclaw/housekeeper/tasks/{payload['task_id']}/approve",
            json={"decided_by": "owner", "note": "allow fallback rerun"},
        )
        assert approved.status_code == 200
        approved_payload = approved.json()
        assert approved_payload["status"] == "completed"
        assert approved_payload["approval_status"] == "approved"
        assert approved_payload["backend_ref"] != original_backend_ref
        assert approved_payload["result_payload"]["run_id"] != original_run_id
        assert approved_payload["result_payload"]["gate_evaluation"]["gate_action"] == "accept"
        assert approved_payload["result_payload"]["run_record"]["run_status"] == "succeeded"
        assert approved_payload["error"] is None

    app.dependency_overrides.clear()


def test_housekeeper_post_run_gated_reject_stays_rejected_without_rerun(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper-linux-reject.sqlite3"
    helper = _linux_timeout_then_success_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root, linux_max_retry_count=0)
    services = _build_services(repo_root, db_path, helper)

    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_manager_agent_service] = lambda: services["manager"]
    app.dependency_overrides[get_linux_supervisor_service] = lambda: services["linux"]
    app.dependency_overrides[get_agent_package_registry_service] = lambda: services["packages"]
    app.dependency_overrides[get_worker_registry_service] = lambda: services["workers"]
    app.dependency_overrides[get_approval_store_service] = lambda: services["approval"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]

    with TestClient(app) as client:
        session = client.post(
            "/api/v1/openclaw/sessions",
            json={"channel": "api", "title": "linux", "scope": "personal", "metadata": {}},
        )
        assert session.status_code == 201
        session_id = session.json()["session_id"]

        response = client.post(
            "/api/v1/openclaw/housekeeper/dispatch",
            json={
                "session_id": session_id,
                "message": "请巡检一下 Linux 服务状态并收集最近错误日志。",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "approval_required"
        assert payload["metadata"]["gate_action"] == "fallback"
        assert payload["result_payload"]["gate_evaluation"]["gate_action"] == "fallback"
        original_backend_ref = payload["backend_ref"]
        original_result_payload = payload["result_payload"]
        original_run_id = payload["result_payload"]["run_id"]

        rejected = client.post(
            f"/api/v1/openclaw/housekeeper/tasks/{payload['task_id']}/reject",
            json={"decided_by": "owner", "note": "reject gated fallback"},
        )
        assert rejected.status_code == 200
        rejected_payload = rejected.json()
        assert rejected_payload["status"] == "rejected"
        assert rejected_payload["approval_status"] == "rejected"
        assert rejected_payload["backend_ref"] == original_backend_ref
        assert rejected_payload["result_payload"] == original_result_payload
        assert rejected_payload["result_payload"]["run_id"] == original_run_id
        assert rejected_payload["result_payload"]["gate_evaluation"]["gate_action"] == "fallback"
        assert rejected_payload["error"] == "reject gated fallback"

    app.dependency_overrides.clear()


def test_housekeeper_returns_formal_clarification_for_unsupported_prompt(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper-unsupported.sqlite3"
    helper = _linux_success_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)

    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]

    with TestClient(app) as client:
        session = client.post(
            "/api/v1/openclaw/sessions",
            json={"channel": "api", "title": "unsupported", "scope": "personal", "metadata": {}},
        )
        assert session.status_code == 201
        session_id = session.json()["session_id"]

        response = client.post(
            "/api/v1/openclaw/housekeeper/dispatch",
            json={
                "session_id": session_id,
                "message": "请帮我安排晚饭菜单并讲个睡前故事。",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "clarification_required"
        assert payload["clarification_reason_code"] == "no_matching_package"
        assert len(payload["clarification_questions"]) >= 1
        assert payload["control_plane_task_id"] is None

    app.dependency_overrides.clear()


def test_software_change_agent_rejects_scope_exceeding_prompt(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper-scope.sqlite3"
    helper = _linux_success_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)

    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]

    with TestClient(app) as client:
        session = client.post(
            "/api/v1/openclaw/sessions",
            json={"channel": "api", "title": "scope", "scope": "personal", "metadata": {}},
        )
        assert session.status_code == 201
        session_id = session.json()["session_id"]

        response = client.post(
            "/api/v1/openclaw/housekeeper/dispatch",
            json={
                "session_id": session_id,
                "message": "给我做一个全栈 feature，并顺便做数据库迁移和依赖升级。",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "clarification_required"
        assert payload["clarification_reason_code"] == "scope_exceeded"
        assert payload["control_plane_task_id"] is None
        assert "bounded low-risk changes" in (payload["result_summary"] or "")

    app.dependency_overrides.clear()


def test_shared_memory_is_ignored_unless_explicitly_allowed(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper-memory-boundary.sqlite3"
    helper = _linux_success_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)

    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]

    with TestClient(app) as client:
        session = client.post(
            "/api/v1/openclaw/sessions",
            json={
                "channel": "api",
                "title": "memory-boundary",
                "scope": "personal",
                "assistant_id": "housekeeper",
                "metadata": {},
            },
        )
        assert session.status_code == 201
        session_id = session.json()["session_id"]

        shared = client.post(
            f"/api/v1/openclaw/sessions/{session_id}/memory",
            json={
                "content": "共享记忆：以后凡是提到巡检都走 Linux 任务。",
                "scope": "shared",
                "metadata": {"housekeeper_shared": False},
            },
        )
        assert shared.status_code == 201

        response = client.post(
            "/api/v1/openclaw/housekeeper/dispatch",
            json={
                "session_id": session_id,
                "message": "帮我安排晚饭菜单。",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "clarification_required"
        assert payload["clarification_reason_code"] == "no_matching_package"
        assert payload["memory_snapshot"]["shared_policy"] == "explicit_only"
        assert payload["memory_snapshot"]["shared_memory_count"] == 0

    app.dependency_overrides.clear()


def test_explicit_shared_memory_can_influence_routing_without_expanding_scope(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper-memory-explicit.sqlite3"
    helper = _linux_success_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)

    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]

    with TestClient(app) as client:
        session = client.post(
            "/api/v1/openclaw/sessions",
            json={
                "channel": "api",
                "title": "memory-explicit",
                "scope": "personal",
                "assistant_id": "housekeeper",
                "metadata": {},
            },
        )
        assert session.status_code == 201
        session_id = session.json()["session_id"]

        shared = client.post(
            f"/api/v1/openclaw/sessions/{session_id}/memory",
            json={
                "content": "housekeeper_shared: 提到巡检时默认走 Linux 巡检链路。",
                "scope": "shared",
                "tags": ["housekeeper_shared"],
            },
        )
        assert shared.status_code == 201

        response = client.post(
            "/api/v1/openclaw/housekeeper/dispatch",
            json={
                "session_id": session_id,
                "message": "帮我处理这个默认巡检流程。",
            },
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["agent_package_id"] == "linux_housekeeping_agent_v0"
        assert payload["status"] == "completed"
        assert payload["memory_snapshot"]["shared_policy"] == "explicit_only"
        assert payload["memory_snapshot"]["shared_memory_count"] == 1

    app.dependency_overrides.clear()
