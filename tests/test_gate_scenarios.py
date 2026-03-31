"""B5: Five gate scenario tests — success, timeout, overreach, missing artifacts, human confirm.

Each scenario exercises the full gate evaluation pipeline:
GateOutcome → GateAction → GateVerdict with checks.
"""

from __future__ import annotations

from autoresearch.shared.task_gate_contract import (
    GateAction,
    GateCheck,
    GateOutcome,
    GateVerdict,
    default_action_for_outcome,
    make_gate_verdict,
)


class TestGateSuccessScenario:
    """Scenario: run completes normally, all checks pass, gate accepts."""

    def test_success_outcome_maps_to_accept(self):
        assert default_action_for_outcome(GateOutcome.SUCCESS) == GateAction.ACCEPT

    def test_make_verdict_auto_accepts(self):
        v = make_gate_verdict(GateOutcome.SUCCESS, reason="All good")
        assert v.action == GateAction.ACCEPT
        assert v.outcome == GateOutcome.SUCCESS

    def test_all_checks_passed_property(self):
        v = make_gate_verdict(
            GateOutcome.SUCCESS,
            checks=[
                GateCheck(check_id="output_exists", passed=True),
                GateCheck(check_id="tests_pass", passed=True),
                GateCheck(check_id="no_overreach", passed=True),
            ],
        )
        assert v.all_checks_passed is True

    def test_verdict_with_multiple_checks(self):
        v = make_gate_verdict(
            GateOutcome.SUCCESS,
            checks=[
                GateCheck(check_id="output_exists", passed=True, detail="3 files changed"),
                GateCheck(check_id="tests_pass", passed=True, detail="12/12 passed"),
            ],
            reason="All checks passed",
        )
        assert len(v.checks) == 2
        assert v.all_checks_passed is True
        assert v.reason == "All checks passed"


class TestGateTimeoutScenario:
    """Scenario: run exceeds timeout, gate recommends retry."""

    def test_timeout_outcome_maps_to_retry(self):
        assert default_action_for_outcome(GateOutcome.TIMEOUT) == GateAction.RETRY

    def test_timeout_verdict_with_check(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Worker exceeded 900s timeout",
            checks=[
                GateCheck(
                    check_id="timeout", passed=False, detail="900s exceeded", severity="critical"
                ),
            ],
            retry_attempt=0,
            max_retries=3,
        )
        assert v.action == GateAction.RETRY
        assert v.can_retry is True
        assert v.retry_attempt == 0

    def test_timeout_retry_count_tracking(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Timeout on retry",
            retry_attempt=2,
            max_retries=3,
        )
        assert v.can_retry is True
        assert v.retry_attempt == 2

    def test_timeout_exhausted_upgrades_to_fallback(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Final timeout",
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="fallback-agent",
        )
        assert v.action == GateAction.FALLBACK
        assert v.can_retry is False

    def test_timeout_exhausted_no_fallback_needs_review(self):
        v = make_gate_verdict(
            GateOutcome.TIMEOUT,
            reason="Final timeout, no fallback",
            retry_attempt=3,
            max_retries=3,
        )
        assert v.action == GateAction.NEEDS_REVIEW


class TestGateOverreachScenario:
    """Scenario: agent modifies files outside allowed scope, gate rejects."""

    def test_overreach_outcome_maps_to_reject(self):
        assert default_action_for_outcome(GateOutcome.OVERREACH) == GateAction.REJECT

    def test_overreach_verdict(self):
        v = make_gate_verdict(
            GateOutcome.OVERREACH,
            reason="Agent modified /etc/passwd outside allowed scope",
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
        assert v.action == GateAction.REJECT
        assert v.all_checks_passed is False
        assert any(not c.passed for c in v.checks)

    def test_overreach_critical_severity(self):
        v = make_gate_verdict(
            GateOutcome.OVERREACH,
            checks=[
                GateCheck(check_id="scope", passed=False, severity="critical"),
            ],
        )
        critical_checks = [c for c in v.checks if c.severity == "critical" and not c.passed]
        assert len(critical_checks) == 1


class TestGateMissingArtifactsScenario:
    """Scenario: expected artifacts are missing, gate recommends retry."""

    def test_missing_artifacts_maps_to_retry(self):
        assert default_action_for_outcome(GateOutcome.MISSING_ARTIFACTS) == GateAction.RETRY

    def test_missing_artifact_verdict(self):
        v = make_gate_verdict(
            GateOutcome.MISSING_ARTIFACTS,
            reason="Expected screenshot not found",
            checks=[
                GateCheck(
                    check_id="screenshot_exists", passed=False, detail="No screenshot.png found"
                ),
                GateCheck(check_id="log_exists", passed=True, detail="stdout.log present"),
            ],
            retry_attempt=0,
            max_retries=3,
        )
        assert v.action == GateAction.RETRY
        assert v.can_retry is True
        assert not v.all_checks_passed

    def test_missing_artifacts_exhausted(self):
        v = make_gate_verdict(
            GateOutcome.MISSING_ARTIFACTS,
            reason="Still missing artifacts",
            retry_attempt=3,
            max_retries=3,
            fallback_agent_id="collector",
        )
        assert v.action == GateAction.FALLBACK


class TestGateHumanConfirmScenario:
    """Scenario: run outcome requires human confirmation."""

    def test_needs_human_confirm_maps_to_needs_review(self):
        assert (
            default_action_for_outcome(GateOutcome.NEEDS_HUMAN_CONFIRM) == GateAction.NEEDS_REVIEW
        )

    def test_human_confirm_verdict(self):
        v = make_gate_verdict(
            GateOutcome.NEEDS_HUMAN_CONFIRM,
            reason="Agent requested manual verification of production config change",
            checks=[
                GateCheck(check_id="change_scope", passed=True),
                GateCheck(check_id="requires_approval", passed=True, detail="Production config"),
            ],
        )
        assert v.action == GateAction.NEEDS_REVIEW
        assert v.outcome == GateOutcome.NEEDS_HUMAN_CONFIRM

    def test_human_confirm_even_if_all_checks_pass(self):
        """Human confirm should still need review even when all checks pass."""
        v = make_gate_verdict(
            GateOutcome.NEEDS_HUMAN_CONFIRM,
            reason="Policy requires human sign-off",
            checks=[GateCheck(check_id="policy", passed=True)],
        )
        assert v.action == GateAction.NEEDS_REVIEW
        assert v.all_checks_passed is True


class TestGateVerdictProperties:
    """Cross-cutting GateVerdict property tests."""

    def test_can_retry_property(self):
        v = GateVerdict(
            outcome=GateOutcome.TIMEOUT,
            action=GateAction.RETRY,
            retry_attempt=2,
            max_retries=3,
        )
        assert v.can_retry is True

        v_exhausted = GateVerdict(
            outcome=GateOutcome.TIMEOUT,
            action=GateAction.RETRY,
            retry_attempt=3,
            max_retries=3,
        )
        assert v_exhausted.can_retry is False

    def test_all_checks_passed_with_empty_list(self):
        v = GateVerdict(
            outcome=GateOutcome.SUCCESS,
            action=GateAction.ACCEPT,
            checks=[],
        )
        assert v.all_checks_passed is True

    def test_verdict_metadata_roundtrip(self):
        v = make_gate_verdict(
            GateOutcome.SUCCESS,
            metadata={"custom_key": "custom_value", "run_duration_s": 120},
        )
        assert v.metadata["custom_key"] == "custom_value"
        assert v.metadata["run_duration_s"] == 120
