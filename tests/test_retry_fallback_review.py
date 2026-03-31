"""B6: Retry / fallback / needs_review rule tests.

Tests for:
- Retry exhaustion auto-upgrade to fallback
- Fallback agent delegation
- Needs_review resolution paths
- Max retries boundary conditions
"""

from __future__ import annotations

import pytest

from autoresearch.shared.run_contract import RunRecord, RunStatus
from autoresearch.shared.task_contract import TaskStatus, is_valid_transition
from autoresearch.shared.task_gate_contract import (
    GateAction,
    GateOutcome,
    make_gate_verdict,
)


class TestRetryRules:
    """Retry mechanics: when to retry vs upgrade to fallback."""

    def test_first_attempt_is_retryable(self):
        v = make_gate_verdict(GateOutcome.TIMEOUT, retry_attempt=0, max_retries=3)
        assert v.action == GateAction.RETRY
        assert v.can_retry is True

    def test_second_attempt_is_retryable(self):
        v = make_gate_verdict(GateOutcome.TIMEOUT, retry_attempt=1, max_retries=3)
        assert v.action == GateAction.RETRY
        assert v.can_retry is True

    def test_last_retry_before_exhaustion(self):
        v = make_gate_verdict(GateOutcome.TIMEOUT, retry_attempt=2, max_retries=3)
        assert v.action == GateAction.RETRY
        assert v.can_retry is True

    def test_exhausted_retries_with_fallback(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="fallback-hk",
        )
        assert v.action == GateAction.FALLBACK
        assert v.can_retry is False

    def test_exhausted_retries_without_fallback(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id=None,
        )
        assert v.action == GateAction.NEEDS_REVIEW

    def test_exhausted_retries_max_1(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            retry_attempt=1,
            max_retries=1,
            fallback_agent_id="fb",
        )
        assert v.action == GateAction.FALLBACK
        assert v.can_retry is False

    def test_zero_max_retries_goes_straight_to_fallback(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            retry_attempt=0,
            max_retries=0,
            fallback_agent_id="fb",
        )
        assert v.action == GateAction.FALLBACK

    def test_zero_max_retries_no_fallback(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            retry_attempt=0,
            max_retries=0,
        )
        assert v.action == GateAction.NEEDS_REVIEW

    def test_missing_artifacts_also_upgrades_on_exhaustion(self):
        v = make_gate_verdict(
            GateOutcome.MISSING_ARTIFACTS,
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="collector",
        )
        assert v.action == GateAction.FALLBACK

    def test_success_never_retries(self):
        v = make_gate_verdict(GateOutcome.SUCCESS)
        assert v.action == GateAction.ACCEPT
        assert v.outcome != GateOutcome.TIMEOUT

    def test_overreach_never_retries(self):
        v = make_gate_verdict(GateOutcome.OVERREACH)
        assert v.action == GateAction.REJECT


class TestFallbackRules:
    """Fallback agent delegation after retry exhaustion."""

    def test_fallback_agent_id_preserved(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="fallback-hk",
        )
        assert v.fallback_agent_id == "fallback-hk"

    def test_fallback_agent_none_when_not_exhausted(self):
        v = make_gate_verdict(GateOutcome.TIMEOUT, retry_attempt=0, max_retries=3)
        assert v.fallback_agent_id is None

    def test_different_fallback_agents_per_scenario(self):
        v1 = make_gate_verdict(
            GateOutcome.TIMEOUT, retry_attempt=3, max_retries=3, fallback_agent_id="timeout-handler"
        )
        v2 = make_gate_verdict(
            GateOutcome.MISSING_ARTIFACTS,
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="artifact-collector",
        )
        assert v1.fallback_agent_id == "timeout-handler"
        assert v2.fallback_agent_id == "artifact-collector"


class TestNeedsReviewRules:
    """Needs_review resolution: succeeded / failed paths."""

    def test_needs_review_to_succeeded_valid(self):
        assert is_valid_transition(TaskStatus.NEEDS_REVIEW, TaskStatus.SUCCEEDED)

    def test_needs_review_to_failed_valid(self):
        assert is_valid_transition(TaskStatus.NEEDS_REVIEW, TaskStatus.FAILED)

    def test_needs_review_to_rejected_valid(self):
        assert is_valid_transition(TaskStatus.NEEDS_REVIEW, TaskStatus.REJECTED)

    def test_needs_review_to_queued_valid(self):
        assert is_valid_transition(TaskStatus.NEEDS_REVIEW, TaskStatus.QUEUED)

    def test_needs_review_to_running_invalid(self):
        assert not is_valid_transition(TaskStatus.NEEDS_REVIEW, TaskStatus.RUNNING)

    def test_needs_review_to_pending_invalid(self):
        assert not is_valid_transition(TaskStatus.NEEDS_REVIEW, TaskStatus.PENDING)

    def test_run_needs_review_to_succeeded(self):
        run = RunRecord(run_id="r1", task_id="t1")
        run.transition_to(RunStatus.LEASED)
        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.NEEDS_REVIEW)
        run.transition_to(RunStatus.SUCCEEDED)
        assert run.status == RunStatus.SUCCEEDED

    def test_run_needs_review_to_failed(self):
        run = RunRecord(run_id="r1", task_id="t1")
        run.transition_to(RunStatus.LEASED)
        run.transition_to(RunStatus.RUNNING)
        run.transition_to(RunStatus.NEEDS_REVIEW)
        run.transition_to(RunStatus.FAILED)
        assert run.status == RunStatus.FAILED

    def test_run_needs_review_cannot_go_to_running(self):
        run = RunRecord(run_id="r1", task_id="t1", status=RunStatus.NEEDS_REVIEW)
        with pytest.raises(ValueError):
            run.transition_to(RunStatus.RUNNING)

    def test_run_needs_review_cannot_go_to_queued(self):
        run = RunRecord(run_id="r1", task_id="t1", status=RunStatus.NEEDS_REVIEW)
        with pytest.raises(ValueError):
            run.transition_to(RunStatus.QUEUED)

    def test_run_needs_review_cannot_go_to_leased(self):
        run = RunRecord(run_id="r1", task_id="t1", status=RunStatus.NEEDS_REVIEW)
        with pytest.raises(ValueError):
            run.transition_to(RunStatus.LEASED)


class TestRetryBoundaryConditions:
    """Edge cases around retry counts and max_retries."""

    def test_negative_retry_attempt_treated_as_retryable(self):
        v = make_gate_verdict(GateOutcome.TIMEOUT, retry_attempt=-1, max_retries=3)
        assert v.action == GateAction.RETRY
        assert v.can_retry is True

    def test_very_large_max_retries(self):
        v = make_gate_verdict(GateOutcome.TIMEOUT, retry_attempt=100, max_retries=1000)
        assert v.action == GateAction.RETRY
        assert v.can_retry is True

    def test_retry_attempt_exactly_at_max(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            retry_attempt=5,
            max_retries=5,
            fallback_agent_id="fb",
        )
        assert v.action == GateAction.FALLBACK

    def test_retry_attempt_just_below_max(self):
        v = make_gate_verdict(GateOutcome.TIMEOUT, retry_attempt=4, max_retries=5)
        assert v.action == GateAction.RETRY
        assert v.can_retry is True

    def test_task_failed_can_retry_to_queued(self):
        assert is_valid_transition(TaskStatus.FAILED, TaskStatus.QUEUED)

    def test_task_failed_cannot_retry_to_running(self):
        assert not is_valid_transition(TaskStatus.FAILED, TaskStatus.RUNNING)
