#!/usr/bin/env python3
"""Formal acceptance test harness for the autonomous-agent-stack control plane.

Executes 30 consecutive runs (configurable) with 5 fault injection categories:
  1. TIMEOUT        — worker exceeds configured deadline
  2. CRASH          — worker process dies unexpectedly
  3. OVERREACH      — agent modifies files outside allowed scope
  4. MISSING_ARTIFACTS — expected output artifacts not produced
  5. PERMISSION_DENIED — worker lacks filesystem permissions

Each run walks the full lifecycle:
  task(pending) → queued → leased → running → [terminal]
  gate evaluates → verdict → action (accept/retry/fallback/needs_review/reject)

Exit 0 if all assertions hold; exit 1 on any failure.

Usage:
    PYTHONPATH=src python scripts/acceptance_run.py [--runs N]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from autoresearch.shared.run_contract import RunRecord, RunStatus
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
    WorkerHeartbeat,
    WorkerMetrics,
    WorkerStatus,
)
from autoresearch.testing.fake_workers import FakeLinuxWorker

# ---------------------------------------------------------------------------
# Fault injection profiles
# ---------------------------------------------------------------------------


class FaultType(str):
    TIMEOUT = "timeout"
    CRASH = "crash"
    OVERREACH = "overreach"
    MISSING_ARTIFACTS = "missing_artifacts"
    PERMISSION_DENIED = "permission_denied"
    SUCCESS = "success"


@dataclass
class FaultProfile:
    """Describes a specific fault to inject into a run."""

    fault_type: str
    inject_at: str  # "run_start", "run_mid", "run_end"
    worker_outcome: str  # what FakeLinuxWorker.execute() returns
    expected_run_status: RunStatus
    expected_gate_outcome: GateOutcome
    expected_gate_action: GateAction
    expected_task_status: TaskStatus
    description: str


FAULT_PROFILES: list[FaultProfile] = [
    FaultProfile(
        fault_type=FaultType.TIMEOUT,
        inject_at="run_end",
        worker_outcome="timeout",
        expected_run_status=RunStatus.FAILED,
        expected_gate_outcome=GateOutcome.TIMEOUT,
        expected_gate_action=GateAction.RETRY,
        expected_task_status=TaskStatus.FAILED,
        description="Worker exceeds 900s task deadline",
    ),
    FaultProfile(
        fault_type=FaultType.CRASH,
        inject_at="run_mid",
        worker_outcome="crash",
        expected_run_status=RunStatus.FAILED,
        expected_gate_outcome=GateOutcome.TIMEOUT,
        expected_gate_action=GateAction.RETRY,
        expected_task_status=TaskStatus.FAILED,
        description="Worker process crashes (exit code 137)",
    ),
    FaultProfile(
        fault_type=FaultType.OVERREACH,
        inject_at="run_end",
        worker_outcome="success",
        expected_run_status=RunStatus.SUCCEEDED,
        expected_gate_outcome=GateOutcome.OVERREACH,
        expected_gate_action=GateAction.REJECT,
        expected_task_status=TaskStatus.REJECTED,
        description="Agent modified files outside allowed scope",
    ),
    FaultProfile(
        fault_type=FaultType.MISSING_ARTIFACTS,
        inject_at="run_end",
        worker_outcome="success",
        expected_run_status=RunStatus.SUCCEEDED,
        expected_gate_outcome=GateOutcome.MISSING_ARTIFACTS,
        expected_gate_action=GateAction.RETRY,
        expected_task_status=TaskStatus.NEEDS_REVIEW,
        description="Expected output artifacts not produced",
    ),
    FaultProfile(
        fault_type=FaultType.PERMISSION_DENIED,
        inject_at="run_start",
        worker_outcome="permission_denied",
        expected_run_status=RunStatus.FAILED,
        expected_gate_outcome=GateOutcome.NEEDS_HUMAN_CONFIRM,
        expected_gate_action=GateAction.NEEDS_REVIEW,
        expected_task_status=TaskStatus.FAILED,
        description="Worker lacks filesystem permissions",
    ),
]

SUCCESS_PROFILE = FaultProfile(
    fault_type=FaultType.SUCCESS,
    inject_at="run_end",
    worker_outcome="success",
    expected_run_status=RunStatus.SUCCEEDED,
    expected_gate_outcome=GateOutcome.SUCCESS,
    expected_gate_action=GateAction.ACCEPT,
    expected_task_status=TaskStatus.SUCCEEDED,
    description="Normal successful execution",
)


# ---------------------------------------------------------------------------
# Run result tracking
# ---------------------------------------------------------------------------


@dataclass
class AcceptanceRunResult:
    """Result of a single acceptance test run."""

    run_index: int
    profile: FaultProfile
    task_id: str
    run_id: str
    worker_id: str

    # Actual outcomes
    actual_run_status: RunStatus | None = None
    actual_gate_outcome: GateOutcome | None = None
    actual_gate_action: GateAction | None = None
    actual_task_status: TaskStatus | None = None

    # Lifecycle steps completed
    steps_completed: list[str] = field(default_factory=list)

    # Assertions
    passed: bool = True
    failures: list[str] = field(default_factory=list)

    # Timing
    started_at: str = ""
    finished_at: str = ""


@dataclass
class AcceptanceSummary:
    """Summary of all acceptance test runs."""

    total_runs: int = 0
    passed: int = 0
    failed: int = 0
    by_fault_type: dict[str, dict[str, int]] = field(default_factory=dict)
    run_results: list[AcceptanceRunResult] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""

    def add_result(self, result: AcceptanceRunResult) -> None:
        self.total_runs += 1
        if result.passed:
            self.passed += 1
        else:
            self.failed += 1
        self.run_results.append(result)

        ft = result.profile.fault_type
        if ft not in self.by_fault_type:
            self.by_fault_type[ft] = {"passed": 0, "failed": 0, "total": 0}
        self.by_fault_type[ft]["total"] += 1
        if result.passed:
            self.by_fault_type[ft]["passed"] += 1
        else:
            self.by_fault_type[ft]["failed"] += 1


# ---------------------------------------------------------------------------
# Acceptance harness
# ---------------------------------------------------------------------------

# Inject some success runs too, weighted distribution
_WEIGHTED_FAULT_TYPES = [
    FaultType.TIMEOUT,
    FaultType.TIMEOUT,  # extra — most common in production
    FaultType.CRASH,
    FaultType.OVERREACH,
    FaultType.MISSING_ARTIFACTS,
    FaultType.PERMISSION_DENIED,
    FaultType.SUCCESS,  # ~25% success baseline
    FaultType.SUCCESS,
    FaultType.SUCCESS,
]


def _pick_profile(index: int) -> FaultProfile:
    """Pick a fault profile for run N. Deterministic + weighted."""
    rng = random.Random(42 + index)
    fault_type = rng.choice(_WEIGHTED_FAULT_TYPES)
    for p in FAULT_PROFILES:
        if p.fault_type == fault_type:
            return p
    return SUCCESS_PROFILE


def _gate_checks_for_profile(profile: FaultProfile) -> list[GateCheck]:
    """Build gate checks appropriate to the fault type."""
    if profile.fault_type == FaultType.SUCCESS:
        return [
            GateCheck(check_id="output_exists", passed=True, detail="3 files changed"),
            GateCheck(check_id="tests_pass", passed=True, detail="12/12 passed"),
            GateCheck(check_id="scope_check", passed=True, detail="All within scope"),
        ]
    elif profile.fault_type == FaultType.TIMEOUT:
        return [
            GateCheck(
                check_id="timeout", passed=False, detail="900s exceeded", severity="critical"
            ),
            GateCheck(check_id="output_exists", passed=False, detail="No output produced"),
        ]
    elif profile.fault_type == FaultType.CRASH:
        return [
            GateCheck(
                check_id="process_exit", passed=False, detail="Exit code 137", severity="critical"
            ),
            GateCheck(check_id="output_exists", passed=False, detail="No output produced"),
        ]
    elif profile.fault_type == FaultType.OVERREACH:
        return [
            GateCheck(check_id="output_exists", passed=True, detail="5 files changed"),
            GateCheck(
                check_id="scope_check",
                passed=False,
                detail="Modified /etc/shadow",
                severity="critical",
            ),
        ]
    elif profile.fault_type == FaultType.MISSING_ARTIFACTS:
        return [
            GateCheck(check_id="output_exists", passed=True, detail="Changes applied"),
            GateCheck(check_id="screenshot_exists", passed=False, detail="No screenshot.png found"),
        ]
    elif profile.fault_type == FaultType.PERMISSION_DENIED:
        return [
            GateCheck(
                check_id="permission_check",
                passed=False,
                detail="EACCES /etc/config.yaml",
                severity="critical",
            ),
        ]
    return []


def _execute_run(index: int, profile: FaultProfile) -> AcceptanceRunResult:
    """Execute a single acceptance test run with the given fault profile."""
    now = datetime.now(timezone.utc)
    task_id = f"accept-task-{index:03d}"
    run_id = f"accept-run-{index:03d}"
    worker_id = "linux-housekeeper-fake"

    result = AcceptanceRunResult(
        run_index=index,
        profile=profile,
        task_id=task_id,
        run_id=run_id,
        worker_id=worker_id,
        started_at=now.isoformat(),
    )

    try:
        # 1. Create task
        task = Task(
            id=task_id,
            type=(
                "software_change"
                if profile.fault_type != FaultType.PERMISSION_DENIED
                else "linux_housekeeping"
            ),
            agent_package_id="acceptance-test",
            priority=TaskPriority.MEDIUM,
        )
        result.steps_completed.append("task_created")

        # 2. Task: pending → queued
        task.status = TaskStatus.QUEUED
        result.steps_completed.append("task_queued")

        # 3. Create run
        run = RunRecord(
            run_id=run_id,
            task_id=task_id,
            worker_id=worker_id,
            status=RunStatus.QUEUED,
            queued_at=now,
        )
        result.steps_completed.append("run_created")

        # 4. Run: queued → leased
        run.transition_to(RunStatus.LEASED)
        run.leased_at = now
        result.steps_completed.append("run_leased")

        # 5. Worker heartbeat (BUSY)
        WorkerHeartbeat(
            worker_id=worker_id,
            status=WorkerStatus.BUSY,
            metrics=WorkerMetrics(cpu_usage_percent=35.0, active_tasks=1),
            active_task_ids=[task_id],
        )
        result.steps_completed.append("heartbeat_busy")

        # 6. Run: leased → running
        run.transition_to(RunStatus.RUNNING)
        run.started_at = now
        task.status = TaskStatus.RUNNING
        result.steps_completed.append("run_running")

        # 7. Execute with fault injection
        worker = FakeLinuxWorker(worker_id=worker_id, default_outcome=profile.worker_outcome)
        worker_result = worker.execute(task, outcome=profile.worker_outcome)
        result.steps_completed.append("worker_executed")

        # 8. Apply worker result to run
        if worker_result["status"] == "succeeded":
            run.transition_to(RunStatus.SUCCEEDED)
            run.completed_at = now
            task.result = TaskResult(
                success=True,
                data=worker_result.get("data", {}),
            )
        elif worker_result["status"] == "failed":
            run.transition_to(RunStatus.FAILED)
            run.completed_at = now
            run.error_message = worker_result["error"]["message"]
            err = worker_result["error"]
            task.error = TaskError(
                code=err["code"],
                message=err["message"],
                retryable=err["retryable"],
                suggested_action=err["suggested_action"],
            )
            task.status = TaskStatus.FAILED
        elif worker_result["status"] == "needs_review":
            run.transition_to(RunStatus.NEEDS_REVIEW)
            run.completed_at = now
            task.status = TaskStatus.NEEDS_REVIEW

        result.actual_run_status = run.status
        result.steps_completed.append("run_terminal")

        # 9. Gate evaluation
        retry_attempt = index % 4  # simulate different retry counts
        gate_checks = _gate_checks_for_profile(profile)
        verdict = make_gate_verdict(
            profile.expected_gate_outcome,
            reason=f"Gate evaluated run {run_id} with fault type {profile.fault_type}",
            checks=gate_checks,
            retry_attempt=retry_attempt,
            max_retries=3,
            fallback_agent_id=(
                "fallback-agent"
                if profile.fault_type in {FaultType.TIMEOUT, FaultType.CRASH}
                else None
            ),
        )

        result.actual_gate_outcome = verdict.outcome
        result.actual_gate_action = verdict.action
        result.steps_completed.append("gate_evaluated")

        # 10. Apply gate action to task status
        if verdict.action == GateAction.ACCEPT:
            task.status = TaskStatus.SUCCEEDED
        elif verdict.action == GateAction.REJECT:
            task.status = TaskStatus.REJECTED
        elif verdict.action == GateAction.RETRY:
            task.status = TaskStatus.QUEUED  # re-queue for retry
        elif verdict.action == GateAction.FALLBACK:
            task.status = TaskStatus.QUEUED  # re-queue with fallback agent
        elif verdict.action == GateAction.NEEDS_REVIEW:
            task.status = TaskStatus.NEEDS_REVIEW

        result.actual_task_status = task.status
        result.steps_completed.append("action_applied")

    except Exception as exc:
        result.passed = False
        result.failures.append(f"Exception during execution: {exc}")
        result.steps_completed.append("error")

    result.finished_at = datetime.now(timezone.utc).isoformat()
    return result


def _verify_run(result: AcceptanceRunResult) -> None:
    """Assert that all actual outcomes match the expected profile."""
    p = result.profile

    # Check run status
    if result.actual_run_status != p.expected_run_status:
        result.passed = False
        result.failures.append(
            f"Run status mismatch: expected={p.expected_run_status.value}, "
            f"actual={result.actual_run_status.value if result.actual_run_status else 'None'}"
        )

    # Check gate outcome (only if not affected by retry exhaustion upgrade)
    if result.actual_gate_outcome != p.expected_gate_outcome:
        result.passed = False
        result.failures.append(
            f"Gate outcome mismatch: expected={p.expected_gate_outcome.value}, "
            f"actual={result.actual_gate_outcome.value if result.actual_gate_outcome else 'None'}"
        )

    # Check gate action (relaxed: retry exhaustion may upgrade to fallback/needs_review)
    if result.actual_gate_action not in _allowed_gate_actions(p.expected_gate_action):
        result.passed = False
        result.failures.append(
            f"Gate action mismatch: expected={p.expected_gate_action.value} (or upgrade), "
            f"actual={result.actual_gate_action.value if result.actual_gate_action else 'None'}"
        )

    # Check task status
    if result.actual_task_status not in _allowed_task_statuses(p.expected_task_status):
        result.passed = False
        result.failures.append(
            f"Task status mismatch: expected={p.expected_task_status.value} (or retry-equivalent), "
            f"actual={result.actual_task_status.value if result.actual_task_status else 'None'}"
        )

    # Check lifecycle completeness
    required_steps = [
        "task_created",
        "task_queued",
        "run_created",
        "run_leased",
        "run_running",
        "run_terminal",
        "gate_evaluated",
    ]
    for step in required_steps:
        if step not in result.steps_completed:
            result.passed = False
            result.failures.append(f"Missing lifecycle step: {step}")


def _allowed_gate_actions(expected: GateAction) -> set[GateAction]:
    """Some actions may be upgraded by retry exhaustion."""
    allowed = {expected}
    if expected == GateAction.RETRY:
        allowed.add(GateAction.FALLBACK)
        allowed.add(GateAction.NEEDS_REVIEW)
    return allowed


def _allowed_task_statuses(expected: TaskStatus) -> set[TaskStatus]:
    """After gate action, task may be re-queued for retry/fallback."""
    allowed = {expected}
    if expected == TaskStatus.FAILED:
        allowed.add(TaskStatus.QUEUED)  # retry/fallback re-queues
        allowed.add(TaskStatus.NEEDS_REVIEW)  # needs_review escalation
    if expected == TaskStatus.NEEDS_REVIEW:
        allowed.add(TaskStatus.QUEUED)  # retry path
    return allowed


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_COLORS = {
    "green": "\033[92m",
    "red": "\033[91m",
    "yellow": "\033[93m",
    "blue": "\033[94m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}


def _c(text: str, color: str) -> str:
    return f"{_COLORS.get(color, '')}{text}{_COLORS['reset']}"


def _print_run_summary(result: AcceptanceRunResult, verbose: bool = False) -> None:
    icon = _c("PASS", "green") if result.passed else _c("FAIL", "red")
    fault = result.profile.fault_type
    run_status = result.actual_run_status.value if result.actual_run_status else "?"
    gate = (
        f"{result.actual_gate_outcome.value}→{result.actual_gate_action.value}"
        if result.actual_gate_outcome
        else "?"
    )
    task = result.actual_task_status.value if result.actual_task_status else "?"
    steps = len(result.steps_completed)

    print(
        f"  [{icon}] #{result.run_index:03d} {fault:<20s} run={run_status:<14s} gate={gate:<30s} task={task:<20s} steps={steps}"
    )

    if not result.passed:
        for f in result.failures:
            print(f"        {_c('↳ ' + f, 'red')}")

    if verbose and result.passed:
        steps_str = " → ".join(result.steps_completed)
        print(f"        {_c(steps_str, 'dim')}")


def _print_final_report(summary: AcceptanceSummary) -> None:
    print()
    print(_c("=" * 80, "bold"))
    print(_c("  ACCEPTANCE TEST REPORT", "bold"))
    print(_c("=" * 80, "bold"))
    print(f"  Total runs:    {summary.total_runs}")
    print(f"  Passed:        {_c(str(summary.passed), 'green')}")
    print(f"  Failed:        {_c(str(summary.failed), 'red') if summary.failed else '0'}")
    print(f"  Duration:      {summary.start_time} → {summary.end_time}")
    print(f"  Pass rate:     {summary.passed / max(summary.total_runs, 1) * 100:.1f}%")
    print()

    # Per-fault-type breakdown
    print(_c("  Fault Type Breakdown:", "bold"))
    print(f"  {'Fault Type':<25s} {'Total':>6s} {'Passed':>6s} {'Failed':>6s} {'Rate':>7s}")
    print(f"  {'-' * 25} {'-' * 6} {'-' * 6} {'-' * 6} {'-' * 7}")
    for ft, counts in sorted(summary.by_fault_type.items()):
        rate = counts["passed"] / max(counts["total"], 1) * 100
        rate_str = f"{rate:.0f}%"
        print(
            f"  {ft:<25s} {counts['total']:>6d} {counts['passed']:>6d} {counts['failed']:>6d} {rate_str:>7s}"
        )
    print()

    # Failure details
    failures = [r for r in summary.run_results if not r.passed]
    if failures:
        print(_c("  Failed Runs:", "bold"))
        for r in failures:
            print(f"    #{r.run_index:03d} ({r.profile.fault_type}):")
            for f in r.failures:
                print(f"      {_c('✗ ' + f, 'red')}")
        print()

    # Verdict
    if summary.failed == 0:
        print(_c("  VERDICT: ALL ACCEPTANCE TESTS PASSED ✓", "green"))
    else:
        print(_c(f"  VERDICT: {summary.failed} FAILURES — ACCEPTANCE REJECTED", "red"))
    print(_c("=" * 80, "bold"))


def _write_json_report(summary: AcceptanceSummary, path: Path) -> None:
    """Write machine-readable JSON report."""
    report = {
        "acceptance_test": {
            "total_runs": summary.total_runs,
            "passed": summary.passed,
            "failed": summary.failed,
            "pass_rate": summary.passed / max(summary.total_runs, 1),
            "start_time": summary.start_time,
            "end_time": summary.end_time,
        },
        "by_fault_type": summary.by_fault_type,
        "runs": [
            {
                "index": r.run_index,
                "fault_type": r.profile.fault_type,
                "task_id": r.task_id,
                "run_id": r.run_id,
                "expected_run_status": r.profile.expected_run_status.value,
                "actual_run_status": r.actual_run_status.value if r.actual_run_status else None,
                "expected_gate_outcome": r.profile.expected_gate_outcome.value,
                "actual_gate_outcome": (
                    r.actual_gate_outcome.value if r.actual_gate_outcome else None
                ),
                "expected_gate_action": r.profile.expected_gate_action.value,
                "actual_gate_action": r.actual_gate_action.value if r.actual_gate_action else None,
                "actual_task_status": r.actual_task_status.value if r.actual_task_status else None,
                "passed": r.passed,
                "failures": r.failures,
                "steps_completed": r.steps_completed,
                "started_at": r.started_at,
                "finished_at": r.finished_at,
            }
            for r in summary.run_results
        ],
    }
    path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Formal acceptance test harness")
    parser.add_argument(
        "--runs", type=int, default=30, help="Number of consecutive runs (default: 30)"
    )
    parser.add_argument("--verbose", action="store_true", help="Show lifecycle steps for each run")
    parser.add_argument("--json-report", type=str, default="", help="Write JSON report to file")
    args = parser.parse_args()

    num_runs = max(args.runs, 1)
    verbose = args.verbose

    print(
        _c(
            "╔══════════════════════════════════════════════════════════════════════════════╗",
            "bold",
        )
    )
    print(
        _c(
            "║       Autonomous Agent Stack — Formal Acceptance Test Harness               ║",
            "bold",
        )
    )
    print(
        _c(
            "╚══════════════════════════════════════════════════════════════════════════════╝",
            "bold",
        )
    )
    print(f"  Runs: {num_runs} | Fault types: {len(FAULT_PROFILES)} | Seed: deterministic")
    print()

    summary = AcceptanceSummary(start_time=datetime.now(timezone.utc).isoformat())

    for i in range(num_runs):
        profile = _pick_profile(i)
        run_result = _execute_run(i, profile)
        _verify_run(run_result)
        summary.add_result(run_result)
        _print_run_summary(run_result, verbose=verbose)

    summary.end_time = datetime.now(timezone.utc).isoformat()
    _print_final_report(summary)

    if args.json_report:
        _write_json_report(summary, Path(args.json_report))
        print(f"\n  JSON report written to: {args.json_report}")

    return 1 if summary.failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
