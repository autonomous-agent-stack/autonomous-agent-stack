"""Integration tests: real Linux execution produces unified run lifecycle data.

These tests prove that after a real Linux task executes through the control
plane, ``result_payload`` contains a ``run_record`` dict whose status, timing,
and result data stay consistent with the bridge mapping, ``gate_evaluation``,
and the original supervisor summary fields.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.agent_package_registry import AgentPackageRegistryService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.control_plane_service import ControlPlaneService
from autoresearch.core.services.linux_supervisor import LinuxSupervisorService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.housekeeper_contract import (
    HousekeeperTaskDraftRead,
    HousekeeperTaskStatus,
)
from autoresearch.shared.models import utc_now
from autoresearch.shared.store import InMemoryRepository

from autoresearch.agent_protocol.models import DriverResult, RunSummary, ValidationReport

# ---------------------------------------------------------------------------
# Helpers (reuse patterns from test_linux_gate_integration.py)
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_agent_package_tree(repo_root: Path) -> None:
    manifest = {
        "id": "linux_housekeeping_agent_v0",
        "name": "Linux Housekeeping Agent",
        "description": "Linux housekeeping through supervisor",
        "version": "0.1.0",
        "execution_backend": "linux_supervisor",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "required_capabilities": {"platform": ["linux"], "tools": ["shell"], "min_versions": {}},
        "supported_worker_types": ["linux"],
        "governance": {
            "risk_level": "medium",
            "approval_rules": {
                "requires_approval_for_write": False,
                "requires_approval_for_delete": False,
                "approval_threshold": 0,
            },
        },
        "failure_handling": {"fallback_strategy": "manual"},
        "execution": {"timeout_ms": 1000},
    }
    _write(
        repo_root
        / "agent-control-plane"
        / "packages"
        / "agent-packages"
        / "linux-housekeeping"
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


def _linux_timeout_helper(path: Path) -> Path:
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
(run_dir / "progress.txt").write_text("timeout\\n", encoding="utf-8")
summary = {
    "run_id": run_id,
    "final_status": "failed",
    "driver_result": {
        "run_id": run_id,
        "agent_id": "openhands",
        "attempt": 1,
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
(run_dir / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
""",
    )
    return path


def _linux_infra_error_helper(path: Path) -> Path:
    _write(
        path,
        """from __future__ import annotations
from pathlib import Path
import sys

run_dir = Path(sys.argv[1])
run_dir.mkdir(parents=True, exist_ok=True)
(run_dir / "progress.txt").write_text("error\\n", encoding="utf-8")
sys.exit(1)
""",
    )
    return path


def _linux_unknown_helper(path: Path) -> Path:
    """Helper that exits 0 but with a conclusion that doesn't match any known good path.

    _classify_summary cascade: no forced_conclusion, run_summary exists,
    driver_result.status not in {timed_out, stalled_no_progress, contract_error},
    no mock fallback, no assertion failure, final_status not ready_for_promotion,
    returncode 0 → falls through to UNKNOWN.
    """

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


def _build_services(repo_root: Path, helper: Path):
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
    manager_service = ManagerAgentService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
        dispatch_runner=lambda job: RunSummary(
            run_id=job.run_id,
            final_status="ready_for_promotion",
            driver_result=DriverResult(
                run_id=job.run_id,
                agent_id=job.agent_id,
                status="succeeded",
                summary="ok",
            ),
            validation=ValidationReport(run_id=job.run_id, passed=True),
        ),
    )
    control_plane_service = ControlPlaneService(
        repository=InMemoryRepository(),
        package_registry=package_registry,
        worker_registry=worker_registry,
        approval_store=approval_service,
        manager_service=manager_service,
        linux_supervisor_service=linux_service,
    )
    return {
        "control": control_plane_service,
    }


def _dispatch(services, message: str):
    cp = services["control"]
    now = utc_now()
    draft = HousekeeperTaskDraftRead(
        draft_id="draft-run-001",
        session_id="session-run-001",
        source_message=message,
        candidate_package_ids=["linux_housekeeping_agent_v0"],
        routing_reason="run_lifecycle_test",
        created_at=now,
    )
    return cp.submit_housekeeper_draft(draft, housekeeper_task_id="ht-run-001", dry_run=False)


# ===================================================================
# Tests
# ===================================================================


class TestLinuxRunLifecycleIntegration:
    """Prove that the production Linux path emits a consistent ``run_record``."""

    def test_success_produces_run_status_succeeded(self, tmp_path: Path):
        """SUCCEEDED conclusion → run_record.run_status == "succeeded"."""
        repo_root = tmp_path / "repo"
        helper = _linux_success_helper(tmp_path / "success.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch(services, "巡检 Linux 服务状态")

        assert task.status == HousekeeperTaskStatus.COMPLETED
        rr = task.result_payload["run_record"]
        assert rr["run_status"] == "succeeded"

    def test_timeout_produces_run_status_failed(self, tmp_path: Path):
        """TIMED_OUT conclusion → run_record.run_status == "failed"."""
        repo_root = tmp_path / "repo"
        helper = _linux_timeout_helper(tmp_path / "timeout.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch(services, "巡检 Linux 服务状态")

        assert task.status == HousekeeperTaskStatus.FAILED
        rr = task.result_payload["run_record"]
        assert rr["run_status"] == "failed"

    def test_infra_error_produces_run_status_failed(self, tmp_path: Path):
        """INFRA_ERROR keeps run_status failed even when the task enters approval."""
        repo_root = tmp_path / "repo"
        helper = _linux_infra_error_helper(tmp_path / "infra.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch(services, "巡检 Linux 服务状态")

        assert task.status == HousekeeperTaskStatus.APPROVAL_REQUIRED
        rr = task.result_payload["run_record"]
        assert rr["run_status"] == "failed"

    def test_unknown_conclusion_produces_run_status_needs_review(self, tmp_path: Path):
        """UNKNOWN conclusion → run_record.run_status == "needs_review"."""
        repo_root = tmp_path / "repo"
        helper = _linux_unknown_helper(tmp_path / "unknown.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch(services, "巡检 Linux 服务状态")

        rr = task.result_payload["run_record"]
        assert rr["run_status"] == "needs_review"

    def test_run_record_fields_match_summary(self, tmp_path: Path):
        """run_record task_id / run_id / started_at / completed_at match summary fields."""
        repo_root = tmp_path / "repo"
        helper = _linux_success_helper(tmp_path / "success.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch(services, "巡检 Linux 服务状态")

        payload = task.result_payload
        rr = payload["run_record"]

        # Cross-check with original summary fields
        assert rr["task_id"] == payload["task_id"]
        assert rr["run_id"] == payload["run_id"]
        assert rr["started_at"] == payload["started_at"]
        assert rr["completed_at"] == payload["finished_at"]

    def test_run_record_result_data_contains_bridge_fields(self, tmp_path: Path):
        """run_record.result_data matches bridge-selected summary fields."""
        repo_root = tmp_path / "repo"
        helper = _linux_success_helper(tmp_path / "success.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch(services, "巡检 Linux 服务状态")

        rr = task.result_payload["run_record"]
        rd = rr["result_data"]
        payload = task.result_payload
        assert rd["artifacts"] == payload["artifacts"]
        assert rd["conclusion"] == payload["conclusion"]
        assert rd["duration_seconds"] == payload["duration_seconds"]
        assert rd["process_returncode"] == payload["process_returncode"]
        assert rd["aep_final_status"] == payload["aep_final_status"]
        assert rd["aep_driver_status"] == payload["aep_driver_status"]

    def test_run_record_run_status_matches_gate_evaluation(self, tmp_path: Path):
        """run_record status fields stay aligned with gate_evaluation.run_status."""
        repo_root = tmp_path / "repo"
        helper = _linux_success_helper(tmp_path / "success.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch(services, "巡检 Linux 服务状态")

        gate_status = task.result_payload["gate_evaluation"]["run_status"]
        status = task.result_payload["run_record"]["status"]
        run_status = task.result_payload["run_record"]["run_status"]
        assert type(status) is str
        assert status == run_status
        assert gate_status == run_status

    def test_failed_run_record_has_error_message(self, tmp_path: Path):
        """Failed run_record includes error_message from summary."""
        repo_root = tmp_path / "repo"
        helper = _linux_timeout_helper(tmp_path / "timeout.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch(services, "巡检 Linux 服务状态")

        rr = task.result_payload["run_record"]
        assert rr["run_status"] == "failed"
        assert rr["error_message"] is not None
        assert len(rr["error_message"]) > 0
