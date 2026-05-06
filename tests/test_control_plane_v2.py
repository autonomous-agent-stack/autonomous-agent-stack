from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoresearch.api.routers.control_plane_v2 import (
    console_router as control_plane_console_router,
    get_butler_dispatch_center_dependency,
    get_control_plane_service_dependency,
    get_session_event_service_dependency,
    router as control_plane_router,
)
from autoresearch.control_plane.butler_bridge import (
    ButlerControlPlaneRouteRequest,
    build_task_request_from_decision,
)
from autoresearch.control_plane.capabilities import ControlPlaneCapabilityRegistry
from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalGrantRead,
    ControlPlaneApprovalRead,
    ControlPlaneArtifactRead,
    ControlPlaneAuditEventRead,
    ControlPlanePromotionRead,
    ControlPlaneRunRead,
    ControlPlaneRunStatus,
    ControlPlaneSessionRead,
    ControlPlaneTaskRead,
    ControlPlaneTaskStatus,
)
from autoresearch.control_plane.service import ControlPlaneRepositories, ControlPlaneService
from autoresearch.core.services.butler_dispatch import ButlerDispatchCenter, ButlerModelFillService
from autoresearch.core.services.github_ops import GitHubOpsRequest
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    JobStatus,
    SessionEventRead,
    StandbyYouTubeAutoflowRequest,
    WorkerClaimRequest,
    WorkerHealth,
    WorkerHeartbeatRequest,
    WorkerLeaseRead,
    WorkerQueueItemRead,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    WorkerRunReportRequest,
    WorkerTaskType,
    WorkerType,
)
from autoresearch.shared.store import InMemoryRepository


def build_control_plane() -> tuple[ControlPlaneService, WorkerSchedulerService, WorkerRegistryService]:
    session_events = SessionEventService(InMemoryRepository[SessionEventRead]())
    worker_registry = WorkerRegistryService(
        repository=InMemoryRepository[WorkerRegistrationRead](),
    )
    worker_scheduler = WorkerSchedulerService(
        worker_registry=worker_registry,
        queue_repository=InMemoryRepository[WorkerQueueItemRead](),
        lease_repository=InMemoryRepository[WorkerLeaseRead](),
        session_events=session_events,
    )
    service = ControlPlaneService(
        repositories=ControlPlaneRepositories(
            sessions=InMemoryRepository[ControlPlaneSessionRead](),
            tasks=InMemoryRepository[ControlPlaneTaskRead](),
            runs=InMemoryRepository[ControlPlaneRunRead](),
            approvals=InMemoryRepository[ControlPlaneApprovalRead](),
            approval_grants=InMemoryRepository[ControlPlaneApprovalGrantRead](),
            artifacts=InMemoryRepository[ControlPlaneArtifactRead](),
            audit_events=InMemoryRepository[ControlPlaneAuditEventRead](),
            promotions=InMemoryRepository[ControlPlanePromotionRead](),
        ),
        worker_scheduler=worker_scheduler,
        session_events=session_events,
    )
    return service, worker_scheduler, worker_registry


def build_client(service: ControlPlaneService) -> TestClient:
    app = FastAPI()
    app.include_router(control_plane_console_router)
    app.include_router(control_plane_router)
    app.dependency_overrides[get_control_plane_service_dependency] = lambda: service
    app.dependency_overrides[get_session_event_service_dependency] = lambda: service._session_events
    app.dependency_overrides[get_butler_dispatch_center_dependency] = lambda: ButlerDispatchCenter(
        model_fill=ButlerModelFillService(enabled=False)
    )
    return TestClient(app)


def register_worker(worker_registry: WorkerRegistryService) -> None:
    worker_registry.register(
        WorkerRegisterRequest(
            worker_id="worker-1",
            worker_type=WorkerType.MAC,
            capabilities=["echo", "worker_queue"],
        )
    )
    worker_registry.heartbeat(
        "worker-1",
        WorkerHeartbeatRequest(
            health=WorkerHealth.OK,
            accepting_work=True,
        ),
    )


def test_butler_decision_maps_to_v2_task_request() -> None:
    center = ButlerDispatchCenter(model_fill=ButlerModelFillService(enabled=False))
    decision = center.dispatch("帮我看这个 PR https://github.com/acme/demo/pull/7")
    request = build_task_request_from_decision(
        request=ButlerControlPlaneRouteRequest(
            message="帮我看这个 PR https://github.com/acme/demo/pull/7",
            session_id="session-butler-map",
            requested_by="tester",
            metadata={"channel": "unit"},
        ),
        decision=decision,
        capabilities=ControlPlaneCapabilityRegistry().list_descriptors(),
    )

    assert request.capability_id == "github_assistant"
    assert request.intent == "帮我看这个 PR https://github.com/acme/demo/pull/7"
    assert request.session_id == "session-butler-map"
    assert request.requested_by == "tester"
    assert request.priority == 8
    assert "external_api" in request.risk_tags
    assert request.parameters["repo"] == "acme/demo"
    assert request.parameters["pr_number"] == 7
    assert request.parameters["action"] == "github_ops.pr_ops"
    assert request.metadata["butler_bridge"] is True


def test_v2_low_risk_task_uses_worker_backbone_and_session_spine() -> None:
    service, worker_scheduler, worker_registry = build_control_plane()
    client = build_client(service)

    response = client.post(
        "/api/v2/tasks",
        json={"name": "v2 echo", "parameters": {"message": "hello"}},
    )
    assert response.status_code == 202
    task = response.json()
    assert task["status"] == "queued"
    assert task["run_id"]
    assert task["session_id"]

    register_worker(worker_registry)
    claim = worker_scheduler.claim("worker-1", WorkerClaimRequest())
    assert claim.claimed is True
    assert claim.run is not None
    assert claim.run.run_id == task["run_id"]
    worker_scheduler.report(
        "worker-1",
        claim.run.run_id,
        WorkerRunReportRequest(
            status=JobStatus.COMPLETED,
            message="done",
            result={"summary": "echo complete"},
        ),
    )

    projected = client.get(f"/api/v2/tasks/{task['task_id']}").json()
    assert projected["status"] == "succeeded"
    assert projected["result"] == {"summary": "echo complete"}

    run = client.get(f"/api/v2/runs/{task['run_id']}").json()
    assert run["status"] == ControlPlaneRunStatus.SUCCEEDED.value
    assert run["output"] == {"summary": "echo complete"}

    timeline = client.get(f"/api/v2/sessions/{task['session_id']}/timeline").json()
    event_types = [event["event_type"] for event in timeline["events"]]
    assert "session.created" in event_types
    assert "task.created" in event_types
    assert "run.queued" in event_types
    assert "worker.run.completed" in event_types


def test_v2_worker_report_sync_updates_projection_and_terminal_timeline() -> None:
    service, worker_scheduler, worker_registry = build_control_plane()
    client = build_client(service)

    task = client.post(
        "/api/v2/tasks",
        json={"name": "sync worker result", "session_id": "session-worker-sync"},
    ).json()
    register_worker(worker_registry)
    claim = worker_scheduler.claim("worker-1", WorkerClaimRequest())
    assert claim.run is not None
    reported = worker_scheduler.report(
        "worker-1",
        claim.run.run_id,
        WorkerRunReportRequest(
            status=JobStatus.COMPLETED,
            message="worker finished",
            result={"summary": "worker output"},
            metrics={"duration_ms": 42},
        ),
    )

    projected_task = service.sync_worker_run(reported)

    assert projected_task is not None
    assert projected_task.status == ControlPlaneTaskStatus.SUCCEEDED
    assert projected_task.result == {"summary": "worker output"}
    run = service.get_run(task["run_id"])
    assert run is not None
    assert run.status == ControlPlaneRunStatus.SUCCEEDED
    assert run.output == {"summary": "worker output"}
    assert run.metadata["worker_status"] == "completed"
    assert run.metadata["worker_message"] == "worker finished"
    assert run.metadata["worker_metrics"] == {"duration_ms": 42}
    assert run.metadata["worker_run_id"] == task["run_id"]

    timeline = client.get("/api/v2/sessions/session-worker-sync/timeline").json()
    event_types = [event["event_type"] for event in timeline["events"]]
    assert "worker.run.completed" in event_types
    assert "run.succeeded" in event_types


def test_v2_cancel_queued_run_operator_updates_projection_and_timeline() -> None:
    service, worker_scheduler, _ = build_control_plane()
    client = build_client(service)

    task = client.post(
        "/api/v2/tasks",
        json={"name": "queued cancel", "session_id": "session-v2-cancel-queued"},
    ).json()

    response = client.post(
        f"/api/v2/tasks/{task['task_id']}/cancel",
        json={"reason": "operator cancelled queued run", "requested_by": "tester"},
    )

    assert response.status_code == 200
    cancelled = response.json()
    assert cancelled["status"] == ControlPlaneTaskStatus.CANCELLED.value
    assert cancelled["run_id"] == task["run_id"]
    worker_run = worker_scheduler.get_run(task["run_id"])
    assert worker_run is not None
    assert worker_run.status == JobStatus.CANCELLED
    run = client.get(f"/api/v2/runs/{task['run_id']}").json()
    assert run["status"] == ControlPlaneRunStatus.CANCELLED.value
    assert run["error"] == "operator cancelled queued run"
    timeline = client.get("/api/v2/sessions/session-v2-cancel-queued/timeline").json()
    event_types = [event["event_type"] for event in timeline["events"]]
    assert "run.cancelled" in event_types


def test_v2_cancel_running_run_records_request_without_terminal_projection() -> None:
    service, worker_scheduler, worker_registry = build_control_plane()
    client = build_client(service)

    task = client.post(
        "/api/v2/tasks",
        json={"name": "running cancel", "session_id": "session-v2-cancel-running"},
    ).json()
    register_worker(worker_registry)
    claim = worker_scheduler.claim("worker-1", WorkerClaimRequest())
    assert claim.run is not None
    running_worker = worker_scheduler.report(
        "worker-1",
        claim.run.run_id,
        WorkerRunReportRequest(status=JobStatus.RUNNING, message="started"),
    )
    service.sync_worker_run(running_worker)

    response = client.post(
        f"/api/v2/runs/{task['run_id']}/cancel",
        json={"reason": "operator requested stop", "requested_by": "tester"},
    )

    assert response.status_code == 200
    projected = response.json()
    assert projected["status"] == ControlPlaneTaskStatus.RUNNING.value
    worker_run = worker_scheduler.get_run(task["run_id"])
    assert worker_run is not None
    assert worker_run.status == JobStatus.RUNNING
    assert worker_run.metadata["cancel_requested"] is True
    assert worker_run.metadata["cancel_reason"] == "operator requested stop"
    run = client.get(f"/api/v2/runs/{task['run_id']}").json()
    assert run["status"] == ControlPlaneRunStatus.RUNNING.value
    assert run["metadata"]["cancel_requested"] is True
    timeline = client.get("/api/v2/sessions/session-v2-cancel-running/timeline").json()
    event_types = [event["event_type"] for event in timeline["events"]]
    assert "run.cancel_requested" in event_types


def test_v2_force_fail_operator_updates_projection_and_timeline() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    task = client.post(
        "/api/v2/tasks",
        json={"name": "force fail", "session_id": "session-v2-force-fail"},
    ).json()

    response = client.post(
        f"/api/v2/runs/{task['run_id']}/force-fail",
        json={"reason": "operator forced failure", "requested_by": "tester"},
    )

    assert response.status_code == 200
    failed = response.json()
    assert failed["status"] == ControlPlaneTaskStatus.FAILED.value
    run = client.get(f"/api/v2/runs/{task['run_id']}").json()
    assert run["status"] == ControlPlaneRunStatus.FAILED.value
    assert run["error"] == "operator forced failure"
    timeline = client.get("/api/v2/sessions/session-v2-force-fail/timeline").json()
    event_types = [event["event_type"] for event in timeline["events"]]
    assert "run.failed" in event_types


def test_v2_retry_failed_run_creates_new_run_with_lineage_metadata() -> None:
    service, worker_scheduler, _ = build_control_plane()
    client = build_client(service)

    task = client.post(
        "/api/v2/tasks",
        json={"name": "retry failed", "session_id": "session-v2-retry-failed"},
    ).json()
    old_run_id = task["run_id"]
    worker_scheduler.merge_queue_metadata(
        old_run_id,
        {
            "telegram_completion_via_api": True,
            "chat_id": "9710",
            "session_key": "telegram:personal:user:9710",
            "telegram_queue_ack_message_id": 123,
            "telegram_butler_primary_sent": True,
        },
    )
    failed = client.post(
        f"/api/v2/runs/{old_run_id}/force-fail",
        json={"reason": "make retryable", "requested_by": "tester"},
    ).json()
    assert failed["status"] == ControlPlaneTaskStatus.FAILED.value

    response = client.post(
        f"/api/v2/runs/{old_run_id}/retry",
        json={"reason": "try again", "requested_by": "tester", "metadata": {"ticket": "ops-1"}},
    )

    assert response.status_code == 200
    retried = response.json()
    new_run_id = retried["run_id"]
    assert new_run_id != old_run_id
    assert retried["status"] == ControlPlaneTaskStatus.QUEUED.value
    assert retried["metadata"]["previous_run_ids"] == [old_run_id]
    assert retried["metadata"]["latest_retry_of_run_id"] == old_run_id
    old_run = client.get(f"/api/v2/runs/{old_run_id}").json()
    assert old_run["status"] == ControlPlaneRunStatus.FAILED.value
    new_run = client.get(f"/api/v2/runs/{new_run_id}").json()
    assert new_run["status"] == ControlPlaneRunStatus.QUEUED.value
    assert new_run["metadata"]["retry_of_run_id"] == old_run_id
    assert new_run["metadata"]["retry_of_worker_run_id"] == old_run_id
    assert new_run["metadata"]["retry_sequence"] == 1
    assert new_run["metadata"]["operator_metadata"] == {"ticket": "ops-1"}
    new_worker = worker_scheduler.get_run(new_run_id)
    assert new_worker is not None
    assert new_worker.metadata["control_plane_task_id"] == retried["task_id"]
    assert new_worker.metadata["control_plane_session_id"] == "session-v2-retry-failed"
    assert new_worker.metadata["capability_id"] == "echo"
    assert new_worker.metadata["telegram_completion_via_api"] is True
    assert new_worker.metadata["chat_id"] == "9710"
    assert new_worker.metadata["session_key"] == "telegram:personal:user:9710"
    assert "telegram_butler_primary_sent" not in new_worker.metadata
    timeline = client.get("/api/v2/sessions/session-v2-retry-failed/timeline").json()
    event_types = [event["event_type"] for event in timeline["events"]]
    assert "task.retried" in event_types
    assert event_types.count("run.queued") == 2


def test_v2_retry_cancelled_task_creates_new_run() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    task = client.post(
        "/api/v2/tasks",
        json={"name": "retry cancelled", "session_id": "session-v2-retry-cancelled"},
    ).json()
    old_run_id = task["run_id"]
    cancelled = client.post(
        f"/api/v2/tasks/{task['task_id']}/cancel",
        json={"reason": "cancel before retry", "requested_by": "tester"},
    ).json()
    assert cancelled["status"] == ControlPlaneTaskStatus.CANCELLED.value

    response = client.post(
        f"/api/v2/tasks/{task['task_id']}/retry",
        json={"reason": "retry cancelled task", "requested_by": "tester"},
    )

    assert response.status_code == 200
    retried = response.json()
    assert retried["run_id"] != old_run_id
    assert retried["status"] == ControlPlaneTaskStatus.QUEUED.value
    assert retried["metadata"]["previous_run_ids"] == [old_run_id]
    old_run = client.get(f"/api/v2/runs/{old_run_id}").json()
    assert old_run["status"] == ControlPlaneRunStatus.CANCELLED.value


def test_v2_retry_rejects_non_terminal_current_runs_and_missing_targets() -> None:
    service, worker_scheduler, worker_registry = build_control_plane()
    client = build_client(service)

    queued = client.post("/api/v2/tasks", json={"name": "queued retry"}).json()
    queued_retry = client.post(f"/api/v2/tasks/{queued['task_id']}/retry", json={"reason": "too early"})
    assert queued_retry.status_code == 409

    register_worker(worker_registry)
    claim = worker_scheduler.claim("worker-1", WorkerClaimRequest())
    assert claim.run is not None
    running_worker = worker_scheduler.report(
        "worker-1",
        claim.run.run_id,
        WorkerRunReportRequest(status=JobStatus.RUNNING, message="started"),
    )
    service.sync_worker_run(running_worker)
    running_retry = client.post(f"/api/v2/runs/{queued['run_id']}/retry", json={"reason": "still running"})
    assert running_retry.status_code == 409

    service2, worker_scheduler2, worker_registry2 = build_control_plane()
    client2 = build_client(service2)
    succeeded = client2.post("/api/v2/tasks", json={"name": "succeeded retry"}).json()
    register_worker(worker_registry2)
    claim2 = worker_scheduler2.claim("worker-1", WorkerClaimRequest())
    assert claim2.run is not None
    completed_worker = worker_scheduler2.report(
        "worker-1",
        claim2.run.run_id,
        WorkerRunReportRequest(status=JobStatus.COMPLETED, message="done"),
    )
    service2.sync_worker_run(completed_worker)
    succeeded_retry = client2.post(f"/api/v2/tasks/{succeeded['task_id']}/retry", json={"reason": "done"})
    assert succeeded_retry.status_code == 409

    missing_task = client.post("/api/v2/tasks/task_missing/retry", json={"reason": "missing"})
    missing_run = client.post("/api/v2/runs/run_missing/retry", json={"reason": "missing"})
    assert missing_task.status_code == 404
    assert missing_run.status_code == 404


def test_v2_high_risk_task_requires_approval_before_enqueue() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    create = client.post(
        "/api/v2/tasks",
        json={
            "name": "write filesystem",
            "risk_tags": ["filesystem_write"],
            "parameters": {"path": "README.md"},
        },
    )
    assert create.status_code == 202
    task = create.json()
    assert task["status"] == ControlPlaneTaskStatus.AWAITING_APPROVAL.value
    assert task["approval_id"]
    assert task["run_id"] is None

    approve = client.post(
        f"/api/v2/tasks/{task['task_id']}/approval",
        json={"decision": "approved", "decided_by": "tester"},
    )
    assert approve.status_code == 200
    approved = approve.json()
    assert approved["status"] == ControlPlaneTaskStatus.QUEUED.value
    assert approved["run_id"]

    events = client.get(f"/api/v2/runs/{approved['run_id']}/events").json()
    event_types = [event["event_type"] for event in events]
    assert "approval.requested" in event_types
    assert "approval.approved" in event_types
    assert "run.queued" in event_types


def test_v2_rejected_task_never_dispatches() -> None:
    service, worker_scheduler, _ = build_control_plane()
    client = build_client(service)

    created = client.post(
        "/api/v2/tasks",
        json={"name": "external task", "risk_tags": ["external_api"]},
    ).json()
    rejected = client.post(
        f"/api/v2/tasks/{created['task_id']}/approval",
        json={"decision": "rejected", "decided_by": "tester", "note": "No external calls."},
    ).json()

    assert rejected["status"] == ControlPlaneTaskStatus.REJECTED.value
    assert rejected["run_id"] is None
    assert rejected["error"] == "No external calls."
    assert worker_scheduler.list_queue() == []


def test_v2_capability_registry_exposes_protocol_boundaries() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    response = client.get("/api/v2/capabilities")
    assert response.status_code == 200
    capabilities = {item["capability_id"]: item for item in response.json()}

    assert capabilities["echo"]["dispatch_mode"] == "worker_queue"
    assert capabilities["worker_queue"]["enabled"] is True
    assert capabilities["github_assistant"]["requires_approval"] is True
    assert capabilities["source_collect"]["external_calls_enabled"] is True
    assert "external_api" in capabilities["source_collect"]["risk_tags"]
    assert capabilities["mcp"]["external_calls_enabled"] is False
    assert capabilities["a2a"]["external_calls_enabled"] is False
    assert capabilities["adk_workflow"]["enabled"] is False


def test_butler_route_creates_task_draft_without_creating_task() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    response = client.post(
        "/api/v2/butler/route",
        json={
            "message": "帮我核对3月提成表",
            "session_id": "session-route-only",
            "requested_by": "tester",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["task"] is None
    assert payload["task_request"]["capability_id"] == "excel_audit"
    assert payload["task_request"]["priority"] == 3
    assert service.list_tasks() == []

    timeline = client.get("/api/v2/sessions/session-route-only/timeline").json()
    event_types = [event["event_type"] for event in timeline["events"]]
    assert event_types == ["butler.route.decided"]


def test_butler_task_routes_github_to_approval_control_plane() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    response = client.post(
        "/api/v2/butler/tasks",
        json={
            "message": "帮我 review 这个 PR https://github.com/acme/demo/pull/7",
            "session_id": "session-github-butler",
            "requested_by": "tester",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["task_request"]["capability_id"] == "github_assistant"
    assert "external_api" in payload["task_request"]["risk_tags"]
    task = payload["task"]
    assert task["capability_id"] == "github_assistant"
    assert task["status"] == ControlPlaneTaskStatus.AWAITING_APPROVAL.value
    assert task["approval_id"]
    assert "external_api" in task["risk_tags"]

    timeline = client.get("/api/v2/sessions/session-github-butler/timeline").json()
    event_types = [event["event_type"] for event in timeline["events"]]
    assert "butler.route.decided" in event_types
    assert "task.created" in event_types
    assert "approval.requested" in event_types


def test_butler_task_routes_excel_commission_to_worker_queue() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    response = client.post(
        "/api/v2/butler/tasks",
        json={"message": "帮我核对3月提成表", "session_id": "session-excel-butler"},
    )

    assert response.status_code == 202
    payload = response.json()
    task = payload["task"]
    assert payload["task_request"]["capability_id"] == "excel_audit"
    assert task["capability_id"] == "excel_audit"
    assert task["status"] == ControlPlaneTaskStatus.QUEUED.value
    assert task["run_id"]

    run = client.get(f"/api/v2/runs/{task['run_id']}").json()
    assert run["metadata"]["worker_task_type"] == "excel_audit"

    timeline = client.get("/api/v2/sessions/session-excel-butler/timeline").json()
    event_types = [event["event_type"] for event in timeline["events"]]
    assert "butler.route.decided" in event_types
    assert "task.created" in event_types
    assert "run.queued" in event_types


def test_butler_task_routes_youtube_to_autoflow_approval() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    response = client.post(
        "/api/v2/butler/tasks",
        json={
            "message": "总结这个 YouTube https://youtube.com/watch?v=abc123",
            "session_id": "session-youtube-butler",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    task = payload["task"]
    assert payload["task_request"]["capability_id"] == "youtube_autoflow"
    assert task["capability_id"] == "youtube_autoflow"
    assert task["status"] == ControlPlaneTaskStatus.AWAITING_APPROVAL.value
    assert "external_api" in task["risk_tags"]


def test_butler_task_routes_unknown_to_hermes_openclaw() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    response = client.post(
        "/api/v2/butler/tasks",
        json={"message": "帮我想想今天这些杂事怎么安排", "session_id": "session-hermes-butler"},
    )

    assert response.status_code == 202
    payload = response.json()
    task = payload["task"]
    assert payload["dispatch_decision"]["canonical_task_type"] == "hermes.general"
    assert payload["task_request"]["capability_id"] == "hermes_openclaw"
    assert task["capability_id"] == "hermes_openclaw"
    assert task["status"] == ControlPlaneTaskStatus.QUEUED.value


def test_v2_capability_worker_payloads_match_worker_contracts() -> None:
    service, worker_scheduler, _ = build_control_plane()
    client = build_client(service)

    github = client.post(
        "/api/v2/butler/tasks",
        json={
            "message": "帮我看这个 PR https://github.com/acme/demo/pull/12",
            "session_id": "payload-github",
        },
    ).json()["task"]
    github_approved = client.post(
        f"/api/v2/tasks/{github['task_id']}/approval",
        json={"decision": "approved", "decided_by": "tester"},
    ).json()
    github_run = worker_scheduler.get_run(github_approved["run_id"])
    assert github_run is not None
    assert github_run.task_type == WorkerTaskType.GITHUB_OPS
    github_request = GitHubOpsRequest.model_validate(github_run.payload)
    assert github_request.action == "summarize_pr"
    assert github_request.repo == "acme/demo"
    assert github_request.pr_number == 12

    youtube = client.post(
        "/api/v2/butler/tasks",
        json={
            "message": "总结这个 YouTube https://youtube.com/watch?v=abc123",
            "session_id": "payload-youtube",
        },
    ).json()["task"]
    youtube_approved = client.post(
        f"/api/v2/tasks/{youtube['task_id']}/approval",
        json={"decision": "approved", "decided_by": "tester"},
    ).json()
    youtube_run = worker_scheduler.get_run(youtube_approved["run_id"])
    assert youtube_run is not None
    assert youtube_run.task_type == WorkerTaskType.YOUTUBE_AUTOFLOW
    youtube_request = StandbyYouTubeAutoflowRequest.model_validate(youtube_run.payload)
    assert youtube_request.source_url == "https://youtube.com/watch?v=abc123"
    assert youtube_request.input_text == "总结这个 YouTube https://youtube.com/watch?v=abc123"

    excel = client.post(
        "/api/v2/butler/tasks",
        json={"message": "帮我核对 sales.xlsx 和 commission.xlsx 的提成差异"},
    ).json()["task"]
    excel_run = worker_scheduler.get_run(excel["run_id"])
    assert excel_run is not None
    assert excel_run.task_type == WorkerTaskType.EXCEL_AUDIT
    assert excel_run.payload["task_brief"] == "帮我核对 sales.xlsx 和 commission.xlsx 的提成差异"
    assert excel_run.payload["source_files"] == ["sales.xlsx", "commission.xlsx"]
    assert excel_run.payload["rules"] == []
    assert excel_run.payload["sheet_mapping"] == {}
    assert excel_run.payload["outputs"] == {}

    content = client.post(
        "/api/v2/butler/tasks",
        json={"message": "把字幕入库到知识库", "session_id": "payload-content-kb"},
    ).json()["task"]
    content_approved = client.post(
        f"/api/v2/tasks/{content['task_id']}/approval",
        json={"decision": "approved", "decided_by": "tester"},
    ).json()
    content_run = worker_scheduler.get_run(content_approved["run_id"])
    assert content_run is not None
    assert content_run.task_type == WorkerTaskType.CONTENT_KB_INGEST
    assert content_run.payload["subtitle_text_path"] == ""
    assert content_run.payload["request_text"] == "把字幕入库到知识库"


def test_butler_x_bookmarks_routes_source_collect_then_content_kb() -> None:
    service, worker_scheduler, worker_registry = build_control_plane()
    client = build_client(service)

    response = client.post(
        "/api/v2/butler/tasks",
        json={
            "message": "帮我整理一下 X 书签",
            "session_id": "payload-x-bookmarks",
        },
    )

    assert response.status_code == 202
    payload = response.json()
    task = payload["task"]
    assert payload["dispatch_decision"]["canonical_task_type"] == "source_collect.collect"
    assert payload["task_request"]["capability_id"] == "source_collect"
    assert task["capability_id"] == "source_collect"
    assert task["status"] == ControlPlaneTaskStatus.AWAITING_APPROVAL.value

    approved = client.post(
        f"/api/v2/tasks/{task['task_id']}/approval",
        json={"decision": "approved", "decided_by": "tester"},
    ).json()
    source_run = worker_scheduler.get_run(approved["run_id"])
    assert source_run is not None
    assert source_run.task_type == WorkerTaskType.SOURCE_COLLECT
    assert source_run.payload["source_kind"] == "x_bookmarks"
    assert source_run.payload["collector"] == "xreach"
    assert source_run.payload["runtime_id"] == "source_collect"
    assert source_run.payload["downstream_capability_id"] == "content_kb"

    register_worker(worker_registry)
    claim = worker_scheduler.claim("worker-1", WorkerClaimRequest())
    assert claim.run is not None
    assert claim.run.run_id == source_run.run_id
    reported = worker_scheduler.report(
        "worker-1",
        source_run.run_id,
        WorkerRunReportRequest(
            status=JobStatus.COMPLETED,
            message="source collected",
            result={
                "artifact_path": "/tmp/x-bookmarks.txt",
                "content_kb_payload": {
                    "subtitle_text_path": "/tmp/x-bookmarks.txt",
                    "title": "整理 X 书签",
                    "topic": "",
                    "source_url": "https://twitter.com/example/status/1",
                    "source_kind": "x_bookmarks",
                },
            },
        ),
    )
    downstream_task = service.sync_worker_run(reported)

    assert downstream_task is not None
    assert downstream_task.status == ControlPlaneTaskStatus.QUEUED
    assert downstream_task.run_id != source_run.run_id
    downstream_run = worker_scheduler.get_run(downstream_task.run_id or "")
    assert downstream_run is not None
    assert downstream_run.task_type == WorkerTaskType.CONTENT_KB_INGEST
    assert downstream_run.payload["subtitle_text_path"] == "/tmp/x-bookmarks.txt"
    assert downstream_run.payload["source_kind"] == "x_bookmarks"


def test_control_plane_console_exposes_natural_language_butler_form() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    response = client.get("/control-plane")

    assert response.status_code == 200
    assert "/api/v2/butler/tasks" in response.text
    assert "/api/v2/butler/route" in response.text
    assert "自然语言任务 | Natural Language Task" in response.text
