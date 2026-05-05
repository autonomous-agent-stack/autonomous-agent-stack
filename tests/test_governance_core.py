from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoresearch.api.routers.governance_core import (
    get_governance_core_service_dependency,
    router as governance_router,
)
from autoresearch.core.services.governance_core import GovernanceCoreService, GovernanceRepositories
from autoresearch.shared.governance_core import (
    GovernanceApprovalRead,
    GovernanceArtifactRead,
    GovernanceAuditEventRead,
    GovernanceApprovalDecisionRequest,
    GovernanceRunRead,
    GovernanceRunStatus,
    GovernanceTaskCreateRequest,
    GovernanceTaskRead,
    GovernanceTaskStatus,
)
from autoresearch.shared.store import InMemoryRepository


class InlineQueue:
    def submit(self, callback, *args):
        callback(*args)


def build_service() -> GovernanceCoreService:
    return GovernanceCoreService(
        repositories=GovernanceRepositories(
            tasks=InMemoryRepository[GovernanceTaskRead](),
            runs=InMemoryRepository[GovernanceRunRead](),
            approvals=InMemoryRepository[GovernanceApprovalRead](),
            artifacts=InMemoryRepository[GovernanceArtifactRead](),
            audit_events=InMemoryRepository[GovernanceAuditEventRead](),
        ),
        queue=InlineQueue(),
    )


def build_client(service: GovernanceCoreService) -> TestClient:
    app = FastAPI()
    app.include_router(governance_router)
    app.dependency_overrides[get_governance_core_service_dependency] = lambda: service
    return TestClient(app)


def test_low_risk_echo_task_runs_to_completion() -> None:
    service = build_service()

    created = service.create_task(
        GovernanceTaskCreateRequest(
            name="Echo task",
            parameters={"message": "hello"},
            risk_tags=[],
        )
    )

    task = service.get_task(created.task_id)
    assert task is not None
    assert task.status == GovernanceTaskStatus.SUCCEEDED
    assert task.run_id is not None
    assert task.result is not None
    assert task.result["parameters"] == {"message": "hello"}

    run = service.get_run(task.run_id)
    assert run is not None
    assert run.status == GovernanceRunStatus.SUCCEEDED

    events = service.list_run_events(run.run_id)
    event_types = [event.event_type for event in events]
    assert "task.created" in event_types
    assert "policy.auto_approved" in event_types
    assert "run.queued" in event_types
    assert "run.succeeded" in event_types


def test_high_risk_task_waits_for_approval_then_runs() -> None:
    service = build_service()

    created = service.create_task(
        GovernanceTaskCreateRequest(
            name="External task",
            parameters={"target": "github"},
            risk_tags=["external_api"],
        )
    )
    assert created.status == GovernanceTaskStatus.AWAITING_APPROVAL
    assert created.approval_id is not None
    assert created.run_id is None

    approved = service.decide_task(
        created.task_id,
        GovernanceApprovalDecisionRequest(decision="approved", approver="tester"),
    )
    assert approved is not None

    task = service.get_task(created.task_id)
    assert task is not None
    assert task.status == GovernanceTaskStatus.SUCCEEDED
    assert task.run_id is not None


def test_high_risk_task_can_be_rejected() -> None:
    service = build_service()

    created = service.create_task(
        GovernanceTaskCreateRequest(name="Shell task", risk_tags=["shell"])
    )
    rejected = service.decide_task(
        created.task_id,
        GovernanceApprovalDecisionRequest(
            decision="rejected",
            approver="tester",
            note="No shell access.",
        ),
    )

    assert rejected is not None
    assert rejected.status == GovernanceTaskStatus.REJECTED
    assert rejected.error == "No shell access."


def test_api_task_approval_and_events_flow() -> None:
    service = build_service()
    client = build_client(service)

    create_response = client.post(
        "/tasks",
        json={
            "name": "Filesystem task",
            "parameters": {"path": "README.md"},
            "risk_tags": ["filesystem_write"],
        },
    )
    assert create_response.status_code == 202
    created = create_response.json()
    assert created["status"] == "awaiting_approval"

    approve_response = client.post(
        f"/tasks/{created['task_id']}/approve",
        json={"decision": "approved", "approver": "tester"},
    )
    assert approve_response.status_code == 200
    approved = approve_response.json()
    assert approved["status"] in {"queued", "running", "succeeded"}

    task_response = client.get(f"/tasks/{created['task_id']}")
    assert task_response.status_code == 200
    task = task_response.json()
    assert task["status"] == "succeeded"
    assert task["run_id"]

    events_response = client.get(f"/runs/{task['run_id']}/events")
    assert events_response.status_code == 200
    event_types = [event["event_type"] for event in events_response.json()]
    assert "approval.approved" in event_types
    assert "run.succeeded" in event_types


def test_adapters_expose_echo_and_disabled_a2a_boundary() -> None:
    client = build_client(build_service())

    response = client.get("/adapters")
    assert response.status_code == 200
    adapters = {adapter["adapter_id"]: adapter for adapter in response.json()}

    assert adapters["echo"]["enabled"] is True
    assert adapters["echo"]["external_calls_enabled"] is False
    assert adapters["a2a"]["type"] == "a2a"
    assert adapters["a2a"]["external_calls_enabled"] is False
