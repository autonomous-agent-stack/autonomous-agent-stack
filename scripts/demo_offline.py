#!/usr/bin/env python3
"""Offline demo runner — exercises the unified contracts without real workers.

Usage:
    PYTHONPATH=src python scripts/demo_offline.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}


def _color(text: str, color: str) -> str:
    return f"{_COLORS.get(color, '')}{text}{_COLORS['reset']}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _section(title: str) -> None:
    print()
    print(_color(f"{'=' * 60}", "bold"))
    print(_color(f"  {title}", "bold"))
    print(_color(f"{'=' * 60}", "bold"))


def _step(msg: str) -> None:
    print(f"  {_color('→', 'blue')} {msg}")


def _ok(msg: str) -> None:
    print(f"  {_color('✓', 'green')} {msg}")


def _fail(msg: str) -> None:
    print(f"  {_color('✗', 'red')} {msg}")


def _warn(msg: str) -> None:
    print(f"  {_color('⚠', 'yellow')} {msg}")


def _json_dump(obj) -> str:
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
    elif isinstance(obj, dict):
        data = obj
    else:
        data = str(obj)
    return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# Demo scenarios
# ---------------------------------------------------------------------------


def demo_success_flow() -> None:
    """Scenario 1: Happy path — task succeeds through the full lifecycle."""
    _section("SCENARIO 1: Success Flow (queued → leased → running → succeeded)")

    # Worker registration
    worker = WorkerRegistration(
        worker_id="linux-housekeeper-01",
        name="Linux Housekeeper #1",
        worker_type=WorkerType.LINUX,
        capabilities=["shell", "script_runner"],
        allowed_actions=[AllowedAction.EXECUTE_TASK, AllowedAction.RUN_SCRIPT],
        status=WorkerStatus.ONLINE,
    )
    _step(f"Worker registered: {worker.worker_id} ({worker.worker_type.value})")
    _ok(f"Status: {worker.status.value}")

    # Task creation
    req = CreateTaskRequest(
        type="software_change",
        agent_package_id="software-change",
        input={"goal": "Fix the CI pipeline"},
        priority=TaskPriority.HIGH,
        created_by="demo-runner",
    )
    task = Task(
        id="task-001",
        type=req.type,
        agent_package_id=req.agent_package_id,
        input=req.input,
        priority=req.priority,
    )
    _step(f"Task created: {task.id} (status={task.status.value})")

    # Dispatch
    task.status = TaskStatus.QUEUED
    _step(f"Task dispatched: status={task.status.value}")

    # Run lifecycle
    run = RunRecord(
        run_id="run-001",
        task_id=task.id,
        worker_id=worker.worker_id,
        status=RunStatus.QUEUED,
        queued_at=_now(),
    )
    _step(f"Run created: {run.run_id} (status={run.status.value})")

    run.transition_to(RunStatus.LEASED)
    run.leased_at = _now()
    _step(f"Run leased by worker: status={run.status.value}")

    # Heartbeat during execution
    hb = WorkerHeartbeat(
        worker_id=worker.worker_id,
        status=WorkerStatus.BUSY,
        metrics=WorkerMetrics(cpu_usage_percent=42.0, active_tasks=1),
        active_task_ids=[task.id],
    )
    _step(f"Heartbeat: worker={hb.status.value}, cpu={hb.metrics.cpu_usage_percent}%")

    run.transition_to(RunStatus.RUNNING)
    run.started_at = _now()
    _step(f"Run started: status={run.status.value}")

    # Completion
    run.transition_to(RunStatus.SUCCEEDED)
    run.completed_at = _now()
    task.result = TaskResult(success=True, data={"files_changed": 3})
    task.status = TaskStatus.SUCCEEDED
    _ok(f"Run succeeded: {run.status.value}")
    _ok(f"Task succeeded: {task.status.value}, result={task.result.data}")

    # Gate evaluation
    verdict = make_gate_verdict(
        GateOutcome.SUCCESS,
        reason="All checks passed",
        checks=[
            GateCheck(check_id="output_exists", passed=True),
            GateCheck(check_id="tests_pass", passed=True),
        ],
    )
    _ok(f"Gate verdict: outcome={verdict.outcome.value}, action={verdict.action.value}")
    _ok(f"All checks passed: {verdict.all_checks_passed}")


def demo_failure_flow() -> None:
    """Scenario 2: Failure — task times out, gate recommends retry."""
    _section("SCENARIO 2: Failure Flow (queued → leased → running → failed)")

    task = Task(
        id="task-002",
        type="linux_housekeeping",
        agent_package_id="linux-hk",
        status=TaskStatus.PENDING,
        priority=TaskPriority.MEDIUM,
    )
    task.status = TaskStatus.QUEUED
    _step(f"Task created and queued: {task.id}")

    run = RunRecord(
        run_id="run-002", task_id=task.id, worker_id="linux-housekeeper-01", status=RunStatus.QUEUED
    )
    run.transition_to(RunStatus.LEASED)
    run.transition_to(RunStatus.RUNNING)
    _step(f"Run started: {run.run_id}")

    # Timeout
    run.transition_to(RunStatus.FAILED)
    run.error_message = "Worker timed out after 900s"
    task.error = TaskError(
        code="TIMEOUT", message="Worker timed out", retryable=True, suggested_action="retry"
    )
    task.status = TaskStatus.FAILED
    _fail(f"Run failed: {run.error_message}")
    _warn(f"Task error: code={task.error.code}, retryable={task.error.retryable}")

    # Gate evaluation
    verdict = make_gate_verdict(
        GateOutcome.TIMEOUT,
        reason="Worker exceeded 900s timeout",
        checks=[
            GateCheck(check_id="timeout", passed=False, detail="900s exceeded", severity="critical")
        ],
        retry_attempt=0,
        max_retries=3,
    )
    _step(f"Gate verdict: outcome={verdict.outcome.value}, action={verdict.action.value}")
    _ok(f"Can retry: {verdict.can_retry} (attempt {verdict.retry_attempt}/{verdict.max_retries})")


def demo_review_flow() -> None:
    """Scenario 3: Needs review — gate escalates to human."""
    _section("SCENARIO 3: Review Flow (queued → leased → running → needs_review)")

    run = RunRecord(run_id="run-003", task_id="task-003", worker_id="openclaw-runtime-01")
    run.transition_to(RunStatus.LEASED)
    run.transition_to(RunStatus.RUNNING)
    run.transition_to(RunStatus.NEEDS_REVIEW)
    _warn(f"Run needs review: {run.run_id} (status={run.status.value})")

    verdict = make_gate_verdict(
        GateOutcome.NEEDS_HUMAN_CONFIRM,
        reason="Agent modified production config — requires manual approval",
    )
    _step(f"Gate verdict: outcome={verdict.outcome.value}, action={verdict.action.value}")

    # Human approves
    task = Task(
        id="task-003",
        type="software_change",
        agent_package_id="software-change",
        requires_approval=True,
        status=TaskStatus.APPROVAL_REQUIRED,
    )
    _step(f"Task awaiting approval: {task.id}")
    task.approval_status = ApprovalStatus.APPROVED
    task.status = TaskStatus.QUEUED
    _ok(f"Human approved! Task re-queued: status={task.status.value}")

    # Run resolved
    run.transition_to(RunStatus.SUCCEEDED)
    _ok(f"Run resolved to: {run.status.value}")


def demo_rejection_flow() -> None:
    """Scenario 4: Rejection — overreach detected, gate rejects."""
    _section("SCENARIO 4: Rejection Flow (overreach → reject)")

    verdict = make_gate_verdict(
        GateOutcome.OVERREACH,
        reason="Agent modified files outside the allowed scope",
        checks=[
            GateCheck(
                check_id="scope_check",
                passed=False,
                detail="Modified /etc/passwd",
                severity="critical",
            ),
            GateCheck(check_id="file_whitelist", passed=True),
        ],
    )
    _fail(f"Gate verdict: outcome={verdict.outcome.value}, action={verdict.action.value}")
    _fail(f"Reason: {verdict.reason}")
    for check in verdict.checks:
        icon = _color("✓", "green") if check.passed else _color("✗", "red")
        print(
            f"    {icon} {check.check_id}: {check.detail or ('passed' if check.passed else 'FAILED')}"
        )


def demo_retry_exhaustion_flow() -> None:
    """Scenario 5: Retry exhaustion — auto-upgrades to fallback."""
    _section("SCENARIO 5: Retry Exhaustion (retry → fallback)")

    # Retry 1
    v1 = make_gate_verdict(
        GateOutcome.TIMEOUT,
        reason="Timeout attempt 1",
        retry_attempt=0,
        max_retries=3,
        fallback_agent_id="fallback-hk",
    )
    _step(f"Attempt 1: action={v1.action.value}, can_retry={v1.can_retry}")

    # Retry 2
    v2 = make_gate_verdict(
        GateOutcome.TIMEOUT,
        reason="Timeout attempt 2",
        retry_attempt=1,
        max_retries=3,
        fallback_agent_id="fallback-hk",
    )
    _step(f"Attempt 2: action={v2.action.value}, can_retry={v2.can_retry}")

    # Retry 3 (exhausted)
    v3 = make_gate_verdict(
        GateOutcome.TIMEOUT,
        reason="Timeout attempt 3 — exhausted",
        retry_attempt=3,
        max_retries=3,
        fallback_agent_id="fallback-hk",
    )
    _warn(f"Attempt 3: RETRIES EXHAUSTED — auto-upgraded to action={v3.action.value}")
    _step(f"Fallback agent: {v3.fallback_agent_id}")
    _ok("Correctly upgraded to FALLBACK (not RETRY)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    print(_color("╔══════════════════════════════════════════════════════════╗", "bold"))
    print(_color("║       Autonomous Agent Stack — Offline Demo Runner      ║", "bold"))
    print(_color("║       No real worker connections — mock data only        ║", "bold"))
    print(_color("╚══════════════════════════════════════════════════════════╝", "bold"))

    scenarios = [
        ("Success Flow", demo_success_flow),
        ("Failure Flow", demo_failure_flow),
        ("Review Flow", demo_review_flow),
        ("Rejection Flow", demo_rejection_flow),
        ("Retry Exhaustion", demo_retry_exhaustion_flow),
    ]

    passed = 0
    failed = 0
    for name, fn in scenarios:
        try:
            fn()
            passed += 1
        except Exception as exc:
            _fail(f"Scenario '{name}' raised: {exc}")
            failed += 1

    _section("SUMMARY")
    print(
        f"  Scenarios: {_color(str(passed), 'green')} passed, {_color(str(failed), 'red')} failed"
    )
    if failed == 0:
        _ok("All demo scenarios passed!")
    else:
        _fail(f"{failed} scenario(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
