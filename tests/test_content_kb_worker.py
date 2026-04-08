"""Tests for content_kb worker task type integration."""
from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    JobStatus,
    WorkerLeaseRead,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    WorkerTaskType,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository
from autoresearch.workers.mac.client import InProcessMacWorkerClient
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.workers.mac.daemon import MacWorkerDaemon
from autoresearch.workers.mac.executor import MacWorkerExecutor


@pytest.fixture
def worker_services(tmp_path: Path) -> tuple[WorkerRegistryService, WorkerSchedulerService]:
    db_path = tmp_path / "ckb-worker-test.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_ckb_test",
            model_cls=WorkerRegistrationRead,
        ),
        stale_after_seconds=45,
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_ckb_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_ckb_test",
            model_cls=WorkerLeaseRead,
        ),
        lease_ttl_seconds=60,
    )
    return registry, scheduler


def _build_daemon(
    tmp_path: Path,
    *,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> MacWorkerDaemon:
    registry, scheduler = worker_services
    config = MacWorkerConfig(
        worker_id="test-worker-01",
        control_plane_base_url="http://127.0.0.1:8001",
        worker_name="Test Worker",
        host="test.local",
        heartbeat_seconds=15,
        claim_poll_seconds=5,
        lease_ttl_seconds=60,
        housekeeping_root=tmp_path,
        dry_run=True,
    )
    return MacWorkerDaemon(
        config=config,
        client=InProcessMacWorkerClient(worker_registry=registry, worker_scheduler=scheduler),
        executor=MacWorkerExecutor(config),
        sleep=lambda _: None,
    )


def test_content_kb_classify_task_type_registered() -> None:
    """Verify CONTENT_KB_CLASSIFY exists in the enum."""
    assert hasattr(WorkerTaskType, "CONTENT_KB_CLASSIFY")
    assert WorkerTaskType.CONTENT_KB_CLASSIFY.value == "content_kb_classify"


def test_content_kb_classify_enqueue_claim_execute_report(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """Full lifecycle: enqueue → claim → execute → report for content_kb_classify."""
    registry, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services)

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_CLASSIFY,
            payload={"text": "人工智能和深度学习最新进展"},
            requested_by="test",
        ),
        now=utc_now(),
    )
    assert queued.status == JobStatus.QUEUED
    assert queued.task_type == WorkerTaskType.CONTENT_KB_CLASSIFY

    processed = daemon.run_once(now=utc_now())
    assert processed is True

    worker = registry.get_worker("test-worker-01", as_of=utc_now())
    assert worker is not None

    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.COMPLETED
    assert run.result is not None
    assert run.result["primary_topic"] == "ai-status-and-outlook"
    assert run.result["confidence"] > 0
    assert "alternatives" in run.result


def test_content_kb_classify_fails_without_text(
    tmp_path: Path,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    """Verify executor reports FAILED when text is missing."""
    _, scheduler = worker_services
    daemon = _build_daemon(tmp_path, worker_services=worker_services)

    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_CLASSIFY,
            payload={},
            requested_by="test",
        ),
        now=utc_now(),
    )

    daemon.run_once(now=utc_now())

    run = scheduler.get_run(queued.run_id)
    assert run is not None
    assert run.status == JobStatus.FAILED
    assert run.error is not None
    assert "text" in run.error.lower()


def test_content_kb_classify_via_api() -> None:
    """Verify the convenience endpoint returns a queued run."""
    from fastapi.testclient import TestClient

    from autoresearch.api.main import app

    client = TestClient(app)
    response = client.post(
        "/api/v1/worker-runs/content-kb-classify",
        json={"text": "编程和开发工具", "requested_by": "api-test"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["task_type"] == "content_kb_classify"
    assert data["status"] == "queued"
    assert data["run_id"]
    assert data["payload"]["text"] == "编程和开发工具"
