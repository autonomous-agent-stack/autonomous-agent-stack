"""Integration tests: real LinuxSupervisorService → ControlPlaneService → gate evaluation.

These tests prove that when a real Linux task executes through the control plane,
the linux_supervisor_bridge functions are called and unified contract artifacts
(GateOutcome, GateCheck[], GateVerdict, RunStatus) are produced and stored in
result_payload["gate_evaluation"].

The control plane's decision logic (COMPLETED/FAILED based on summary.success)
is unchanged — gate evaluation is observational, not controlling.
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
# Helpers
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
    """Helper script that produces a SUCCEEDED conclusion."""
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
    """Helper script that produces a TIMED_OUT conclusion."""
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
    """Helper script that exits without creating summary.json → INFRA_ERROR."""
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
        "linux": linux_service,
        "packages": package_registry,
        "workers": worker_registry,
        "approval": approval_service,
        "manager": manager_service,
        "control": control_plane_service,
    }


def _dispatch_linux_task(services, message: str) -> dict:
    """Dispatch a Linux task through the control plane and return result_payload."""
    cp = services["control"]
    now = utc_now()
    draft = HousekeeperTaskDraftRead(
        draft_id="draft-001",
        session_id="session-001",
        source_message=message,
        candidate_package_ids=["linux_housekeeping_agent_v0"],
        routing_reason="test",
        created_at=now,
    )
    task = cp.submit_housekeeper_draft(draft, housekeeper_task_id="ht-001", dry_run=False)
    return task


# ===================================================================
# Tests
# ===================================================================


class TestLinuxGateIntegration:
    """Prove that real Linux execution through ControlPlaneService produces
    gate evaluation artifacts via the bridge module."""

    def test_successful_dispatch_produces_gate_accept(self, tmp_path: Path):
        """SUCCEEDED conclusion → gate_outcome=success, gate_action=accept."""
        repo_root = tmp_path / "repo"
        helper = _linux_success_helper(tmp_path / "success.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch_linux_task(services, "巡检 Linux 服务状态")

        assert task.status == HousekeeperTaskStatus.COMPLETED
        gate = task.result_payload["gate_evaluation"]
        assert gate["gate_outcome"] == "success"
        assert gate["gate_action"] == "accept"
        assert gate["run_status"] == "succeeded"
        assert len(gate["gate_checks"]) == 5
        assert all(c["passed"] for c in gate["gate_checks"])

    def test_timeout_dispatch_produces_gate_retry(self, tmp_path: Path):
        """TIMED_OUT conclusion → gate_outcome=timeout, gate_action=retry."""
        repo_root = tmp_path / "repo"
        helper = _linux_timeout_helper(tmp_path / "timeout.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch_linux_task(services, "巡检 Linux 服务状态")

        assert task.status == HousekeeperTaskStatus.FAILED
        gate = task.result_payload["gate_evaluation"]
        assert gate["gate_outcome"] == "timeout"
        assert gate["gate_action"] == "retry"
        assert gate["run_status"] == "failed"
        # At least one check should fail for timeout
        assert any(not c["passed"] for c in gate["gate_checks"])

    def test_infra_error_dispatch_produces_needs_review(self, tmp_path: Path):
        """INFRA_ERROR conclusion → gate_outcome=needs_human_confirm, action=needs_review."""
        repo_root = tmp_path / "repo"
        helper = _linux_infra_error_helper(tmp_path / "infra.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch_linux_task(services, "巡检 Linux 服务状态")

        assert task.status == HousekeeperTaskStatus.FAILED
        gate = task.result_payload["gate_evaluation"]
        assert gate["gate_outcome"] == "needs_human_confirm"
        assert gate["gate_action"] == "needs_review"
        assert gate["run_status"] == "failed"

    def test_gate_checks_match_bridge_output(self, tmp_path: Path):
        """Gate checks contain the 5 expected check_ids from bridge module."""
        repo_root = tmp_path / "repo"
        helper = _linux_success_helper(tmp_path / "success.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch_linux_task(services, "巡检 Linux 服务状态")

        gate = task.result_payload["gate_evaluation"]
        check_ids = {c["check_id"] for c in gate["gate_checks"]}
        assert check_ids == {
            "aep_final_status",
            "process_exit",
            "agent_completed",
            "no_mock_fallback",
            "artifacts_present",
        }

    def test_gate_evaluation_preserves_original_summary(self, tmp_path: Path):
        """result_payload still contains all original summary fields alongside gate_evaluation."""
        repo_root = tmp_path / "repo"
        helper = _linux_success_helper(tmp_path / "success.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch_linux_task(services, "巡检 Linux 服务状态")

        payload = task.result_payload
        # Original summary fields preserved
        assert "task_id" in payload
        assert "run_id" in payload
        assert "conclusion" in payload
        assert "success" in payload
        assert "duration_seconds" in payload
        assert "artifacts" in payload
        # Gate evaluation added
        assert "gate_evaluation" in payload

    def test_failed_task_error_includes_conclusion(self, tmp_path: Path):
        """Failed task's error field contains the conclusion value."""
        repo_root = tmp_path / "repo"
        helper = _linux_timeout_helper(tmp_path / "timeout.py")
        _seed_agent_package_tree(repo_root)
        services = _build_services(repo_root, helper)

        task = _dispatch_linux_task(services, "巡检 Linux 服务状态")

        assert task.status == HousekeeperTaskStatus.FAILED
        assert task.error == "timed_out"
