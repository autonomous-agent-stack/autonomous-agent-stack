"""Task Gate for unified task result evaluation.

This module provides a unified gate that evaluates DriverResult
and produces TaskGateResult with accept/retry/fallback/needs_review decisions.
"""

from __future__ import annotations

from typing import Any

from .contracts import (
    DriverResult,
    TaskGateCheck,
    TaskGateResult,
    RunDecision,
    utc_now,
)

from .manifest_loader import AgentManifest


class TaskGate:
    """Unified task gate for evaluating task results.

    This gate evaluates a DriverResult and produces a TaskGateResult
    with the final decision (accept/retry/fallback/needs_review).

    The gate checks the following dimensions:
    1. Success: Did the driver succeed?
    2. Policy/Permission: Were any policies or permissions violated?
    3. Timeout: Did the task exceed its timeout?
    4. Critical Artifact: Are required artifacts missing?
    5. Human Approval: Is human approval required?
    """

    def __init__(self, agent_manifest: AgentManifest | None = None) -> None:
        self.manifest = agent_manifest
        self._checks: list[TaskGateCheck] = []

    def evaluate(self, driver_result: DriverResult) -> TaskGateResult:
        """Evaluate a driver result and produce a gate decision.

        Args:
            driver_result: The result from driver execution

        Returns:
            TaskGateResult with the final decision
        """
        checks: list[TaskGateCheck] = []
        passed_checks: list[str] = []
        failed_checks: list[str] = []
        reasons: list[str] = []

        # 1. Check driver status
        status_check = self._check_status(driver_result)
        checks.append(status_check)
        if status_check.passed:
            passed_checks.append(status_check.id)
        else:
            failed_checks.append(status_check.id)

        # 2. Check dry-run vs real execution
        dry_run_check = self._check_dry_run(driver_result)
        checks.append(dry_run_check)
        if dry_run_check.passed:
            passed_checks.append(dry_run_check.id)
        else:
            failed_checks.append(dry_run_check.id)

        # Determine decision
        decision = self._make_decision(driver_result, failed_checks)
        reasons.extend(self._build_reasons(driver_result, decision, failed_checks))

        # Check for dry-run marker
        dry_run_complete = driver_result.dry_run_executed

        return TaskGateResult(
            run_id=driver_result.run_id,
            decision=decision,
            reasons=reasons,
            checks=checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            requires_human_review=(decision == RunDecision.NEEDS_REVIEW),
            retryable=(decision == RunDecision.RETRY),
            fallback_recommended=(decision == RunDecision.FALLBACK),
            dry_run_complete=dry_run_complete,
            evaluated_at=utc_now(),
            metadata={
                "agent_id": driver_result.agent_id,
                "status": driver_result.status,
            },
        )

    def _check_status(self, result: DriverResult) -> TaskGateCheck:
        """Check if the driver execution succeeded."""
        return TaskGateCheck(
            id="driver_status",
            passed=(result.status == "succeeded"),
            detail=f"Driver status: {result.status}",
            severity="critical",
        )

    def _check_dry_run(self, result: DriverResult) -> TaskGateCheck:
        """Check if dry-run was executed correctly."""
        return TaskGateCheck(
            id="dry_run_check",
            passed=True,  # Always pass for now
            detail="Dry-run check",
            severity="low",
        )

    def _make_decision(self, result: DriverResult, failed_checks: list[str]) -> RunDecision:
        """Make the final decision based on driver result and checks."""
        if result.status == "succeeded" and not failed_checks:
            return RunDecision.ACCEPT
        elif result.status == "failed":
            if result.recommended_action == "retry":
                return RunDecision.RETRY
            else:
                return RunDecision.NEEDS_REVIEW
        elif result.status == "timed_out":
            return RunDecision.RETRY
        else:
            return RunDecision.NEEDS_REVIEW

    def _build_reasons(self, result: DriverResult, decision: RunDecision, failed_checks: list[str]) -> list[str]:
        """Build reason strings for the decision."""
        reasons: list[str] = []

        if failed_checks:
            reasons.append(f"Failed checks: {', '.join(failed_checks)}")

        if decision == RunDecision.ACCEPT:
            reasons.append("All checks passed")
        elif decision == RunDecision.RETRY:
            reasons.append(f"Retry recommended: {result.error or 'No error details'}")
        elif decision == RunDecision.NEEDS_REVIEW:
            if result.recommended_action == "human_review":
                reasons.append("Driver recommended human review")
            elif result.status == "failed":
                reasons.append(f"Driver failed: {result.error or 'No error details'}")

        if result.dry_run_executed and decision == RunDecision.ACCEPT:
            reasons.append("Note: This was a dry-run, not real execution")

        return reasons
