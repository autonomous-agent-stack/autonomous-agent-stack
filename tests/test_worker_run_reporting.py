from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from autoresearch.api.dependencies import get_worker_registry_service, get_worker_scheduler_service
from autoresearch.api.main import app
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    WorkerClaimRequest,
    WorkerLeaseRead,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    WorkerRegisterRequest,
    WorkerType,
    WorkerMode,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def worker_services(tmp_path: Path) -> tuple[WorkerRegistryService, WorkerSchedulerService]:
    db_path = tmp_path / "worker-run-reporting.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_reporting_test",
            model_cls=WorkerRegistrationRead,
        ),
        stale_after_seconds=45,
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_reporting_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_reporting_test",
            model_cls=WorkerLeaseRead,
        ),
        lease_ttl_seconds=60,
    )
    return registry, scheduler


@pytest.fixture
def worker_client(worker_services: tuple[WorkerRegistryService, WorkerSchedulerService]) -> TestClient:
    registry, scheduler = worker_services
    app.dependency_overrides[get_worker_registry_service] = lambda: registry
    app.dependency_overrides[get_worker_scheduler_service] = lambda: scheduler
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _register_worker(registry: WorkerRegistryService, *, worker_id: str) -> None:
    registry.register(
        WorkerRegisterRequest(
            worker_id=worker_id,
            worker_type=WorkerType.MAC,
            mode=WorkerMode.STANDBY,
            role="housekeeper",
            capabilities=["housekeeping"],
        )
    )


def test_enqueue_claim_and_report_lifecycle_via_api(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")

    created = worker_client.post(
        "/api/v1/worker-runs",
        json={
            "queue_name": "housekeeping",
            "task_type": "noop",
            "payload": {"message": "hello"},
            "requested_by": "local_test",
        },
    )
    assert created.status_code == 201
    queued = created.json()
    assert queued["task_name"] == "noop"
    assert queued["task_type"] == "noop"
    assert queued["status"] == "queued"

    claimed = scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now())
    assert claimed.claimed is True
    assert claimed.run is not None

    running = worker_client.post(
        f"/api/v1/workers/mac-mini-01/runs/{claimed.run.run_id}/report",
        json={
            "status": "running",
            "message": "started noop",
            "progress": {"current": 1, "total": 1},
            "metrics": {"operations": 1},
        },
    )
    assert running.status_code == 200
    running_body = running.json()
    assert running_body["status"] == "running"
    assert running_body["message"] == "started noop"
    assert running_body["started_at"] is not None

    completed = worker_client.post(
        f"/api/v1/workers/mac-mini-01/runs/{claimed.run.run_id}/report",
        json={
            "status": "succeeded",
            "message": "noop completed",
            "result": {"echo": "hello"},
        },
    )
    assert completed.status_code == 200
    completed_body = completed.json()
    assert completed_body["status"] == "completed"
    assert completed_body["completed_at"] is not None
    assert completed_body["result"]["echo"] == "hello"

    leases = scheduler.list_leases()
    assert len(leases) == 1
    assert leases[0].active is False


def test_report_rejects_other_worker_for_active_lease(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    _register_worker(registry, worker_id="mac-mini-01")
    _register_worker(registry, worker_id="mac-mini-02")

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_type="noop", payload={"message": "hello"}),
        now=utc_now(),
    )
    claimed = scheduler.claim("mac-mini-01", WorkerClaimRequest(), now=utc_now() + timedelta(seconds=1))
    assert claimed.run is not None

    response = worker_client.post(
        f"/api/v1/workers/mac-mini-02/runs/{queued.run_id}/report",
        json={"status": "failed", "message": "nope", "error": "wrong worker"},
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Run is leased to another worker"


def test_enqueue_youtube_autoflow_via_api(
    worker_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, _ = worker_services
    _register_worker(registry, worker_id="mac-mini-01")

    created = worker_client.post(
        "/api/v1/worker-runs/youtube-autoflow",
        json={
            "input_text": "请处理 https://www.youtube.com/watch?v=video-001",
            "repo_hint": "acme/demo",
            "requested_by": "local_test",
            "metadata": {"source": "api_test"},
        },
    )

    assert created.status_code == 201
    queued = created.json()
    assert queued["task_type"] == "youtube_autoflow"
    assert queued["requested_by"] == "local_test"
    assert queued["payload"]["repo_hint"] == "acme/demo"
