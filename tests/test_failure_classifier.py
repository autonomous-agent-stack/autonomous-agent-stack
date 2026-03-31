from __future__ import annotations

from autoresearch.agent_protocol.models import DriverResult, RunSummary, ValidationCheck, ValidationReport
from autoresearch.core.dispatch.failure_classifier import classify_remote_status, classify_run_summary
from autoresearch.shared.remote_run_contract import FailureClass, RecoveryAction, RemoteRunStatus


def _summary(
    *,
    driver_status: str,
    final_status: str,
    agent_id: str = "openhands",
    validation_passed: bool = True,
    error: str | None = None,
) -> RunSummary:
    checks = []
    if not validation_passed:
        checks.append(ValidationCheck(id="worker.test_command", passed=False, detail="assertion failed"))
    return RunSummary(
        run_id="run-classifier",
        final_status=final_status,
        driver_result=DriverResult(
            run_id="run-classifier",
            agent_id=agent_id,
            status=driver_status,
            summary="classifier probe",
            changed_paths=["src/demo.py"],
            recommended_action="fallback" if agent_id == "mock" else "human_review",
            error=error,
        ),
        validation=ValidationReport(
            run_id="run-classifier",
            passed=validation_passed,
            checks=checks,
        ),
    )


def test_classifier_maps_stalled_executor_to_retry() -> None:
    disposition = classify_run_summary(
        _summary(driver_status="stalled_no_progress", final_status="failed", error="no workspace progress")
    )
    assert disposition.failure_class is FailureClass.EXECUTOR_STALLED
    assert disposition.recovery_action is RecoveryAction.RETRY


def test_classifier_maps_timeout_to_retry() -> None:
    disposition = classify_run_summary(_summary(driver_status="timed_out", final_status="failed"))
    assert disposition.failure_class is FailureClass.TOOL_TIMEOUT
    assert disposition.recovery_action is RecoveryAction.RETRY


def test_classifier_maps_env_missing_to_abort() -> None:
    disposition = classify_run_summary(
        _summary(
            driver_status="contract_error",
            final_status="failed",
            error="EnvironmentCheckFailed: launch_ai_lab.sh not found at scripts/launch_ai_lab.sh",
        )
    )
    assert disposition.failure_class is FailureClass.ENV_MISSING
    assert disposition.recovery_action is RecoveryAction.ABORT


def test_classifier_maps_workspace_dirty_to_abort() -> None:
    disposition = classify_run_summary(
        _summary(
            driver_status="contract_error",
            final_status="failed",
            error="repository worktree is not clean; promotion requires a clean base",
        )
    )
    assert disposition.failure_class is FailureClass.WORKSPACE_DIRTY
    assert disposition.recovery_action is RecoveryAction.ABORT


def test_classifier_maps_mock_success_to_downgrade() -> None:
    disposition = classify_run_summary(
        _summary(
            driver_status="succeeded",
            final_status="ready_for_promotion",
            agent_id="mock",
        )
    )
    assert disposition.failure_class is FailureClass.MODEL_FALLBACK
    assert disposition.recovery_action is RecoveryAction.DOWNGRADE_TO_DRAFT


def test_classifier_maps_mock_validation_failure_to_human_review() -> None:
    disposition = classify_run_summary(
        _summary(
            driver_status="failed",
            final_status="human_review",
            agent_id="mock",
            validation_passed=False,
        )
    )
    assert disposition.failure_class is FailureClass.ASSERTION_FAILED_AFTER_FALLBACK
    assert disposition.recovery_action is RecoveryAction.REQUIRE_HUMAN_REVIEW


def test_classifier_maps_planner_stall_to_human_review() -> None:
    disposition = classify_remote_status(RemoteRunStatus.STALLED, stage="planner")
    assert disposition.failure_class is FailureClass.PLANNER_STALLED
    assert disposition.recovery_action is RecoveryAction.REQUIRE_HUMAN_REVIEW


def test_classifier_maps_transient_network_to_retry() -> None:
    disposition = classify_remote_status(
        RemoteRunStatus.FAILED,
        error_text="ssh: connection reset by peer",
    )
    assert disposition.failure_class is FailureClass.TRANSIENT_NETWORK
    assert disposition.recovery_action is RecoveryAction.RETRY
