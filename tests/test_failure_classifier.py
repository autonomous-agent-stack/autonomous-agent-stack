from __future__ import annotations

from autoresearch.agent_protocol.models import DriverResult, ValidationCheck, ValidationReport
from autoresearch.executions.failure_classifier import classify_failure


def _driver(status: str, summary: str = "demo") -> DriverResult:
    return DriverResult(
        run_id="run-1",
        agent_id="agent",
        status=status,  # type: ignore[arg-type]
        summary=summary,
        recommended_action="human_review",
    )


def test_timed_out_maps_to_infra_layer() -> None:
    result = classify_failure(
        driver_result=_driver("timed_out"),
        validation=ValidationReport(run_id="run-1", passed=True),
    )

    assert result.failure_status == "timed_out"
    assert result.failure_layer == "infra"


def test_stalled_no_progress_maps_to_infra_layer() -> None:
    result = classify_failure(
        driver_result=_driver("stalled_no_progress"),
        validation=ValidationReport(run_id="run-1", passed=True),
    )

    assert result.failure_status == "stalled_no_progress"
    assert result.failure_layer == "infra"


def test_mock_fallback_maps_to_orchestration_layer() -> None:
    result = classify_failure(
        driver_result=_driver("succeeded"),
        validation=ValidationReport(run_id="run-1", passed=True),
        metadata={"mock_fallback_enabled": True},
    )

    assert result.failure_status == "mock_fallback"
    assert result.failure_layer == "orchestration"


def test_assertion_failed_maps_to_business_validation_layer() -> None:
    result = classify_failure(
        driver_result=_driver("succeeded"),
        validation=ValidationReport(
            run_id="run-1",
            passed=False,
            checks=[ValidationCheck(id="worker.test_command", passed=False, detail="boom")],
        ),
    )

    assert result.failure_status == "assertion_failed"
    assert result.failure_layer == "business_validation"


def test_infra_error_maps_to_infra_layer() -> None:
    result = classify_failure(
        driver_result=_driver("contract_error"),
        validation=ValidationReport(run_id="run-1", passed=True),
    )

    assert result.failure_status == "infra_error"
    assert result.failure_layer == "infra"


def test_classifier_is_conservative_when_information_is_insufficient() -> None:
    result = classify_failure(
        driver_result=_driver("succeeded"),
        validation=ValidationReport(run_id="run-1", passed=True),
    )

    assert result.failure_status == "unknown"
    assert result.failure_layer is None
