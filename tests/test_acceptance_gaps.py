"""Acceptance harness blind-spot tests.

Covers scenarios the 30-run acceptance harness does NOT exercise.
Runnable offline now; designed to be re-targeted to real backends later.

Blind spots:
  1. Concurrent dispatch — lease contention between workers
  2. Heartbeat timeout — worker goes OFFLINE
  3. Cancel flow — task cancelled mid-execution
  4. Orphan recovery — task stuck in RUNNING after crash
  5. Artifact validation — missing required artifacts detected by gate
  6. Approval pre-check — high-risk task requires approval
  7. Gate after real-shaped result — DriverResult-style output
  8. Max-concurrent enforcement — worker at capacity
"""

from __future__ import annotations

import pytest
from autoresearch.shared.run_contract import RunRecord, RunStatus
from autoresearch.shared.task_contract import (
    Task,
    TaskPriority,
    TaskStatus,
    is_valid_transition,
)
from autoresearch.shared.task_gate_contract import (
    GateAction,
    GateCheck,
    GateOutcome,
    make_gate_verdict,
)
from autoresearch.shared.worker_contract import (
    WorkerStatus,
)
from autoresearch.testing.fake_workers import (
    FakeLinuxWorker,
    HeartbeatSimulation,
    LeaseManager,
)

# ---------------------------------------------------------------------------
# 1. Concurrent dispatch — lease contention
# ---------------------------------------------------------------------------


class TestConcurrentDispatch:
    """Two workers should not both acquire lease for the same task."""

    def test_first_worker_gets_lease_second_rejected(self):
        lease_mgr = LeaseManager(lease_timeout_sec=900)
        task_id = "task-concurrent-001"

        assert lease_mgr.acquire(task_id, "worker-A") is True
        assert lease_mgr.acquire(task_id, "worker-B") is False

    def test_second_worker_gets_lease_after_release(self):
        lease_mgr = LeaseManager(lease_timeout_sec=900)
        task_id = "task-concurrent-002"

        lease_mgr.acquire(task_id, "worker-A")
        lease_mgr.release(task_id)
        assert lease_mgr.acquire(task_id, "worker-B") is True

    def test_lease_timeout_allows_new_acquisition(self):
        lease_mgr = LeaseManager(lease_timeout_sec=900)
        task_id = "task-concurrent-003"

        lease_mgr.acquire(task_id, "worker-A")
        expired = lease_mgr.simulate_timeout_check(task_id, elapsed_seconds=1000)
        assert expired is True

        # simulate_timeout_check is a pure predicate; actual expiry release
        # would be done by a supervisor calling release() after detecting timeout
        lease_mgr.release(task_id)
        assert lease_mgr.acquire(task_id, "worker-B") is True


# ---------------------------------------------------------------------------
# 2. Heartbeat timeout → worker OFFLINE
# ---------------------------------------------------------------------------


class TestHeartbeatTimeout:
    """Worker that misses heartbeats transitions to OFFLINE."""

    def test_fresh_heartbeat_is_online(self):
        sim = HeartbeatSimulation(worker_id="w-001")
        assert sim.simulate_heartbeat_age(5) == WorkerStatus.ONLINE

    def test_stale_heartbeat_is_degraded(self):
        sim = HeartbeatSimulation(worker_id="w-002")
        assert sim.simulate_heartbeat_age(60) == WorkerStatus.DEGRADED

    def test_dead_heartbeat_is_offline(self):
        sim = HeartbeatSimulation(worker_id="w-003")
        assert sim.simulate_heartbeat_age(400) == WorkerStatus.OFFLINE

    def test_heartbeat_with_active_task_is_busy(self):
        sim = HeartbeatSimulation(worker_id="w-004")
        sim.acquire_lease("task-001")
        assert sim.simulate_heartbeat_age(5) == WorkerStatus.BUSY

    def test_heartbeat_age_progression_sequence(self):
        # Thresholds: <=30 ONLINE, 30<x<=300 DEGRADED, >300 OFFLINE
        sim = HeartbeatSimulation(worker_id="w-005")
        ages = [0, 30, 60, 120, 300, 301, 600]
        expected = [
            WorkerStatus.ONLINE,
            WorkerStatus.ONLINE,
            WorkerStatus.DEGRADED,
            WorkerStatus.DEGRADED,
            WorkerStatus.DEGRADED,
            WorkerStatus.OFFLINE,
            WorkerStatus.OFFLINE,
        ]
        for age, exp in zip(ages, expected):
            assert sim.simulate_heartbeat_age(age) == exp


# ---------------------------------------------------------------------------
# 3. Cancel flow
# ---------------------------------------------------------------------------


class TestCancelFlow:
    """Cancelling a task mid-execution."""

    def test_cancel_from_running(self):
        assert is_valid_transition(TaskStatus.RUNNING, TaskStatus.CANCELLED) is True

    def test_cancel_from_queued(self):
        assert is_valid_transition(TaskStatus.QUEUED, TaskStatus.CANCELLED) is True

    def test_cancel_from_succeeded_is_invalid(self):
        assert is_valid_transition(TaskStatus.SUCCEEDED, TaskStatus.CANCELLED) is False

    def test_cancelled_run_record(self):
        run = RunRecord(
            run_id="run-cancel-001",
            task_id="task-cancel-001",
            worker_id="worker-001",
            status=RunStatus.RUNNING,
        )
        run.transition_to(RunStatus.CANCELLED)
        assert run.status == RunStatus.CANCELLED
        with pytest.raises(ValueError):
            run.transition_to(RunStatus.RUNNING)


# ---------------------------------------------------------------------------
# 4. Orphan recovery
# ---------------------------------------------------------------------------


class TestOrphanRecovery:
    """Task stuck in RUNNING after supervisor crash."""

    def test_orphan_detected_via_dead_heartbeat(self):
        sim = HeartbeatSimulation(worker_id="linux-housekeeper-1")
        assert sim.simulate_heartbeat_age(600) == WorkerStatus.OFFLINE

    def test_orphan_run_can_be_failed(self):
        # RUNNING → FAILED is valid for orphan recovery
        assert is_valid_transition(RunStatus.RUNNING, RunStatus.FAILED) is True

    def test_orphan_task_failed_then_requeued(self):
        """Orphan recovery: RUNNING → FAILED (orphan detected) → QUEUED (retry)."""
        assert is_valid_transition(TaskStatus.RUNNING, TaskStatus.FAILED) is True
        assert is_valid_transition(TaskStatus.FAILED, TaskStatus.QUEUED) is True


# ---------------------------------------------------------------------------
# 5. Artifact validation — missing required artifacts
# ---------------------------------------------------------------------------


class TestArtifactValidation:
    """Gate detects missing required artifacts."""

    def test_missing_screenshot_detected(self):
        checks = [
            GateCheck(check_id="output_exists", passed=True, detail="Changes applied"),
            GateCheck(
                check_id="screenshot_exists",
                passed=False,
                detail="No screenshot.png found",
            ),
        ]
        verdict = make_gate_verdict(
            GateOutcome.MISSING_ARTIFACTS,
            reason="Required artifact missing: screenshot.png",
            checks=checks,
        )
        assert verdict.outcome == GateOutcome.MISSING_ARTIFACTS
        assert verdict.action == GateAction.RETRY
        assert any(not c.passed for c in verdict.checks)

    def test_missing_build_log_detected(self):
        checks = [
            GateCheck(check_id="tests_pass", passed=True, detail="12/12 passed"),
            GateCheck(
                check_id="build_log_exists",
                passed=False,
                detail="No build.log found",
            ),
        ]
        verdict = make_gate_verdict(
            GateOutcome.MISSING_ARTIFACTS,
            reason="Required artifact missing: build.log",
            checks=checks,
        )
        assert verdict.action == GateAction.RETRY

    def test_all_artifacts_present_passes(self):
        checks = [
            GateCheck(check_id="output_exists", passed=True, detail="3 files changed"),
            GateCheck(check_id="tests_pass", passed=True, detail="12/12 passed"),
            GateCheck(check_id="scope_check", passed=True, detail="All within scope"),
            GateCheck(check_id="screenshot_exists", passed=True, detail="screenshot.png (42KB)"),
        ]
        verdict = make_gate_verdict(
            GateOutcome.SUCCESS,
            reason="All artifacts present",
            checks=checks,
        )
        assert verdict.action == GateAction.ACCEPT
        assert all(c.passed for c in verdict.checks)


# ---------------------------------------------------------------------------
# 6. Approval pre-check
# ---------------------------------------------------------------------------


class TestApprovalPreCheck:
    """High-risk tasks must go through approval before dispatch."""

    def test_high_risk_task_requires_approval(self):
        task = Task(
            id="task-approval-001",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.HIGH,
            requires_approval=True,
        )
        assert task.requires_approval is True
        assert is_valid_transition(TaskStatus.PENDING, TaskStatus.APPROVAL_REQUIRED) is True

    def test_approved_task_proceeds_to_queued(self):
        assert is_valid_transition(TaskStatus.APPROVAL_REQUIRED, TaskStatus.QUEUED) is True

    def test_rejected_task_goes_to_rejected(self):
        assert is_valid_transition(TaskStatus.APPROVAL_REQUIRED, TaskStatus.REJECTED) is True

    def test_low_risk_task_skips_approval(self):
        task = Task(
            id="task-approval-002",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.LOW,
            requires_approval=False,
        )
        assert task.requires_approval is False
        task.status = TaskStatus.QUEUED
        assert task.status == TaskStatus.QUEUED


# ---------------------------------------------------------------------------
# 7. Gate after real-shaped result
# ---------------------------------------------------------------------------


class TestGateAfterRealShapedResult:
    """Gate evaluates output shaped like real DriverResult."""

    def test_driver_succeeded_gate_accepts(self):
        checks = [
            GateCheck(check_id="output_exists", passed=True, detail="2 files changed"),
            GateCheck(check_id="tests_pass", passed=True, detail="All tests passed"),
        ]
        verdict = make_gate_verdict(
            GateOutcome.SUCCESS,
            reason="All changes applied",
            checks=checks,
        )
        assert verdict.action == GateAction.ACCEPT

    def test_driver_timed_out_gate_retries(self):
        verdict = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Execution exceeded 900s deadline",
            retry_attempt=1,
            max_retries=3,
            fallback_agent_id="fallback-agent",
        )
        assert verdict.action == GateAction.RETRY

    def test_driver_stalled_gate_fallback(self):
        verdict = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="No file changes for 300s",
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="fallback-agent",
        )
        assert verdict.action == GateAction.FALLBACK

    def test_driver_policy_blocked_gate_needs_review(self):
        verdict = make_gate_verdict(
            GateOutcome.NEEDS_HUMAN_CONFIRM,
            reason="Operation blocked by execution policy",
        )
        assert verdict.action == GateAction.NEEDS_REVIEW


# ---------------------------------------------------------------------------
# 8. Max-concurrent enforcement
# ---------------------------------------------------------------------------


class TestMaxConcurrentEnforcement:
    """Worker at capacity should reflect it in heartbeat."""

    def test_worker_at_capacity_reflects_in_heartbeat(self):
        worker = FakeLinuxWorker(worker_id="w-cap-001")
        reg = worker.registration()
        assert reg.max_concurrent_tasks == 1

        task = Task(
            id="task-cap-001",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )

        # Before execution: idle
        hb_idle = worker.heartbeat()
        assert hb_idle.metrics.active_tasks == 0

        # During execution: busy
        worker._current_task = task
        hb_busy = worker.heartbeat()
        assert hb_busy.metrics.active_tasks == 1
        assert hb_busy.status == WorkerStatus.BUSY

    def test_worker_accepts_next_after_completion(self):
        worker = FakeLinuxWorker(worker_id="w-cap-002")

        task1 = Task(
            id="task-cap-002",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        result1 = worker.execute(task1, outcome="success")
        assert result1["status"] == "succeeded"

        task2 = Task(
            id="task-cap-003",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        result2 = worker.execute(task2, outcome="success")
        assert result2["status"] == "succeeded"
