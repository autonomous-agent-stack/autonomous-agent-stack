from __future__ import annotations

from autoresearch.agent_protocol.models import DriverResult, ValidationReport


def attempt_succeeded(driver_result: DriverResult, validation: ValidationReport) -> bool:
    return driver_result.status in {"succeeded", "partial"} and validation.passed


def derive_terminal_status(driver_result: DriverResult, validation: ValidationReport) -> str:
    if driver_result.status in {"contract_error", "failed", "timed_out", "stalled_no_progress"}:
        return "failed"
    if driver_result.status == "policy_blocked":
        return "blocked"

    failed_ids = {check.id for check in validation.checks if not check.passed}
    if "builtin.nonempty_change_for_promote" in failed_ids:
        return "blocked"

    if driver_result.recommended_action == "human_review" or not validation.passed:
        return "human_review"
    return "blocked"
