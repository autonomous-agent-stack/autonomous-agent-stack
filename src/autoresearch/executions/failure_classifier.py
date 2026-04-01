from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from autoresearch.agent_protocol.models import DriverResult, ValidationReport

FailureStatus = Literal[
    "timed_out",
    "stalled_no_progress",
    "mock_fallback",
    "assertion_failed",
    "infra_error",
    "unknown",
]

FailureLayer = Literal["infra", "orchestration", "model", "business_validation"]


@dataclass(frozen=True)
class FailureClassification:
    failure_status: FailureStatus
    failure_layer: FailureLayer | None


def classify_failure(
    *,
    driver_result: DriverResult,
    validation: ValidationReport,
    metadata: dict[str, Any] | None = None,
) -> FailureClassification:
    metadata = metadata or {}
    if driver_result.status == "timed_out":
        return FailureClassification("timed_out", "infra")
    if driver_result.status == "stalled_no_progress":
        return FailureClassification("stalled_no_progress", "infra")
    if _is_mock_fallback(driver_result, metadata):
        return FailureClassification("mock_fallback", "orchestration")
    if not validation.passed:
        return FailureClassification("assertion_failed", "business_validation")
    if driver_result.status in {"contract_error", "failed", "policy_blocked"}:
        return FailureClassification("infra_error", "infra")
    return FailureClassification("unknown", None)


def _is_mock_fallback(driver_result: DriverResult, metadata: dict[str, Any]) -> bool:
    if bool(metadata.get("mock_fallback_enabled")) and driver_result.status in {"succeeded", "partial"}:
        return True
    return False
