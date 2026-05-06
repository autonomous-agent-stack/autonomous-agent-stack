from __future__ import annotations

from autoresearch.core.services.butler_failure_review import (
    ButlerFailureReviewRequest,
    ButlerFailureReviewService,
    classify_butler_failure,
)
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.shared.models import SessionEventRead
from autoresearch.shared.store import InMemoryRepository


def test_hermes_binary_missing_classifies_dependency_missing_and_writes_timeline() -> None:
    session_events = SessionEventService(InMemoryRepository[SessionEventRead]())
    service = ButlerFailureReviewService(session_events=session_events)

    review = service.review(
        ButlerFailureReviewRequest(
            message="整理到GitHub了么",
            task_id="task-1",
            run_id="run-1",
            capability_id="hermes_openclaw",
            worker_error="Hermes executable not found in PATH: hermes",
            worker_result={"error_kind": "binary_missing", "summary": "Hermes executable is unavailable."},
            worker_metrics={"error_kind": "binary_missing"},
            session_id="session-1",
        )
    )

    assert review.failure_kind == "dependency_missing"
    assert review.metadata["review_action"] == "hermes.failure_review"
    timeline = session_events.timeline(session_id="session-1")
    assert [event.event_type for event in timeline.events] == ["butler.failure_reviewed"]
    assert timeline.events[0].metadata["failure_kind"] == "dependency_missing"


def test_worker_payload_contract_error_is_classified() -> None:
    request = ButlerFailureReviewRequest(
        message="content kb",
        capability_id="content_kb",
        worker_error="ValidationError: subtitle_text_path field required",
        worker_metrics={"status": "failed"},
    )

    assert classify_butler_failure(request) == "worker_contract_error"


def test_route_mismatch_writes_rule_candidate_shape(tmp_path) -> None:
    candidates_path = tmp_path / "rule_candidates.yaml"
    service = ButlerFailureReviewService(rule_candidates_path=candidates_path)

    review = service.review(
        ButlerFailureReviewRequest(
            message="整理到GitHub了么",
            task_id="task-2",
            capability_id="source_collect",
            worker_error="route mismatch",
            metadata={
                "route_mismatch": True,
                "expected_capability_id": "butler_context_status",
                "suggested_route": "butler_context_status",
            },
        )
    )

    assert review.failure_kind == "route_mismatch"
    assert review.rule_candidate is not None
    assert review.rule_candidate["status"] == "proposed"
    assert review.rule_candidate["suggested_route"] == "butler_context_status"
    assert candidates_path.exists()
    assert "rule_candidates" in candidates_path.read_text(encoding="utf-8")
