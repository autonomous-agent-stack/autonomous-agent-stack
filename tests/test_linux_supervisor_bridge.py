"""Tests for linux_supervisor_bridge — pure-function bridge between
LinuxSupervisor output shapes and unified contracts.

These tests prove that real Linux execution output flows through the
unified gate/run/worker systems correctly.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from autoresearch.shared.linux_supervisor_contract import (
    LinuxSupervisorConclusion,
    LinuxSupervisorProcessHeartbeatRead,
    LinuxSupervisorProcessStatusRead,
    LinuxSupervisorTaskStatus,
    LinuxSupervisorTaskSummaryRead,
)
from autoresearch.shared.run_contract import RunStatus
from autoresearch.shared.task_gate_contract import (
    GateAction,
    GateOutcome,
    make_gate_verdict,
)
from autoresearch.shared.worker_contract import (
    WorkerHeartbeat,
    WorkerRegistration,
    WorkerStatus,
    WorkerType,
)

from autoresearch.shared.linux_supervisor_bridge import (
    supervisor_conclusion_to_gate_outcome,
    supervisor_conclusion_to_run_status,
    supervisor_heartbeat_to_worker_heartbeat,
    supervisor_heartbeat_to_worker_registration,
    supervisor_summary_to_gate_checks,
    supervisor_summary_to_run_record,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)


def _summary(
    *,
    conclusion: LinuxSupervisorConclusion = LinuxSupervisorConclusion.SUCCEEDED,
    success: bool = True,
    aep_final_status: str | None = "ready_for_promotion",
    aep_driver_status: str | None = "succeeded",
    process_returncode: int | None = 0,
    used_mock_fallback: bool = False,
    artifacts: dict[str, str] | None = None,
    message: str = "",
    duration_seconds: float = 10.0,
) -> LinuxSupervisorTaskSummaryRead:
    return LinuxSupervisorTaskSummaryRead(
        task_id="task-001",
        run_id="run-001",
        status=LinuxSupervisorTaskStatus.COMPLETED if success else LinuxSupervisorTaskStatus.FAILED,
        conclusion=conclusion,
        success=success,
        agent_id="openhands",
        started_at=_NOW,
        finished_at=_NOW + timedelta(seconds=duration_seconds),
        duration_seconds=duration_seconds,
        process_returncode=process_returncode,
        aep_final_status=aep_final_status,
        aep_driver_status=aep_driver_status,
        used_mock_fallback=used_mock_fallback,
        message=message,
        task_dir="/tmp/task-001",
        run_dir="/tmp/task-001/run",
        artifacts=(
            artifacts
            if artifacts is not None
            else {"stdout.log": "/tmp/task-001/artifacts/stdout.log"}
        ),
    )


def _process_hb(
    *,
    status: str = "idle",
    current_task_id: str | None = None,
    queue_depth: int = 0,
    observed_at: datetime | None = None,
) -> LinuxSupervisorProcessHeartbeatRead:
    return LinuxSupervisorProcessHeartbeatRead(
        observed_at=observed_at or _NOW,
        pid=12345 if status != "stopped" else None,
        current_task_id=current_task_id,
        queue_depth=queue_depth,
        status=status,
    )


def _process_status(
    *,
    status: str = "idle",
    current_task_id: str | None = None,
    message: str = "",
) -> LinuxSupervisorProcessStatusRead:
    return LinuxSupervisorProcessStatusRead(
        status=status,
        pid=12345 if status != "stopped" else None,
        current_task_id=current_task_id,
        updated_at=_NOW,
        message=message,
    )


# ===================================================================
# 1. Conclusion → GateOutcome
# ===================================================================


class TestConclusionToGateOutcome:
    """Every LinuxSupervisorConclusion maps to the correct GateOutcome."""

    @pytest.mark.parametrize(
        "conclusion, expected",
        [
            (LinuxSupervisorConclusion.SUCCEEDED, GateOutcome.SUCCESS),
            (LinuxSupervisorConclusion.TIMED_OUT, GateOutcome.TIMEOUT),
            (
                LinuxSupervisorConclusion.STALLED_NO_PROGRESS,
                GateOutcome.TIMEOUT,
            ),
            (LinuxSupervisorConclusion.MOCK_FALLBACK, GateOutcome.MISSING_ARTIFACTS),
            (LinuxSupervisorConclusion.ASSERTION_FAILED, GateOutcome.OVERREACH),
            (LinuxSupervisorConclusion.INFRA_ERROR, GateOutcome.NEEDS_HUMAN_CONFIRM),
            (LinuxSupervisorConclusion.UNKNOWN, GateOutcome.NEEDS_HUMAN_CONFIRM),
        ],
    )
    def test_maps_correctly(self, conclusion, expected):
        assert supervisor_conclusion_to_gate_outcome(conclusion) == expected


# ===================================================================
# 2. Summary → GateChecks
# ===================================================================


class TestSummaryToGateChecks:
    """Gate checks derived from real LinuxSupervisorTaskSummaryRead."""

    def test_succeeded_summary_all_passed(self):
        summary = _summary()
        checks = supervisor_summary_to_gate_checks(summary)
        assert all(c.passed for c in checks)

    def test_failed_summary_mixed_checks(self):
        summary = _summary(
            conclusion=LinuxSupervisorConclusion.TIMED_OUT,
            success=False,
            aep_final_status=None,
            aep_driver_status="timed_out",
        )
        checks = supervisor_summary_to_gate_checks(summary)
        check_map = {c.check_id: c for c in checks}
        assert not check_map["agent_completed"].passed
        assert not check_map["aep_final_status"].passed

    def test_mock_fallback_flags_warning(self):
        summary = _summary(used_mock_fallback=True)
        checks = supervisor_summary_to_gate_checks(summary)
        mock_check = next(c for c in checks if c.check_id == "no_mock_fallback")
        assert mock_check.passed is False
        assert mock_check.severity == "warning"

    def test_empty_artifacts_flagged(self):
        summary = _summary(artifacts={})
        checks = supervisor_summary_to_gate_checks(summary)
        art_check = next(c for c in checks if c.check_id == "artifacts_present")
        assert art_check.passed is False

    def test_bad_returncode_flagged(self):
        summary = _summary(process_returncode=137)
        checks = supervisor_summary_to_gate_checks(summary)
        exit_check = next(c for c in checks if c.check_id == "process_exit")
        assert exit_check.passed is False

    def test_none_returncode_passes(self):
        summary = _summary(process_returncode=None)
        checks = supervisor_summary_to_gate_checks(summary)
        exit_check = next(c for c in checks if c.check_id == "process_exit")
        assert exit_check.passed is True


# ===================================================================
# 3. Conclusion → RunStatus
# ===================================================================


class TestConclusionToRunStatus:
    @pytest.mark.parametrize(
        "conclusion, expected",
        [
            (LinuxSupervisorConclusion.SUCCEEDED, RunStatus.SUCCEEDED),
            (LinuxSupervisorConclusion.TIMED_OUT, RunStatus.FAILED),
            (LinuxSupervisorConclusion.STALLED_NO_PROGRESS, RunStatus.FAILED),
            (LinuxSupervisorConclusion.MOCK_FALLBACK, RunStatus.FAILED),
            (LinuxSupervisorConclusion.ASSERTION_FAILED, RunStatus.FAILED),
            (LinuxSupervisorConclusion.INFRA_ERROR, RunStatus.FAILED),
            (LinuxSupervisorConclusion.UNKNOWN, RunStatus.NEEDS_REVIEW),
        ],
    )
    def test_maps_correctly(self, conclusion, expected):
        assert supervisor_conclusion_to_run_status(conclusion) == expected


# ===================================================================
# 4. Summary → RunRecord
# ===================================================================


class TestSummaryToRunRecord:
    def test_succeeded_run_record_fields(self):
        summary = _summary()
        record = supervisor_summary_to_run_record(
            summary, worker_id="linux_housekeeper", retry_attempt=1
        )
        assert record.run_id == "run-001"
        assert record.task_id == "task-001"
        assert record.worker_id == "linux_housekeeper"
        assert record.status == RunStatus.SUCCEEDED
        assert record.started_at == _NOW
        assert record.completed_at == _NOW + timedelta(seconds=10)
        assert record.error_message is None
        assert record.attempt == 1

    def test_failed_run_record_has_error(self):
        summary = _summary(
            conclusion=LinuxSupervisorConclusion.TIMED_OUT,
            success=False,
            message="Task exceeded 1800s deadline",
        )
        record = supervisor_summary_to_run_record(summary, worker_id="linux_housekeeper")
        assert record.status == RunStatus.FAILED
        assert record.error_message == "Task exceeded 1800s deadline"

    def test_unknown_maps_to_needs_review(self):
        summary = _summary(
            conclusion=LinuxSupervisorConclusion.UNKNOWN,
            success=False,
        )
        record = supervisor_summary_to_run_record(summary, worker_id="linux_housekeeper")
        assert record.status == RunStatus.NEEDS_REVIEW

    def test_result_data_includes_supervisor_fields(self):
        summary = _summary(
            artifacts={"stdout.log": "/tmp/stdout.log", "stderr.log": "/tmp/stderr.log"}
        )
        record = supervisor_summary_to_run_record(summary, worker_id="linux_housekeeper")
        rd = record.result_data
        assert "artifacts" in rd
        assert "aep_final_status" in rd
        assert "aep_driver_status" in rd
        assert "conclusion" in rd
        assert "duration_seconds" in rd
        assert "process_returncode" in rd


# ===================================================================
# 5. Heartbeat → WorkerHeartbeat
# ===================================================================


class TestHeartbeatConversion:
    def test_idle_fresh_is_online(self):
        hb = _process_hb(status="idle")
        ps = _process_status(status="idle")
        whb = supervisor_heartbeat_to_worker_heartbeat(
            hb, ps, worker_id="linux_housekeeper", now=_NOW
        )
        assert isinstance(whb, WorkerHeartbeat)
        assert whb.worker_id == "linux_housekeeper"
        assert whb.status == WorkerStatus.ONLINE
        assert whb.metrics.active_tasks == 0

    def test_running_fresh_is_busy(self):
        hb = _process_hb(status="running", current_task_id="task-001")
        ps = _process_status(status="running", current_task_id="task-001")
        whb = supervisor_heartbeat_to_worker_heartbeat(
            hb, ps, worker_id="linux_housekeeper", now=_NOW
        )
        assert whb.status == WorkerStatus.BUSY
        assert whb.metrics.active_tasks == 1
        assert "task-001" in whb.active_task_ids

    def test_stopped_is_offline(self):
        hb = _process_hb(status="stopped")
        ps = _process_status(status="stopped")
        whb = supervisor_heartbeat_to_worker_heartbeat(hb, ps, worker_id="linux_housekeeper")
        assert whb.status == WorkerStatus.OFFLINE

    def test_stale_heartbeat_is_offline(self):
        """Age > 120s → OFFLINE (STALE and DEAD thresholds are both 120)."""
        stale_time = _NOW - timedelta(seconds=130)
        hb = _process_hb(status="idle", observed_at=stale_time)
        ps = _process_status(status="idle")
        whb = supervisor_heartbeat_to_worker_heartbeat(
            hb, ps, worker_id="linux_housekeeper", now=_NOW
        )
        assert whb.status == WorkerStatus.OFFLINE

    def test_very_stale_heartbeat_is_offline(self):
        dead_time = _NOW - timedelta(seconds=200)
        hb = _process_hb(status="idle", observed_at=dead_time)
        ps = _process_status(status="idle")
        whb = supervisor_heartbeat_to_worker_heartbeat(
            hb, ps, worker_id="linux_housekeeper", now=_NOW
        )
        assert whb.status == WorkerStatus.OFFLINE

    def test_metadata_includes_queue_depth(self):
        hb = _process_hb(queue_depth=3)
        ps = _process_status()
        whb = supervisor_heartbeat_to_worker_heartbeat(hb, ps, worker_id="linux_housekeeper")
        assert whb.metadata["queue_depth"] == 3


# ===================================================================
# 6. Heartbeat → WorkerRegistration
# ===================================================================


class TestHeartbeatToRegistration:
    def test_produces_linux_worker_type(self):
        hb = _process_hb()
        ps = _process_status()
        reg = supervisor_heartbeat_to_worker_registration(hb, ps, worker_id="linux_housekeeper")
        assert isinstance(reg, WorkerRegistration)
        assert reg.worker_type == WorkerType.LINUX

    def test_backend_kind_is_linux_supervisor(self):
        hb = _process_hb()
        ps = _process_status()
        reg = supervisor_heartbeat_to_worker_registration(hb, ps, worker_id="linux_housekeeper")
        assert reg.backend_kind == "linux_supervisor"

    def test_capabilities_match_registry(self):
        hb = _process_hb()
        ps = _process_status()
        reg = supervisor_heartbeat_to_worker_registration(hb, ps, worker_id="linux_housekeeper")
        assert "shell" in reg.capabilities
        assert "script_runner" in reg.capabilities
        assert "log_collection" in reg.capabilities
        assert "ops_inspection" in reg.capabilities

    def test_max_concurrent_is_one(self):
        hb = _process_hb()
        ps = _process_status()
        reg = supervisor_heartbeat_to_worker_registration(hb, ps, worker_id="linux_housekeeper")
        assert reg.max_concurrent_tasks == 1


# ===================================================================
# 7. Full chain end-to-end
# ===================================================================


class TestFullChainEndToEnd:
    """summary → checks → make_gate_verdict → verdict for all conclusions."""

    @pytest.mark.parametrize(
        "conclusion, success, expected_action",
        [
            (LinuxSupervisorConclusion.SUCCEEDED, True, GateAction.ACCEPT),
            (LinuxSupervisorConclusion.TIMED_OUT, False, GateAction.RETRY),
            (
                LinuxSupervisorConclusion.STALLED_NO_PROGRESS,
                False,
                GateAction.RETRY,
            ),
            (LinuxSupervisorConclusion.MOCK_FALLBACK, False, GateAction.RETRY),
            (LinuxSupervisorConclusion.ASSERTION_FAILED, False, GateAction.REJECT),
            (LinuxSupervisorConclusion.INFRA_ERROR, False, GateAction.NEEDS_REVIEW),
            (LinuxSupervisorConclusion.UNKNOWN, False, GateAction.NEEDS_REVIEW),
        ],
    )
    def test_chain_produces_correct_verdict(self, conclusion, success, expected_action):
        summary = _summary(
            conclusion=conclusion,
            success=success,
        )
        outcome = supervisor_conclusion_to_gate_outcome(conclusion)
        checks = supervisor_summary_to_gate_checks(summary)
        verdict = make_gate_verdict(
            outcome,
            reason=summary.message or f"Chain test for {conclusion.value}",
            checks=checks,
        )
        assert verdict.outcome == outcome
        assert verdict.action == expected_action

    def test_timeout_with_retry_exhaustion_upgrades_to_fallback(self):
        summary = _summary(conclusion=LinuxSupervisorConclusion.TIMED_OUT, success=False)
        outcome = supervisor_conclusion_to_gate_outcome(LinuxSupervisorConclusion.TIMED_OUT)
        checks = supervisor_summary_to_gate_checks(summary)
        verdict = make_gate_verdict(
            outcome,
            reason="exhausted",
            checks=checks,
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="fallback-agent",
        )
        assert verdict.action == GateAction.FALLBACK

    def test_timeout_without_fallback_escalates_to_review(self):
        summary = _summary(conclusion=LinuxSupervisorConclusion.TIMED_OUT, success=False)
        outcome = supervisor_conclusion_to_gate_outcome(LinuxSupervisorConclusion.TIMED_OUT)
        checks = supervisor_summary_to_gate_checks(summary)
        verdict = make_gate_verdict(
            outcome,
            reason="exhausted, no fallback",
            checks=checks,
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id=None,
        )
        assert verdict.action == GateAction.NEEDS_REVIEW
