from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from autoresearch.agent_protocol.models import RunSummary
from autoresearch.shared.remote_run_contract import FailureClass, RecoveryAction, RemoteRunStatus


_FAILURE_ACTIONS: dict[FailureClass, RecoveryAction] = {
    FailureClass.PLANNER_STALLED: RecoveryAction.REQUIRE_HUMAN_REVIEW,
    FailureClass.EXECUTOR_STALLED: RecoveryAction.RETRY,
    FailureClass.TOOL_TIMEOUT: RecoveryAction.RETRY,
    FailureClass.MODEL_FALLBACK: RecoveryAction.DOWNGRADE_TO_DRAFT,
    FailureClass.ASSERTION_FAILED_AFTER_FALLBACK: RecoveryAction.REQUIRE_HUMAN_REVIEW,
    FailureClass.ENV_MISSING: RecoveryAction.ABORT,
    FailureClass.WORKSPACE_DIRTY: RecoveryAction.ABORT,
    FailureClass.TRANSIENT_NETWORK: RecoveryAction.RETRY,
    FailureClass.UNKNOWN: RecoveryAction.QUARANTINE,
}

_ENV_MISSING_MARKERS = (
    "environmentcheckfailed:",
    "launch_ai_lab.sh not found",
    "no such file or directory",
    "command not found",
    "docker socket is stale",
)
_WORKSPACE_DIRTY_MARKERS = (
    "repository worktree is not clean",
    "repo root has uncommitted changes",
    "clean git checkout",
    "clean base repository",
)
_TRANSIENT_NETWORK_MARKERS = (
    "connection reset",
    "connection refused",
    "temporary failure",
    "network is unreachable",
    "timed out while connecting",
    "ssh:",
)


@dataclass(frozen=True, slots=True)
class FailureDisposition:
    failure_class: FailureClass | None
    recovery_action: RecoveryAction | None


def recovery_action_for_failure_class(failure_class: FailureClass | None) -> RecoveryAction | None:
    if failure_class is None:
        return None
    return _FAILURE_ACTIONS[failure_class]


def classify_failure_class(failure_class: FailureClass | None) -> FailureDisposition:
    return FailureDisposition(
        failure_class=failure_class,
        recovery_action=recovery_action_for_failure_class(failure_class),
    )


def infer_failure_class_from_error(error_text: str | None) -> FailureClass | None:
    normalized = (error_text or "").strip().lower()
    if not normalized:
        return None
    if any(marker in normalized for marker in _WORKSPACE_DIRTY_MARKERS):
        return FailureClass.WORKSPACE_DIRTY
    if any(marker in normalized for marker in _ENV_MISSING_MARKERS):
        return FailureClass.ENV_MISSING
    if any(marker in normalized for marker in _TRANSIENT_NETWORK_MARKERS):
        return FailureClass.TRANSIENT_NETWORK
    return None


def classify_remote_status(
    status: RemoteRunStatus,
    *,
    stage: Literal["planner", "executor"] = "executor",
    error_text: str | None = None,
) -> FailureDisposition:
    if status is RemoteRunStatus.STALLED:
        if stage == "planner":
            return classify_failure_class(FailureClass.PLANNER_STALLED)
        return classify_failure_class(FailureClass.EXECUTOR_STALLED)
    if status is RemoteRunStatus.TIMED_OUT:
        return classify_failure_class(FailureClass.TOOL_TIMEOUT)
    if status is RemoteRunStatus.FAILED:
        inferred = infer_failure_class_from_error(error_text)
        return classify_failure_class(inferred or FailureClass.UNKNOWN)
    return classify_failure_class(None)


def classify_run_summary(summary: RunSummary) -> FailureDisposition:
    driver_result = summary.driver_result
    error_text = str(driver_result.error or "").strip()

    if driver_result.status == "stalled_no_progress":
        return classify_failure_class(FailureClass.EXECUTOR_STALLED)
    if driver_result.status == "timed_out":
        return classify_failure_class(FailureClass.TOOL_TIMEOUT)

    inferred = infer_failure_class_from_error(error_text)
    if inferred is not None:
        return classify_failure_class(inferred)

    if driver_result.agent_id == "mock" and summary.validation.passed:
        return classify_failure_class(FailureClass.MODEL_FALLBACK)
    if driver_result.agent_id == "mock" and not summary.validation.passed:
        return classify_failure_class(FailureClass.ASSERTION_FAILED_AFTER_FALLBACK)
    if driver_result.recommended_action == "fallback" and not summary.validation.passed:
        return classify_failure_class(FailureClass.ASSERTION_FAILED_AFTER_FALLBACK)

    if summary.final_status == "failed":
        return classify_failure_class(FailureClass.UNKNOWN)
    return classify_failure_class(None)


def classify_remote_terminal(
    *,
    status: RemoteRunStatus,
    stage: Literal["planner", "executor"] = "executor",
    error_text: str | None = None,
    run_summary: RunSummary | None = None,
) -> FailureDisposition:
    if run_summary is not None:
        disposition = classify_run_summary(run_summary)
        if disposition.failure_class is not None or status is not RemoteRunStatus.SUCCEEDED:
            return disposition
        return disposition
    return classify_remote_status(status, stage=stage, error_text=error_text)
