"""Acceptance test harness — pytest wrapper.

Runs the same 30-run acceptance suite via pytest for CI integration.
"""

from __future__ import annotations

import pytest

from autoresearch.shared.run_contract import RunStatus
from autoresearch.shared.task_contract import TaskStatus
from autoresearch.shared.task_gate_contract import GateAction, GateOutcome

# Import the acceptance harness internals
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "acceptance_run",
    str(Path(__file__).resolve().parent.parent / "scripts" / "acceptance_run.py"),
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["acceptance_run"] = _mod
_spec.loader.exec_module(_mod)

_execute_run = _mod._execute_run
_verify_run = _mod._verify_run
_pick_profile = _mod._pick_profile
ACCEPTANCE_RUNS = 30


@pytest.fixture(scope="module")
def acceptance_results():
    results = []
    for i in range(ACCEPTANCE_RUNS):
        profile = _pick_profile(i)
        run_result = _execute_run(i, profile)
        _verify_run(run_result)
        results.append(run_result)
    return results


class TestAcceptanceSuite:
    """30-run acceptance suite — all must pass."""

    def test_all_runs_passed(self, acceptance_results):
        failures = [r for r in acceptance_results if not r.passed]
        assert len(failures) == 0, f"{len(failures)} runs failed:\n" + "\n".join(
            f"  #{r.run_index} ({r.profile.fault_type}): {r.failures}" for r in failures
        )

    def test_total_run_count(self, acceptance_results):
        assert len(acceptance_results) == ACCEPTANCE_RUNS

    def test_all_lifecycle_steps_complete(self, acceptance_results):
        required = [
            "task_created",
            "task_queued",
            "run_created",
            "run_leased",
            "run_running",
            "run_terminal",
            "gate_evaluated",
            "action_applied",
        ]
        for r in acceptance_results:
            missing = [s for s in required if s not in r.steps_completed]
            assert not missing, f"Run #{r.run_index} missing steps: {missing}"

    def test_all_fault_types_covered(self, acceptance_results):
        fault_types = {r.profile.fault_type for r in acceptance_results}
        expected = {
            "timeout",
            "crash",
            "overreach",
            "missing_artifacts",
            "permission_denied",
            "success",
        }
        assert expected.issubset(fault_types), f"Missing fault types: {expected - fault_types}"


class TestAcceptancePerFaultType:
    """Verify each fault type produces correct outcomes."""

    def test_timeout_produces_failed_run(self, acceptance_results):
        timeouts = [r for r in acceptance_results if r.profile.fault_type == "timeout"]
        assert len(timeouts) > 0
        for r in timeouts:
            assert r.actual_run_status == RunStatus.FAILED

    def test_crash_produces_failed_run(self, acceptance_results):
        crashes = [r for r in acceptance_results if r.profile.fault_type == "crash"]
        assert len(crashes) > 0
        for r in crashes:
            assert r.actual_run_status == RunStatus.FAILED

    def test_overreach_produces_rejected_task(self, acceptance_results):
        overreaches = [r for r in acceptance_results if r.profile.fault_type == "overreach"]
        assert len(overreaches) > 0
        for r in overreaches:
            assert r.actual_gate_outcome == GateOutcome.OVERREACH
            assert r.actual_gate_action == GateAction.REJECT

    def test_missing_artifacts_triggers_gate(self, acceptance_results):
        missing = [r for r in acceptance_results if r.profile.fault_type == "missing_artifacts"]
        assert len(missing) > 0
        for r in missing:
            assert r.actual_gate_outcome == GateOutcome.MISSING_ARTIFACTS

    def test_permission_denied_needs_review(self, acceptance_results):
        perms = [r for r in acceptance_results if r.profile.fault_type == "permission_denied"]
        assert len(perms) > 0
        for r in perms:
            assert r.actual_gate_outcome == GateOutcome.NEEDS_HUMAN_CONFIRM
            assert r.actual_gate_action == GateAction.NEEDS_REVIEW

    def test_success_produces_succeeded_task(self, acceptance_results):
        successes = [r for r in acceptance_results if r.profile.fault_type == "success"]
        assert len(successes) > 0
        for r in successes:
            assert r.actual_run_status == RunStatus.SUCCEEDED
            assert r.actual_task_status == TaskStatus.SUCCEEDED
            assert r.actual_gate_action == GateAction.ACCEPT
