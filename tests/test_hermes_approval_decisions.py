from __future__ import annotations

from autoresearch.core.services.approval_decisions import ApprovalDecisionDeliveryError, ApprovalDecisionService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.hermes_gateway_bridge import InMemoryHermesGatewayTransport
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ApprovalStatus,
    JobStatus,
    WorkerClaimRequest,
    WorkerLeaseRead,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    WorkerRunReportRequest,
    WorkerType,
    utc_now,
)
from autoresearch.shared.store import InMemoryRepository


def test_hermes_approval_decision_submits_callback_and_requeues_run() -> None:
    approval_store = ApprovalStoreService(repository=InMemoryRepository[ApprovalRequestRead]())
    registry = WorkerRegistryService(repository=InMemoryRepository[WorkerRegistrationRead]())
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=InMemoryRepository[WorkerQueueItemRead](),
        lease_repository=InMemoryRepository[WorkerLeaseRead](),
    )
    registry.register(
        WorkerRegisterRequest(
            worker_id="worker-1",
            worker_type=WorkerType.MAC,
            capabilities=["claude_runtime", "hermes_interactive"],
        ),
        now=utc_now(),
    )
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_name="interactive",
            task_type="claude_runtime",
            payload={"runtime_id": "hermes", "execution_mode": "interactive"},
        )
    )
    claimed = scheduler.claim("worker-1", WorkerClaimRequest())
    assert claimed.run is not None
    scheduler.report(
        "worker-1",
        queued.run_id,
        WorkerRunReportRequest(
            status=JobStatus.RUNNING,
            message="waiting for approval",
            metrics={
                "telegram_live_phase": "running",
                "worker_pause_reason": "hermes_interactive_approval",
                "hermes_interactive_waiting_for_approval": True,
            },
        ),
    )
    approval = approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Allow Hermes action",
            telegram_uid="9536",
            source="hermes_interactive_approval",
            metadata={
                "action_type": "hermes_interactive_approval",
                "run_id": queued.run_id,
                "aas_session_id": "aas-1",
                "gateway_session_id": "gw-1",
                "gateway_event_id": "evt-approval",
            },
        )
    )
    transport = InMemoryHermesGatewayTransport(gateway_session_id="gw-1", events=[])
    service = ApprovalDecisionService(
        approval_store=approval_store,
        worker_scheduler=scheduler,
        hermes_transport=transport,
    )

    resolved = service.resolve_request(
        approval.approval_id,
        ApprovalDecisionRequest(
            decision="approved",
            decided_by="9536",
            note="ok",
            metadata={"resolved_via": "test"},
        ),
    )

    assert resolved.status == ApprovalStatus.APPROVED
    assert transport.approval_decisions == [
        {
            "gateway_session_id": "gw-1",
            "event_id": "evt-approval",
            "decision": "approved",
            "decided_by": "9536",
            "note": "ok",
            "metadata": {
                "approval_id": approval.approval_id,
                "action_type": "hermes_interactive_approval",
                "aas_session_id": "aas-1",
                "run_id": queued.run_id,
                "source": "aas_approval_decision",
                "resolved_via": "test",
            },
        }
    ]
    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.QUEUED
    assert run.retry_count == 0
    assert run.recovery_reason == "Hermes interactive approval approved"
    refreshed = approval_store.get_request(approval.approval_id)
    assert refreshed is not None
    assert refreshed.metadata["hermes_requeue_status"] == "requeued"


def test_hermes_approval_callback_failure_leaves_approval_pending() -> None:
    approval_store = ApprovalStoreService(repository=InMemoryRepository[ApprovalRequestRead]())
    approval = approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Allow Hermes action",
            telegram_uid="9536",
            source="hermes_interactive_approval",
            metadata={
                "action_type": "hermes_interactive_approval",
                "run_id": "run-1",
                "gateway_session_id": "gw-1",
                "gateway_event_id": "evt-approval",
            },
        )
    )
    transport = InMemoryHermesGatewayTransport(gateway_session_id="gw-1", events=[])
    transport.approval_error = "gateway down"
    service = ApprovalDecisionService(
        approval_store=approval_store,
        hermes_transport=transport,
    )

    try:
        service.resolve_request(
            approval.approval_id,
            ApprovalDecisionRequest(decision="rejected", decided_by="9536"),
        )
    except ApprovalDecisionDeliveryError as exc:
        assert "gateway down" in str(exc)
    else:
        raise AssertionError("expected delivery error")

    refreshed = approval_store.get_request(approval.approval_id)
    assert refreshed is not None
    assert refreshed.status.value == "pending"
    assert transport.approval_decisions == []
