from __future__ import annotations

from autoresearch.agent_protocol.models import DriverResult, ValidationCheck, ValidationReport
from autoresearch.executions.runner import AgentExecutionRunner


def _driver(status: str) -> DriverResult:
    return DriverResult(
        run_id="run-1",
        agent_id="agent",
        status=status,  # type: ignore[arg-type]
        summary=f"driver {status}",
        recommended_action="fallback",
    )


def _failed_validation() -> ValidationReport:
    return ValidationReport(
        run_id="run-1",
        passed=False,
        checks=[
            ValidationCheck(
                id="builtin.driver_success",
                passed=False,
                detail="driver failed before business validation",
            ),
            ValidationCheck(
                id="phase2.business_assertion.required_marker",
                passed=False,
                detail="required marker missing",
            ),
        ],
    )


def test_stalled_no_progress_takes_precedence_over_validation_for_layer_and_stage() -> None:
    driver_result = _driver("stalled_no_progress")
    validation = _failed_validation()

    assert (
        AgentExecutionRunner._infer_failure_layer("failed", driver_result, validation)  # noqa: SLF001
        == "infra"
    )
    assert (
        AgentExecutionRunner._infer_failure_stage(driver_result, validation)  # noqa: SLF001
        == "stalled_no_progress"
    )


def test_timed_out_takes_precedence_over_validation_for_layer_and_stage() -> None:
    driver_result = _driver("timed_out")
    validation = _failed_validation()

    assert (
        AgentExecutionRunner._infer_failure_layer("failed", driver_result, validation)  # noqa: SLF001
        == "infra"
    )
    assert (
        AgentExecutionRunner._infer_failure_stage(driver_result, validation)  # noqa: SLF001
        == "timed_out"
    )


def test_business_validation_still_wins_when_driver_does_not_timeout_or_stall() -> None:
    driver_result = _driver("succeeded")
    validation = _failed_validation()

    assert (
        AgentExecutionRunner._infer_failure_layer("human_review", driver_result, validation)  # noqa: SLF001
        == "business_validation"
    )
    assert (
        AgentExecutionRunner._infer_failure_stage(driver_result, validation)  # noqa: SLF001
        == "builtin.driver_success"
    )
