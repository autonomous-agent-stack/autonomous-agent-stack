"""Tests for the unified task gate contract."""

from __future__ import annotations

import pytest

from autoresearch.shared.task_gate_contract import (
    GateAction,
    GateCheck,
    GateOutcome,
    GateVerdict,
    default_action_for_outcome,
    make_gate_verdict,
)

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestGateOutcome:
    def test_all_outcomes_present(self):
        assert GateOutcome.SUCCESS
        assert GateOutcome.OVERREACH
        assert GateOutcome.TIMEOUT
        assert GateOutcome.MISSING_ARTIFACTS
        assert GateOutcome.NEEDS_HUMAN_CONFIRM


class TestGateAction:
    def test_all_actions_present(self):
        assert GateAction.ACCEPT
        assert GateAction.RETRY
        assert GateAction.FALLBACK
        assert GateAction.NEEDS_REVIEW
        assert GateAction.REJECT


# ---------------------------------------------------------------------------
# Default mapping
# ---------------------------------------------------------------------------


class TestDefaultMapping:
    @pytest.mark.parametrize(
        "outcome, expected",
        [
            (GateOutcome.SUCCESS, GateAction.ACCEPT),
            (GateOutcome.OVERREACH, GateAction.REJECT),
            (GateOutcome.TIMEOUT, GateAction.RETRY),
            (GateOutcome.MISSING_ARTIFACTS, GateAction.RETRY),
            (GateOutcome.NEEDS_HUMAN_CONFIRM, GateAction.NEEDS_REVIEW),
        ],
    )
    def test_default_action(self, outcome, expected):
        assert default_action_for_outcome(outcome) == expected


# ---------------------------------------------------------------------------
# GateCheck
# ---------------------------------------------------------------------------


class TestGateCheck:
    def test_passed_check(self):
        c = GateCheck(check_id="test_output", passed=True, detail="output found")
        assert c.passed
        assert c.severity == "info"

    def test_failed_check(self):
        c = GateCheck(
            check_id="no_changes", passed=False, detail="empty patch", severity="critical"
        )
        assert not c.passed
        assert c.severity == "critical"

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            GateCheck(check_id="x", passed=True, unknown="y")


# ---------------------------------------------------------------------------
# GateVerdict
# ---------------------------------------------------------------------------


class TestGateVerdict:
    def test_success_verdict(self):
        v = GateVerdict(outcome=GateOutcome.SUCCESS, action=GateAction.ACCEPT)
        assert v.can_retry is True
        assert v.all_checks_passed is True

    def test_verdict_with_checks(self):
        v = GateVerdict(
            outcome=GateOutcome.SUCCESS,
            action=GateAction.ACCEPT,
            checks=[
                GateCheck(check_id="c1", passed=True),
                GateCheck(check_id="c2", passed=False, detail="missing"),
            ],
        )
        assert not v.all_checks_passed

    def test_verdict_with_all_passed_checks(self):
        v = GateVerdict(
            outcome=GateOutcome.SUCCESS,
            action=GateAction.ACCEPT,
            checks=[
                GateCheck(check_id="c1", passed=True),
                GateCheck(check_id="c2", passed=True),
            ],
        )
        assert v.all_checks_passed


# ---------------------------------------------------------------------------
# make_gate_verdict factory
# ---------------------------------------------------------------------------


class TestMakeGateVerdict:
    def test_success(self):
        v = make_gate_verdict(GateOutcome.SUCCESS, reason="all good")
        assert v.action == GateAction.ACCEPT
        assert v.reason == "all good"

    def test_timeout_first_retry(self):
        v = make_gate_verdict(GateOutcome.TIMEOUT, retry_attempt=0, max_retries=3)
        assert v.action == GateAction.RETRY
        assert v.can_retry is True

    def test_timeout_exhausted_with_fallback(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="mock",
        )
        assert v.action == GateAction.FALLBACK
        assert v.fallback_agent_id == "mock"

    def test_timeout_exhausted_no_fallback(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            retry_attempt=3,
            max_retries=3,
        )
        assert v.action == GateAction.NEEDS_REVIEW

    def test_overreach(self):
        v = make_gate_verdict(GateOutcome.OVERREACH, reason="wrote to forbidden path")
        assert v.action == GateAction.REJECT

    def test_needs_human_confirm(self):
        v = make_gate_verdict(GateOutcome.NEEDS_HUMAN_CONFIRM)
        assert v.action == GateAction.NEEDS_REVIEW

    def test_with_checks(self):
        checks = [
            GateCheck(check_id="output_exists", passed=True),
            GateCheck(check_id="tests_pass", passed=False, severity="critical"),
        ]
        v = make_gate_verdict(GateOutcome.MISSING_ARTIFACTS, checks=checks)
        assert len(v.checks) == 2
        assert not v.all_checks_passed

    def test_missing_artifacts_first_retry(self):
        v = make_gate_verdict(GateOutcome.MISSING_ARTIFACTS, retry_attempt=1)
        assert v.action == GateAction.RETRY

    def test_factory_preserves_metadata(self):
        v = make_gate_verdict(GateOutcome.SUCCESS, metadata={"source": "test"})
        assert v.metadata["source"] == "test"
