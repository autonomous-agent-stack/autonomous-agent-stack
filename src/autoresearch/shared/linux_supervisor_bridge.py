"""Thin bridge between LinuxSupervisor output shapes and unified contracts.

Pure functions only — no classes, no side effects, no modifications to
existing services.  Each function translates a production type from
``linux_supervisor_contract`` into the corresponding unified type.

These functions are called by tests first, and later by thin adapter layers
in the control plane / worker registry without touching core service code.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .linux_supervisor_contract import (
    LinuxSupervisorConclusion,
    LinuxSupervisorProcessHeartbeatRead,
    LinuxSupervisorProcessStatusRead,
    LinuxSupervisorTaskSummaryRead,
)
from .run_contract import RunStatus
from .task_gate_contract import GateCheck, GateOutcome
from .worker_contract import (
    AllowedAction,
    WorkerHeartbeat,
    WorkerMetrics,
    WorkerRegistration,
    WorkerStatus,
    WorkerType,
)

# ---------------------------------------------------------------------------
# 1. Conclusion → GateOutcome
# ---------------------------------------------------------------------------

_CONCLUSION_TO_OUTCOME: dict[LinuxSupervisorConclusion, GateOutcome] = {
    LinuxSupervisorConclusion.SUCCEEDED: GateOutcome.SUCCESS,
    LinuxSupervisorConclusion.TIMED_OUT: GateOutcome.TIMEOUT,
    LinuxSupervisorConclusion.STALLED_NO_PROGRESS: GateOutcome.TIMEOUT,
    LinuxSupervisorConclusion.MOCK_FALLBACK: GateOutcome.MISSING_ARTIFACTS,
    LinuxSupervisorConclusion.ASSERTION_FAILED: GateOutcome.OVERREACH,
    LinuxSupervisorConclusion.INFRA_ERROR: GateOutcome.NEEDS_HUMAN_CONFIRM,
    LinuxSupervisorConclusion.UNKNOWN: GateOutcome.NEEDS_HUMAN_CONFIRM,
}


def supervisor_conclusion_to_gate_outcome(
    conclusion: LinuxSupervisorConclusion,
) -> GateOutcome:
    """Map a LinuxSupervisorConclusion to unified GateOutcome."""
    return _CONCLUSION_TO_OUTCOME[conclusion]


# ---------------------------------------------------------------------------
# 2. Summary → GateChecks
# ---------------------------------------------------------------------------


def supervisor_summary_to_gate_checks(
    summary: LinuxSupervisorTaskSummaryRead,
) -> list[GateCheck]:
    """Derive gate checks from a real LinuxSupervisorTaskSummaryRead."""
    checks: list[GateCheck] = []

    # AEP final status — None means no AEP summary was produced (not ok)
    aep_ok = summary.aep_final_status in {"ready_for_promotion", "promoted"}
    checks.append(
        GateCheck(
            check_id="aep_final_status",
            passed=aep_ok,
            detail=summary.aep_final_status or "no AEP summary",
            severity="critical" if not aep_ok else "info",
        )
    )

    # Process exit
    exit_ok = summary.process_returncode in {0, 2, None}
    checks.append(
        GateCheck(
            check_id="process_exit",
            passed=exit_ok,
            detail=f"returncode={summary.process_returncode}",
            severity="critical" if not exit_ok else "info",
        )
    )

    # Agent completed
    checks.append(
        GateCheck(
            check_id="agent_completed",
            passed=summary.conclusion == LinuxSupervisorConclusion.SUCCEEDED,
            detail=f"conclusion={summary.conclusion.value}",
            severity=(
                "critical" if summary.conclusion != LinuxSupervisorConclusion.SUCCEEDED else "info"
            ),
        )
    )

    # No mock fallback
    checks.append(
        GateCheck(
            check_id="no_mock_fallback",
            passed=not summary.used_mock_fallback,
            detail=f"used_mock_fallback={summary.used_mock_fallback}",
            severity="warning",
        )
    )

    # Artifacts present
    has_artifacts = bool(summary.artifacts)
    checks.append(
        GateCheck(
            check_id="artifacts_present",
            passed=has_artifacts,
            detail=f"{len(summary.artifacts)} artifacts",
            severity="warning" if not has_artifacts else "info",
        )
    )

    return checks


# ---------------------------------------------------------------------------
# 3. Conclusion → RunStatus
# ---------------------------------------------------------------------------

_CONCLUSION_TO_RUN: dict[LinuxSupervisorConclusion, RunStatus] = {
    LinuxSupervisorConclusion.SUCCEEDED: RunStatus.SUCCEEDED,
    LinuxSupervisorConclusion.TIMED_OUT: RunStatus.FAILED,
    LinuxSupervisorConclusion.STALLED_NO_PROGRESS: RunStatus.FAILED,
    LinuxSupervisorConclusion.MOCK_FALLBACK: RunStatus.FAILED,
    LinuxSupervisorConclusion.ASSERTION_FAILED: RunStatus.FAILED,
    LinuxSupervisorConclusion.INFRA_ERROR: RunStatus.FAILED,
    LinuxSupervisorConclusion.UNKNOWN: RunStatus.NEEDS_REVIEW,
}


def supervisor_conclusion_to_run_status(
    conclusion: LinuxSupervisorConclusion,
) -> RunStatus:
    """Map a LinuxSupervisorConclusion to unified RunStatus."""
    return _CONCLUSION_TO_RUN[conclusion]


# ---------------------------------------------------------------------------
# 4. Summary → BridgeRunRecord
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BridgeRunRecord:
    """Mapped run record produced from a supervisor summary."""

    run_id: str
    task_id: str
    worker_id: str
    status: RunStatus
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    result_data: dict[str, Any]
    attempt: int


def supervisor_summary_to_run_record(
    summary: LinuxSupervisorTaskSummaryRead,
    *,
    worker_id: str,
    retry_attempt: int = 1,
) -> BridgeRunRecord:
    """Convert a LinuxSupervisorTaskSummaryRead to a unified run record."""
    status = supervisor_conclusion_to_run_status(summary.conclusion)
    return BridgeRunRecord(
        run_id=summary.run_id,
        task_id=summary.task_id,
        worker_id=worker_id,
        status=status,
        started_at=summary.started_at,
        completed_at=summary.finished_at,
        error_message=summary.message if not summary.success else None,
        result_data={
            "artifacts": summary.artifacts,
            "aep_final_status": summary.aep_final_status,
            "aep_driver_status": summary.aep_driver_status,
            "conclusion": summary.conclusion.value,
            "duration_seconds": summary.duration_seconds,
            "process_returncode": summary.process_returncode,
        },
        attempt=retry_attempt,
    )


# ---------------------------------------------------------------------------
# 5. Heartbeat → WorkerHeartbeat
# ---------------------------------------------------------------------------

# Thresholds match worker_registry.py lines 117-124
_STALE_THRESHOLD_SEC = 120
_DEAD_THRESHOLD_SEC = 120  # worker_registry uses >120 → OFFLINE


def _derive_worker_status(
    process_status: str,
    heartbeat_age_sec: float,
) -> WorkerStatus:
    if process_status == "stopped":
        return WorkerStatus.OFFLINE
    if heartbeat_age_sec > _DEAD_THRESHOLD_SEC:
        return WorkerStatus.OFFLINE
    if heartbeat_age_sec > _STALE_THRESHOLD_SEC:
        return WorkerStatus.DEGRADED
    if process_status == "running":
        return WorkerStatus.BUSY
    return WorkerStatus.ONLINE


def supervisor_heartbeat_to_worker_heartbeat(
    process_hb: LinuxSupervisorProcessHeartbeatRead,
    process_status: LinuxSupervisorProcessStatusRead,
    *,
    worker_id: str,
    now: datetime | None = None,
) -> WorkerHeartbeat:
    """Convert supervisor heartbeat + status to unified WorkerHeartbeat."""
    now = now or datetime.now(timezone.utc)
    age = (now - process_hb.observed_at).total_seconds()
    status = _derive_worker_status(process_hb.status, age)

    active_tasks = 1 if process_hb.status == "running" else 0
    active_task_ids = [process_hb.current_task_id] if process_hb.current_task_id else []

    errors: list[str] = []
    if process_status.message and process_hb.status == "stopped":
        errors.append(process_status.message)

    return WorkerHeartbeat(
        worker_id=worker_id,
        status=status,
        metrics=WorkerMetrics(active_tasks=active_tasks),
        active_task_ids=active_task_ids,
        errors=errors,
        metadata={
            "queue_depth": process_hb.queue_depth,
            "process_status": process_hb.status,
        },
    )


# ---------------------------------------------------------------------------
# 6. Heartbeat → WorkerRegistration
# ---------------------------------------------------------------------------

_LINUX_CAPABILITIES = [
    "shell",
    "script_runner",
    "log_collection",
    "ops_inspection",
]

_LINUX_ALLOWED_ACTIONS = [
    AllowedAction.EXECUTE_TASK,
    AllowedAction.RUN_SCRIPT,
    AllowedAction.COLLECT_LOGS,
]


def supervisor_heartbeat_to_worker_registration(
    process_hb: LinuxSupervisorProcessHeartbeatRead,
    process_status: LinuxSupervisorProcessStatusRead,
    *,
    worker_id: str,
    name: str = "Linux Housekeeper",
) -> WorkerRegistration:
    """Derive a WorkerRegistration from supervisor heartbeat + status."""
    now = datetime.now(timezone.utc)
    age = (now - process_hb.observed_at).total_seconds()
    status = _derive_worker_status(process_hb.status, age)

    return WorkerRegistration(
        worker_id=worker_id,
        name=name,
        worker_type=WorkerType.LINUX,
        capabilities=_LINUX_CAPABILITIES,
        allowed_actions=_LINUX_ALLOWED_ACTIONS,
        status=status,
        last_heartbeat=process_hb.observed_at,
        max_concurrent_tasks=1,
        backend_kind="linux_supervisor",
    )
