from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_session_event_service
from autoresearch.api.main import app
from autoresearch.core.services.approval_decisions import ApprovalDecisionDeliveryError, ApprovalDecisionService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.hermes_gateway_bridge import (
    HermesGatewayEvent,
    InMemoryHermesGatewayTransport,
    PersistedHermesGatewayBridge,
)
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ApprovalStatus,
    HermesInteractiveSessionRead,
    JobStatus,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSessionRead,
    SessionEventCreateRequest,
    SessionEventRead,
    WorkerClaimRequest,
    WorkerHeartbeatRequest,
    WorkerLeaseRead,
    WorkerMode,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    WorkerRunReportRequest,
    WorkerType,
    utc_now,
)
from autoresearch.shared.store import InMemoryRepository


def _session_events() -> SessionEventService:
    return SessionEventService(repository=InMemoryRepository[SessionEventRead]())


def test_session_event_service_append_list_filter_and_idempotency() -> None:
    service = _session_events()
    first = service.append(
        SessionEventCreateRequest(
            session_id="oc-1",
            source="unit",
            event_type="unit.first",
            content="first",
            run_id="run-1",
            idempotency_key="idem-1",
        )
    )
    duplicate = service.append(
        SessionEventCreateRequest(
            session_id="oc-1",
            source="unit",
            event_type="unit.first.changed",
            content="changed",
            idempotency_key="idem-1",
        )
    )
    second = service.append(
        SessionEventCreateRequest(
            session_id="oc-1",
            source="other",
            event_type="unit.second",
            content="second",
            approval_id="apr-1",
        )
    )

    assert duplicate.event_id == first.event_id
    assert duplicate.event_type == "unit.first"
    assert [event.event_id for event in service.list_events(session_id="oc-1")] == [
        first.event_id,
        second.event_id,
    ]
    assert service.list_events(session_id="oc-1", source="unit") == [first]
    assert service.list_events(session_id="oc-1", run_id="run-1") == [first]
    assert service.list_events(session_id="oc-1", approval_id="apr-1") == [second]
    assert service.list_events(session_id="oc-1", after_event_id=first.event_id) == [second]

    timeline = service.timeline(session_id="oc-1")
    assert timeline.latest_event == second
    assert timeline.summary["event_count"] == 2
    assert timeline.correlations["run_ids"] == ["run-1"]
    assert timeline.correlations["approval_ids"] == ["apr-1"]


def test_session_events_api_exposes_events_and_timeline() -> None:
    service = _session_events()
    first = service.append(
        SessionEventCreateRequest(
            session_id="oc-api",
            source="worker_scheduler",
            event_type="worker.run.queued",
            content="queued",
            run_id="run-api",
        )
    )
    service.append(
        SessionEventCreateRequest(
            session_id="oc-api",
            source="approval_store",
            event_type="approval.requested",
            content="approval",
            approval_id="apr-api",
        )
    )
    app.dependency_overrides[get_session_event_service] = lambda: service
    try:
        with TestClient(app) as client:
            filtered = client.get("/api/v1/sessions/oc-api/events?source=worker_scheduler")
            assert filtered.status_code == 200
            assert [item["event_id"] for item in filtered.json()] == [first.event_id]

            timeline = client.get("/api/v1/sessions/oc-api/timeline")
            assert timeline.status_code == 200
            payload = timeline.json()
            assert payload["summary"]["event_count"] == 2
            assert payload["correlations"]["run_ids"] == ["run-api"]
            assert payload["correlations"]["approval_ids"] == ["apr-api"]
    finally:
        app.dependency_overrides.clear()


def test_openclaw_service_projects_session_events() -> None:
    session_events = _session_events()
    openclaw = OpenClawCompatService(
        repository=InMemoryRepository[OpenClawSessionRead](),
        session_events=session_events,
    )

    session = openclaw.create_session(OpenClawSessionCreateRequest(title="Spine smoke"))
    openclaw.append_event(
        session.session_id,
        OpenClawSessionEventAppendRequest(
            role="user",
            content="hello",
            metadata={"run_id": "run-openclaw", "runtime_id": "hermes"},
        ),
    )
    openclaw.set_status(session.session_id, JobStatus.RUNNING, metadata_updates={"latest_agent_run_id": "run-openclaw"})

    event_types = [event.event_type for event in session_events.list_events(session_id=session.session_id)]
    assert event_types == ["session.created", "session.event_appended", "session.status_changed"]
    user_event = session_events.list_events(session_id=session.session_id, run_id="run-openclaw")[0]
    assert user_event.role == "user"
    assert user_event.runtime_id == "hermes"


def test_worker_scheduler_projects_run_lifecycle_events() -> None:
    session_events = _session_events()
    registry = WorkerRegistryService(repository=InMemoryRepository[WorkerRegistrationRead]())
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=InMemoryRepository[WorkerQueueItemRead](),
        lease_repository=InMemoryRepository[WorkerLeaseRead](),
        session_events=session_events,
    )
    registry.register(
        WorkerRegisterRequest(
            worker_id="mac-1",
            worker_type=WorkerType.MAC,
            mode=WorkerMode.STANDBY,
            capabilities=["hermes_interactive"],
        )
    )
    registry.heartbeat("mac-1", WorkerHeartbeatRequest())

    run = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_name="interactive",
            task_type="claude_runtime",
            payload={"runtime_id": "hermes", "execution_mode": "interactive", "session_id": "oc-worker"},
            metadata={"session_id": "oc-worker"},
        )
    )
    scheduler.claim("mac-1", WorkerClaimRequest())
    scheduler.report(
        "mac-1",
        run.run_id,
        WorkerRunReportRequest(
            status="running",
            message="waiting for approval",
            metrics={"hermes_interactive_waiting_for_approval": True},
        ),
    )
    scheduler.requeue_run(run.run_id, reason="approved", backoff_seconds=1, increment_retry=False)

    event_types = [event.event_type for event in session_events.list_events(session_id="oc-worker")]
    assert event_types == [
        "worker.run.queued",
        "worker.run.claimed",
        "worker.run.paused",
        "worker.run.requeued",
    ]
    paused = next(event for event in session_events.list_events(session_id="oc-worker") if event.event_type == "worker.run.paused")
    assert paused.run_id == run.run_id
    assert paused.worker_id == "mac-1"


def test_approval_store_projects_create_resolve_and_expire_events() -> None:
    repository = InMemoryRepository[ApprovalRequestRead]()
    session_events = _session_events()
    approvals = ApprovalStoreService(repository=repository, session_events=session_events)

    pending = approvals.create_request(
        ApprovalRequestCreateRequest(
            title="Approve deploy",
            session_id="oc-approval",
            agent_run_id="run-approval",
            metadata={"worker_id": "mac-1", "runtime_id": "hermes"},
        )
    )
    approvals.resolve_request(
        pending.approval_id,
        ApprovalDecisionRequest(decision="approved", decided_by="owner"),
    )
    expiring = approvals.create_request(
        ApprovalRequestCreateRequest(title="Expire me", session_id="oc-approval")
    )
    repository.save(
        expiring.approval_id,
        expiring.model_copy(update={"expires_at": utc_now() - timedelta(seconds=1)}),
    )
    assert approvals.get_request(expiring.approval_id).status == ApprovalStatus.EXPIRED

    event_types = [event.event_type for event in session_events.list_events(session_id="oc-approval")]
    assert event_types == [
        "approval.requested",
        "approval.approved",
        "approval.requested",
        "approval.expired",
    ]


def test_hermes_decision_delivery_failure_records_pending_side_event() -> None:
    session_events = _session_events()
    approvals = ApprovalStoreService(
        repository=InMemoryRepository[ApprovalRequestRead](),
        session_events=session_events,
    )
    approval = approvals.create_request(
        ApprovalRequestCreateRequest(
            title="Hermes approval",
            session_id="oc-hermes",
            source="hermes_interactive_approval",
            metadata={
                "action_type": "hermes_interactive_approval",
                "gateway_session_id": "gw-1",
                "gateway_event_id": "evt-1",
                "run_id": "run-hermes",
            },
        )
    )
    transport = InMemoryHermesGatewayTransport(gateway_session_id="gw-1", events=[])
    transport.approval_error = "gateway down"
    decisions = ApprovalDecisionService(
        approval_store=approvals,
        hermes_transport=transport,
        session_events=session_events,
    )

    with pytest.raises(ApprovalDecisionDeliveryError):
        decisions.resolve_request(
            approval.approval_id,
            ApprovalDecisionRequest(decision="approved", decided_by="owner"),
        )

    refreshed = approvals.get_request(approval.approval_id)
    assert refreshed.status == ApprovalStatus.PENDING
    event_types = [event.event_type for event in session_events.list_events(session_id="oc-hermes")]
    assert event_types == ["approval.requested", "approval.decision_delivery_failed"]


def test_hermes_approval_required_dedupes_approval_and_gateway_event() -> None:
    session_events = _session_events()
    approvals = ApprovalStoreService(
        repository=InMemoryRepository[ApprovalRequestRead](),
        session_events=session_events,
    )
    gateway_event = HermesGatewayEvent(
        event_id="evt-approval",
        event_type="interactive.approval_required",
        timestamp=utc_now(),
        payload={"title": "Approve shell", "summary": "Hermes wants to continue"},
    )
    transport = InMemoryHermesGatewayTransport(
        gateway_session_id="gw-approval",
        events=[gateway_event, gateway_event],
    )
    bridge = PersistedHermesGatewayBridge(
        repository=InMemoryRepository[HermesInteractiveSessionRead](),
        transport=transport,
        approval_store=approvals,
        session_events=session_events,
    )

    result = bridge.execute_interactive(
        {
            "session_id": "oc-hermes-dedupe",
            "prompt": "continue",
            "runtime_id": "hermes",
            "run_id": "run-hermes-dedupe",
            "worker_id": "mac-1",
        }
    )

    assert result.status == JobStatus.RUNNING
    assert len(approvals.list_requests(session_id="oc-hermes-dedupe")) == 1
    hermes_events = [
        event
        for event in session_events.list_events(session_id="oc-hermes-dedupe")
        if event.event_type == "hermes.interactive.approval_required"
    ]
    assert len(hermes_events) == 1
    assert hermes_events[0].approval_id == approvals.list_requests(session_id="oc-hermes-dedupe")[0].approval_id
