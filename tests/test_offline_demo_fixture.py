"""A1: Offline demo fixture — success and failure flows.

Demonstrates the full lifecycle of tasks, runs, workers, and gate verdicts
using only unified contract models.  No real worker connections.
"""

from __future__ import annotations

from datetime import datetime, timezone

from autoresearch.shared.run_contract import RunRecord, RunStatus
from autoresearch.shared.task_contract import (
    ApprovalStatus,
    CreateTaskRequest,
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
    GateVerdict,
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

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_worker(
    worker_id: str = "linux-housekeeper-01", status: WorkerStatus = WorkerStatus.ONLINE
) -> WorkerRegistration:
    return WorkerRegistration(
        worker_id=worker_id,
        name="Linux Housekeeper #1",
        worker_type=WorkerType.LINUX,
        capabilities=["shell", "script_runner", "log_collection"],
        allowed_actions=[AllowedAction.EXECUTE_TASK, AllowedAction.RUN_SCRIPT],
        status=status,
        backend_kind="linux_supervisor",
    )


def _make_task(task_id: str = "task-001", status: TaskStatus = TaskStatus.PENDING) -> Task:
    return Task(
        id=task_id,
        type="software_change",
        agent_package_id="software-change",
        status=status,
        created_by="demo-fixture",
        tags=["demo"],
    )


def _make_run(run_id: str = "run-001", task_id: str = "task-001") -> RunRecord:
    return RunRecord(
        run_id=run_id,
        task_id=task_id,
        worker_id="linux-housekeeper-01",
        status=RunStatus.QUEUED,
        queued_at=_now(),
    )


# ===================================================================
# SUCCESS FLOW: task queued → leased → running → succeeded
# ===================================================================


class TestSuccessFlow:
    """Walk a task and its run through the happy path."""

    def test_worker_registers_online(self):
        worker = _make_worker()
        assert worker.status == WorkerStatus.ONLINE
        assert WorkerType.LINUX in [worker.worker_type]
        assert "shell" in worker.capabilities

    def test_task_created_as_pending(self):
        req = CreateTaskRequest(
            type="software_change",
            agent_package_id="software-change",
            input={"goal": "Fix the CI pipeline"},
            priority=TaskPriority.HIGH,
            created_by="demo",
            tags=["infra"],
        )
        task = Task(
            id="task-001",
            type=req.type,
            agent_package_id=req.agent_package_id,
            input=req.input,
            priority=req.priority,
            tags=req.tags,
        )
        assert task.status == TaskStatus.PENDING

    def test_task_dispatched_to_queued(self):
        task = _make_task()
        task.status = TaskStatus.QUEUED
        assert task.status == TaskStatus.QUEUED

    def test_run_created_and_leased(self):
        run = _make_run()
        assert run.status == RunStatus.QUEUED
        run.transition_to(RunStatus.LEASED)
        assert run.status == RunStatus.LEASED
        run.leased_at = _now()

    def test_run_transitions_to_running(self):
        run = _make_run()
        run.transition_to(RunStatus.LEASED)
        run.transition_to(RunStatus.RUNNING)
        run.started_at = _now()
        assert run.status == RunStatus.RUNNING

    def test_run_succeeds(self):
        run = _make_run()
        run.transition_to(RunStatus.LEASED)
        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.SUCCEEDED)
        run.completed_at = _now()
        assert run.status == RunStatus.SUCCEEDED

    def test_task_succeeded_with_result(self):
        task = _make_task()
        task.status = TaskStatus.QUEUED
        task.status = TaskStatus.RUNNING
        task.result = TaskResult(success=True, data={"files_changed": 3})
        task.status = TaskStatus.SUCCEEDED
        assert task.status == TaskStatus.SUCCEEDED
        assert task.result.success is True
        assert task.result.data["files_changed"] == 3

    def test_gate_accepts_successful_run(self):
        verdict = make_gate_verdict(
            GateOutcome.SUCCESS,
            reason="All checks passed",
            checks=[
                GateCheck(check_id="output_exists", passed=True),
                GateCheck(check_id="tests_pass", passed=True),
            ],
        )
        assert verdict.action == GateAction.ACCEPT
        assert verdict.all_checks_passed is True

    def test_worker_heartbeat_during_run(self):
        hb = WorkerHeartbeat(
            worker_id="linux-housekeeper-01",
            status=WorkerStatus.BUSY,
            metrics=WorkerMetrics(cpu_usage_percent=45.0, memory_usage_mb=512, active_tasks=1),
            active_task_ids=["task-001"],
        )
        assert hb.status == WorkerStatus.BUSY
        assert "task-001" in hb.active_task_ids


# ===================================================================
# FAILURE / REVIEW FLOW: queued → leased → running → needs_review
# ===================================================================


class TestFailureReviewFlow:
    """Walk a task that fails the gate and needs human review."""

    def test_run_goes_to_needs_review(self):
        run = _make_run()
        run.transition_to(RunStatus.LEASED)
        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.NEEDS_REVIEW)
        assert run.status == RunStatus.NEEDS_REVIEW

    def test_gate_flags_overreach(self):
        verdict = make_gate_verdict(
            GateOutcome.OVERREACH,
            reason="Agent modified files outside allowed scope",
            checks=[
                GateCheck(check_id="scope_check", passed=False, severity="critical"),
            ],
        )
        assert verdict.action == GateAction.REJECT
        assert verdict.all_checks_passed is False

    def test_gate_flags_timeout(self):
        verdict = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Worker exceeded 900s timeout",
            checks=[
                GateCheck(check_id="timeout", passed=False, severity="critical"),
            ],
            retry_attempt=0,
            max_retries=3,
        )
        assert verdict.action == GateAction.RETRY
        assert verdict.can_retry is True

    def test_gate_flags_missing_artifacts(self):
        verdict = make_gate_verdict(
            GateOutcome.MISSING_ARTIFACTS,
            reason="Expected screenshot artifact not found",
            checks=[
                GateCheck(check_id="screenshot_exists", passed=False),
            ],
            retry_attempt=0,
            max_retries=3,
        )
        assert verdict.action == GateAction.RETRY

    def test_gate_escalates_to_human(self):
        verdict = make_gate_verdict(
            GateOutcome.NEEDS_HUMAN_CONFIRM,
            reason="Agent requested manual verification of production change",
        )
        assert verdict.action == GateAction.NEEDS_REVIEW

    def test_task_with_approval_required(self):
        task = Task(
            id="task-approval",
            type="software_change",
            agent_package_id="software-change",
            status=TaskStatus.PENDING,
            requires_approval=True,
            priority=TaskPriority.HIGH,
        )
        task.status = TaskStatus.APPROVAL_REQUIRED
        assert task.status == TaskStatus.APPROVAL_REQUIRED
        task.approval_status = ApprovalStatus.APPROVED
        task.status = TaskStatus.QUEUED
        assert task.status == TaskStatus.QUEUED

    def test_task_rejected(self):
        task = Task(
            id="task-rejected",
            type="software_change",
            agent_package_id="software-change",
            status=TaskStatus.APPROVAL_REQUIRED,
            requires_approval=True,
        )
        task.approval_status = ApprovalStatus.REJECTED
        task.status = TaskStatus.REJECTED
        assert task.status == TaskStatus.REJECTED

    def test_run_fails_with_error(self):
        run = _make_run()
        run.transition_to(RunStatus.LEASED)
        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.FAILED)
        run.error_message = "Worker timed out after 900s"
        assert run.status == RunStatus.FAILED
        assert "timed out" in run.error_message

    def test_task_failed_with_error_object(self):
        task = _make_task()
        task.status = TaskStatus.QUEUED
        task.status = TaskStatus.RUNNING
        task.error = TaskError(
            code="TIMEOUT",
            message="Worker timed out",
            retryable=True,
            suggested_action="retry",
        )
        task.status = TaskStatus.FAILED
        assert task.status == TaskStatus.FAILED
        assert task.error.retryable is True


# ===================================================================
# RETRY EXHAUSTION FLOW
# ===================================================================


class TestRetryExhaustionFlow:
    """When retries are exhausted, the gate should auto-upgrade to fallback."""

    def test_retry_exhaustion_upgrades_to_fallback(self):
        verdict = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Timeout on final attempt",
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="fallback-agent",
        )
        assert verdict.action == GateAction.FALLBACK
        assert verdict.can_retry is False

    def test_retry_exhaustion_no_fallback_available(self):
        verdict = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Timeout, no fallback agent configured",
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id=None,
        )
        assert verdict.action == GateAction.NEEDS_REVIEW

    def test_needs_review_resolved_to_succeeded(self):
        run = _make_run()
        run.transition_to(RunStatus.LEASED)
        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.NEEDS_REVIEW)
        run.transition_to(RunStatus.SUCCEEDED)
        assert run.status == RunStatus.SUCCEEDED

    def test_needs_review_resolved_to_failed(self):
        run = _make_run()
        run.transition_to(RunStatus.LEASED)
        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.NEEDS_REVIEW)
        run.transition_to(RunStatus.FAILED)
        assert run.status == RunStatus.FAILED


# ===================================================================
# DEMO FIXTURE BUNDLE (used by demo runner script)
# ===================================================================


class DemoFixtureBundle:
    """Pre-built demo data bundle for the offline demo runner."""

    def __init__(self) -> None:
        self.workers = self._build_workers()
        self.tasks = self._build_tasks()
        self.runs = self._build_runs()
        self.gate_verdicts = self._build_gate_verdicts()

    def _build_workers(self) -> dict[str, WorkerRegistration]:
        return {
            "linux-housekeeper-01": _make_worker("linux-housekeeper-01", WorkerStatus.ONLINE),
            "openclaw-runtime-01": WorkerRegistration(
                worker_id="openclaw-runtime-01",
                name="OpenClaw Runtime #1",
                worker_type=WorkerType.OPENCLAW,
                capabilities=["conversation", "skill_execution"],
                status=WorkerStatus.DEGRADED,
                backend_kind="openclaw_runtime",
            ),
            "win-yingdao-01": WorkerRegistration(
                worker_id="win-yingdao-01",
                name="Windows Yingdao #1",
                worker_type=WorkerType.WIN_YINGDAO,
                capabilities=["yingdao_flow", "form_fill"],
                status=WorkerStatus.OFFLINE,
                backend_kind="win_yingdao",
            ),
        }

    def _build_tasks(self) -> dict[str, Task]:
        return {
            "task-001": Task(
                id="task-001",
                type="software_change",
                agent_package_id="software-change",
                status=TaskStatus.SUCCEEDED,
                priority=TaskPriority.HIGH,
                worker_id="linux-housekeeper-01",
                result=TaskResult(success=True, data={"files_changed": 3}),
                tags=["infra", "demo"],
            ),
            "task-002": Task(
                id="task-002",
                type="linux_housekeeping",
                agent_package_id="linux-housekeeping",
                status=TaskStatus.FAILED,
                priority=TaskPriority.MEDIUM,
                worker_id="linux-housekeeper-01",
                error=TaskError(code="TIMEOUT", message="Worker timed out", retryable=True),
                tags=["ops", "demo"],
            ),
            "task-003": Task(
                id="task-003",
                type="form_fill",
                agent_package_id="form-fill",
                status=TaskStatus.APPROVAL_REQUIRED,
                requires_approval=True,
                priority=TaskPriority.LOW,
                tags=["yingdao", "demo"],
            ),
        }

    def _build_runs(self) -> dict[str, RunRecord]:
        run_001 = RunRecord(
            run_id="run-001",
            task_id="task-001",
            worker_id="linux-housekeeper-01",
            status=RunStatus.SUCCEEDED,
        )
        run_002 = RunRecord(
            run_id="run-002",
            task_id="task-002",
            worker_id="linux-housekeeper-01",
            status=RunStatus.FAILED,
            error_message="Worker timed out after 900s",
        )
        run_003 = RunRecord(
            run_id="run-003",
            task_id="task-002",
            worker_id="linux-housekeeper-01",
            status=RunStatus.QUEUED,
            attempt=2,
        )
        return {"run-001": run_001, "run-002": run_002, "run-003": run_003}

    def _build_gate_verdicts(self) -> dict[str, GateVerdict]:
        return {
            "run-001": make_gate_verdict(
                GateOutcome.SUCCESS,
                reason="All checks passed",
                checks=[
                    GateCheck(check_id="output_exists", passed=True),
                    GateCheck(check_id="tests_pass", passed=True),
                ],
            ),
            "run-002": make_gate_verdict(
                GateOutcome.TIMEOUT,
                reason="Worker exceeded 900s timeout",
                checks=[
                    GateCheck(check_id="timeout", passed=False, severity="critical"),
                ],
                retry_attempt=0,
                max_retries=3,
            ),
        }


class TestDemoFixtureBundle:
    def test_bundle_instantiates(self):
        bundle = DemoFixtureBundle()
        assert len(bundle.workers) == 3
        assert len(bundle.tasks) == 3
        assert len(bundle.runs) == 3
        assert len(bundle.gate_verdicts) == 2

    def test_success_task_has_result(self):
        bundle = DemoFixtureBundle()
        task = bundle.tasks["task-001"]
        assert task.result is not None
        assert task.result.success is True

    def test_failed_task_has_error(self):
        bundle = DemoFixtureBundle()
        task = bundle.tasks["task-002"]
        assert task.error is not None
        assert task.error.code == "TIMEOUT"

    def test_approval_task_is_pending_approval(self):
        bundle = DemoFixtureBundle()
        task = bundle.tasks["task-003"]
        assert task.status == TaskStatus.APPROVAL_REQUIRED
        assert task.requires_approval is True
