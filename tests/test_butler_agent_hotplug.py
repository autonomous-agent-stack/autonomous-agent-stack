from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_butler_agent_state_service
from autoresearch.api.routers.butler import router as butler_router
from autoresearch.control_plane.service import ControlPlaneRepositories, ControlPlaneService
from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalGrantRead,
    ControlPlaneApprovalRead,
    ControlPlaneArtifactRead,
    ControlPlaneAuditEventRead,
    ControlPlanePromotionRead,
    ControlPlaneRunRead,
    ControlPlaneSessionRead,
    ControlPlaneTaskCreateRequest,
    ControlPlaneTaskRead,
    ControlPlaneTaskStatus,
)
from autoresearch.core.services.butler_agent_state import ButlerAgentStateService
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.models import (
    ButlerAgentStateRead,
    ButlerAgentStatus,
    SessionEventRead,
    WorkerClaimRequest,
    WorkerLeaseRead,
    WorkerMode,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    WorkerTaskType,
    WorkerType,
)
from autoresearch.shared.store import InMemoryRepository


def test_butler_agent_state_defaults_and_transitions() -> None:
    service = ButlerAgentStateService(repository=InMemoryRepository[ButlerAgentStateRead]())

    agents = service.list_agents()
    assert [item.agent_name for item in agents][:3] == [
        "butler_orchestrator",
        "source_collect",
        "content_kb",
    ]
    assert all(item.status == ButlerAgentStatus.ACTIVE for item in agents)

    disabled = service.set_status(
        "source_collect",
        ButlerAgentStatus.DISABLED,
        actor="test",
        reason="maintenance",
    )
    assert disabled.status == ButlerAgentStatus.DISABLED
    assert disabled.reason == "maintenance"
    assert service.is_active("source_collect") is False

    active = service.set_status("SOURCE_COLLECT", ButlerAgentStatus.ACTIVE, actor="test")
    assert active.agent_name == "source_collect"
    assert active.status == ButlerAgentStatus.ACTIVE
    assert service.is_active("source_collect") is True


def test_worker_claim_skips_disabled_target_agent_then_recovers() -> None:
    agent_state = ButlerAgentStateService(repository=InMemoryRepository[ButlerAgentStateRead]())
    registry = WorkerRegistryService(repository=InMemoryRepository[WorkerRegistrationRead]())
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=InMemoryRepository[WorkerQueueItemRead](),
        lease_repository=InMemoryRepository[WorkerLeaseRead](),
        butler_agent_state=agent_state,
    )
    registry.register(
        WorkerRegisterRequest(
            worker_id="worker-1",
            worker_type=WorkerType.MAC,
            mode=WorkerMode.ACTIVE,
            capabilities=["source_collect"],
        )
    )
    agent_state.set_status("source_collect", ButlerAgentStatus.DISABLED, actor="test")
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.SOURCE_COLLECT,
            metadata={"target_agent": "source_collect"},
        )
    )

    blocked = scheduler.claim("worker-1", WorkerClaimRequest())
    assert blocked.claimed is False
    assert scheduler.get_run(queued.run_id) is not None

    agent_state.set_status("source_collect", ButlerAgentStatus.ACTIVE, actor="test")
    claimed = scheduler.claim("worker-1", WorkerClaimRequest())
    assert claimed.claimed is True
    assert claimed.run is not None
    assert claimed.run.run_id == queued.run_id


def test_control_plane_rejects_disabled_butler_agent_without_enqueueing() -> None:
    agent_state = ButlerAgentStateService(repository=InMemoryRepository[ButlerAgentStateRead]())
    agent_state.set_status("source_collect", ButlerAgentStatus.DISABLED, actor="test")
    registry = WorkerRegistryService(repository=InMemoryRepository[WorkerRegistrationRead]())
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=InMemoryRepository[WorkerQueueItemRead](),
        lease_repository=InMemoryRepository[WorkerLeaseRead](),
        butler_agent_state=agent_state,
    )
    control_plane = ControlPlaneService(
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
        worker_scheduler=scheduler,
        session_events=SessionEventService(repository=InMemoryRepository[SessionEventRead]()),
        butler_agent_state=agent_state,
    )

    task = control_plane.create_task(
        ControlPlaneTaskCreateRequest(
            name="collect bookmarks",
            capability_id="source_collect",
        )
    )

    assert task.status == ControlPlaneTaskStatus.REJECTED
    assert task.run_id is None
    assert task.metadata["butler_agent_hotplug"] is True
    assert scheduler.list_queue() == []


def test_butler_agent_api_lists_and_stops_agent() -> None:
    service = ButlerAgentStateService(repository=InMemoryRepository[ButlerAgentStateRead]())
    app = FastAPI()
    app.include_router(butler_router)
    app.dependency_overrides[get_butler_agent_state_service] = lambda: service
    client = TestClient(app)

    listing = client.get("/api/v1/butler/agents")
    assert listing.status_code == 200
    assert any(item["agent_name"] == "source_collect" for item in listing.json())

    stopped = client.post(
        "/api/v1/butler/agents/source_collect/stop",
        json={"actor": "test", "reason": "maintenance"},
    )
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "disabled"
    assert service.is_active("source_collect") is False


def test_butlerctl_service_dry_run_lists_service_scripts() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "scripts/butlerctl", "--dry-run", "status", "all"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "status-api-daemon.sh" in completed.stdout
    assert "status-telegram-poller.sh" in completed.stdout
    assert "status-mac-worker-daemon.sh" in completed.stdout


def test_butlerctl_restart_all_uses_safe_stop_then_start_order() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "scripts/butlerctl", "--dry-run", "restart", "all"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    scripts = [line.rsplit("/", 1)[-1] for line in completed.stdout.splitlines() if line.startswith("bash ")]
    assert scripts == [
        "stop-mac-worker-daemon.sh",
        "stop-telegram-poller.sh",
        "stop-api-daemon.sh",
        "start-api-daemon.sh",
        "start-telegram-poller.sh",
        "start-mac-worker-daemon.sh",
    ]
