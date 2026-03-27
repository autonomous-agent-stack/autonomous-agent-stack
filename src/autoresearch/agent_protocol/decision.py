from __future__ import annotations

from autoresearch.agent_protocol.models import DriverResult, ValidationReport


def attempt_succeeded(driver_result: DriverResult, validation: ValidationReport) -> bool:
    return driver_result.status in {"succeeded", "partial"} and validation.passed


def derive_terminal_status(driver_result: DriverResult, validation: ValidationReport) -> str:
    if driver_result.status == "contract_error":
        return "failed"
    if driver_result.recommended_action == "human_review" or not validation.passed:
        return "human_review"
    return "blocked"
