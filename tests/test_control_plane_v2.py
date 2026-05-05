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
    service, _, _ = build_control_plane()
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


def test_v2_capability_registry_exposes_protocol_boundaries() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    response = client.get("/api/v2/capabilities")
    assert response.status_code == 200
    capabilities = {item["capability_id"]: item for item in response.json()}

    assert capabilities["echo"]["dispatch_mode"] == "worker_queue"
    assert capabilities["worker_queue"]["enabled"] is True
    assert capabilities["github_assistant"]["requires_approval"] is True
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


def test_control_plane_console_exposes_natural_language_butler_form() -> None:
    service, _, _ = build_control_plane()
    client = build_client(service)

    response = client.get("/control-plane")

    assert response.status_code == 200
    assert "/api/v2/butler/tasks" in response.text
    assert "/api/v2/butler/route" in response.text
    assert "自然语言任务 | Natural Language Task" in response.text
