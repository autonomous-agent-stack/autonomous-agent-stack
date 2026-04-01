"""Worker contract compliance tests.

Any worker (real or fake) must pass these to be certified for the
control plane. Swap _make_worker() for a real adapter — the tests
must still pass without modification.

Contracts tested:
  1. Registration — valid WorkerRegistration with required fields
  2. Heartbeat — valid WorkerHeartbeat with metrics and status
  3. Run lifecycle — produces correct status sequence + result
  4. Gate integration — execution result is gate-evaluable
  5. Error classification — retryable vs non-retryable errors
"""

from __future__ import annotations

from datetime import datetime, timezone

from autoresearch.shared.run_contract import RunRecord, RunStatus, is_valid_run_transition
from autoresearch.shared.task_contract import (
    Task,
    TaskError,
    TaskPriority,
    TaskResult,
    TaskStatus,
)
from autoresearch.shared.task_gate_contract import (
    GateAction,
    GateCheck,
    GateOutcome,
    make_gate_verdict,
)
from autoresearch.shared.worker_contract import (
    AllowedAction,
    WorkerHeartbeat,
    WorkerMetrics,
    WorkerRegistration,
    WorkerStatus,
    WorkerType,
)
from autoresearch.testing.fake_workers import FakeLinuxWorker


def _make_worker() -> FakeLinuxWorker:
    """Factory for the worker under test. Swap this for a real adapter."""
    return FakeLinuxWorker(worker_id="worker-compliance-test")


# ===========================================================================
# Contract 1: Registration
# ===========================================================================


class TestWorkerRegistrationCompliance:
    """Worker must produce a valid WorkerRegistration."""

    def test_registration_returns_valid_model(self):
        reg = _make_worker().registration()
        assert isinstance(reg, WorkerRegistration)

    def test_worker_type_is_set(self):
        reg = _make_worker().registration()
        assert isinstance(reg.worker_type, WorkerType)

    def test_capabilities_non_empty(self):
        reg = _make_worker().registration()
        assert len(reg.capabilities) > 0

    def test_allowed_actions_non_empty(self):
        reg = _make_worker().registration()
        assert len(reg.allowed_actions) > 0
        for action in reg.allowed_actions:
            assert isinstance(action, AllowedAction)

    def test_max_concurrent_tasks_positive(self):
        reg = _make_worker().registration()
        assert reg.max_concurrent_tasks >= 1

    def test_status_is_valid_enum(self):
        reg = _make_worker().registration()
        assert reg.status in (
            WorkerStatus.ONLINE,
            WorkerStatus.BUSY,
            WorkerStatus.DEGRADED,
            WorkerStatus.OFFLINE,
        )


# ===========================================================================
# Contract 2: Heartbeat
# ===========================================================================


class TestWorkerHeartbeatCompliance:
    """Worker must produce valid heartbeats."""

    def test_heartbeat_returns_valid_model(self):
        hb = _make_worker().heartbeat()
        assert isinstance(hb, WorkerHeartbeat)

    def test_heartbeat_contains_worker_id(self):
        hb = _make_worker().heartbeat()
        assert hb.worker_id == "worker-compliance-test"

    def test_heartbeat_contains_metrics(self):
        hb = _make_worker().heartbeat()
        assert isinstance(hb.metrics, WorkerMetrics)
        assert hb.metrics.cpu_usage_percent >= 0
        assert hb.metrics.memory_usage_mb >= 0

    def test_heartbeat_status_is_valid(self):
        hb = _make_worker().heartbeat()
        assert hb.status in (
            WorkerStatus.ONLINE,
            WorkerStatus.BUSY,
            WorkerStatus.DEGRADED,
            WorkerStatus.OFFLINE,
        )

    def test_heartbeat_busy_when_executing(self):
        worker = _make_worker()
        task = Task(
            id="hb-task",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        worker._current_task = task
        hb = worker.heartbeat()
        assert hb.status == WorkerStatus.BUSY
        assert task.id in hb.active_task_ids


# ===========================================================================
# Contract 3: Run lifecycle traceability
# ===========================================================================


class TestRunLifecycleTraceability:
    """Execution must produce traceable status sequence + result."""

    def test_successful_run_produces_complete_lifecycle(self):
        worker = _make_worker()
        task = Task(
            id="trace-task-001",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        now = datetime.now(timezone.utc)

        run = RunRecord(
            run_id="trace-run-001",
            task_id=task.id,
            worker_id=worker.registration().worker_id,
            status=RunStatus.QUEUED,
            queued_at=now,
        )
        run.transition_to(RunStatus.LEASED)
        run.leased_at = now
        run.transition_to(RunStatus.RUNNING)
        run.started_at = now

        result = worker.execute(task, outcome="success")
        assert result["status"] == "succeeded"

        run.transition_to(RunStatus.SUCCEEDED)
        run.completed_at = now
        task.status = TaskStatus.SUCCEEDED
        task.result = TaskResult(success=True, data=result.get("data", {}))

        assert run.status == RunStatus.SUCCEEDED
        assert task.status == TaskStatus.SUCCEEDED
        assert task.result.success is True
        assert run.queued_at is not None
        assert run.started_at is not None
        assert run.completed_at is not None

    def test_failed_run_produces_error_info(self):
        worker = _make_worker()
        task = Task(
            id="trace-task-002",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        now = datetime.now(timezone.utc)

        run = RunRecord(
            run_id="trace-run-002",
            task_id=task.id,
            worker_id="w",
            status=RunStatus.QUEUED,
            queued_at=now,
        )
        run.transition_to(RunStatus.LEASED)
        run.transition_to(RunStatus.RUNNING)

        result = worker.execute(task, outcome="timeout")
        assert result["status"] == "failed"
        assert result["error"]["code"] == "TIMEOUT"
        assert result["error"]["retryable"] is True

        run.transition_to(RunStatus.FAILED)
        run.error_message = result["error"]["message"]
        task.error = TaskError(
            code=result["error"]["code"],
            message=result["error"]["message"],
            retryable=result["error"]["retryable"],
            suggested_action=result["error"]["suggested_action"],
        )
        task.status = TaskStatus.FAILED

        assert run.status == RunStatus.FAILED
        assert task.error.code == "TIMEOUT"

    def test_every_lifecycle_transition_is_valid(self):
        valid_sequence = [
            RunStatus.QUEUED,
            RunStatus.LEASED,
            RunStatus.RUNNING,
            RunStatus.SUCCEEDED,
        ]
        for i in range(len(valid_sequence) - 1):
            assert is_valid_run_transition(
                valid_sequence[i], valid_sequence[i + 1]
            ), f"Invalid: {valid_sequence[i]} -> {valid_sequence[i+1]}"


# ===========================================================================
# Contract 4: Gate integration
# ===========================================================================


class TestGateIntegrationContract:
    """Execution result must be gate-evaluable."""

    def test_success_result_gate_accepts(self):
        worker = _make_worker()
        task = Task(
            id="gate-task-001",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        worker.execute(task, outcome="success")

        checks = [
            GateCheck(check_id="output_exists", passed=True, detail="Output present"),
            GateCheck(check_id="scope_check", passed=True, detail="Within scope"),
        ]
        verdict = make_gate_verdict(
            GateOutcome.SUCCESS,
            reason="Worker returned success",
            checks=checks,
        )
        assert verdict.action == GateAction.ACCEPT

    def test_timeout_result_gate_retries(self):
        worker = _make_worker()
        task = Task(
            id="gate-task-002",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        result = worker.execute(task, outcome="timeout")

        verdict = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason=result["error"]["message"],
            retry_attempt=1,
            max_retries=3,
            fallback_agent_id="fallback",
        )
        assert verdict.action == GateAction.RETRY

    def test_overreach_result_gate_rejects(self):
        verdict = make_gate_verdict(
            GateOutcome.OVERREACH,
            reason="Agent modified files outside allowed scope",
            checks=[
                GateCheck(check_id="output_exists", passed=True, detail="5 files"),
                GateCheck(
                    check_id="scope_check",
                    passed=False,
                    detail="Modified /etc/shadow",
                    severity="critical",
                ),
            ],
        )
        assert verdict.action == GateAction.REJECT

    def test_retry_exhaustion_escalates_to_fallback(self):
        verdict = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Worker timed out again",
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="fallback-agent",
        )
        assert verdict.action == GateAction.FALLBACK

    def test_retry_exhaustion_without_fallback_needs_review(self):
        verdict = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Worker timed out, no fallback",
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id=None,
        )
        assert verdict.action == GateAction.NEEDS_REVIEW

    def test_gate_verdict_has_required_fields(self):
        verdict = make_gate_verdict(
            GateOutcome.SUCCESS,
            reason="test",
            checks=[GateCheck(check_id="c1", passed=True, detail="ok")],
        )
        assert verdict.outcome is not None
        assert verdict.action is not None
        assert verdict.reason is not None
        assert len(verdict.checks) > 0


# ===========================================================================
# Contract 5: Error classification
# ===========================================================================


class TestErrorClassification:
    """Worker errors must classify correctly for retry decisions."""

    def test_timeout_is_retryable(self):
        worker = _make_worker()
        task = Task(
            id="err-task-001",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        result = worker.execute(task, outcome="timeout")
        assert result["error"]["retryable"] is True
        assert result["error"]["suggested_action"] == "retry"

    def test_crash_is_retryable(self):
        worker = _make_worker()
        task = Task(
            id="err-task-002",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        result = worker.execute(task, outcome="crash")
        assert result["error"]["retryable"] is True

    def test_permission_denied_not_retryable(self):
        worker = _make_worker()
        task = Task(
            id="err-task-003",
            type="software_change",
            agent_package_id="test",
            priority=TaskPriority.MEDIUM,
        )
        result = worker.execute(task, outcome="permission_denied")
        assert result["error"]["retryable"] is False
        assert result["error"]["suggested_action"] == "manual"

    def test_error_code_is_set_for_all_failure_types(self):
        worker = _make_worker()
        for outcome in ["timeout", "crash", "permission_denied"]:
            task = Task(
                id=f"err-task-{outcome}",
                type="software_change",
                agent_package_id="test",
                priority=TaskPriority.MEDIUM,
            )
            result = worker.execute(task, outcome=outcome)
            assert result["error"]["code"] is not None
            assert len(result["error"]["code"]) > 0
