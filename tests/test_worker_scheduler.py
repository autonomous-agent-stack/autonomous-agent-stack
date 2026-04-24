from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_worker_registry_service, get_worker_scheduler_service
from autoresearch.api.main import app
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerClaimError, WorkerSchedulerService
from autoresearch.shared.models import (
    WorkerClaimRequest,
    WorkerHeartbeatRequest,
    WorkerMode,
    WorkerQueueItemCreateRequest,
    WorkerRegistrationRead,
    WorkerType,
    utc_now,
)
from autoresearch.shared.models import WorkerLeaseRead, WorkerQueueItemRead
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def worker_services(tmp_path: Path) -> tuple[WorkerRegistryService, WorkerSchedulerService]:
    db_path = tmp_path / "worker-scheduler.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_scheduler_test",
            model_cls=WorkerRegistrationRead,
        ),
        stale_after_seconds=45,
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_scheduler_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_scheduler_test",
            model_cls=WorkerLeaseRead,
        ),
        lease_ttl_seconds=60,
    )
    return registry, scheduler


@pytest.fixture
def worker_scheduler_client(worker_services: tuple[WorkerRegistryService, WorkerSchedulerService]) -> TestClient:
    registry, scheduler = worker_services
    app.dependency_overrides[get_worker_registry_service] = lambda: registry
    app.dependency_overrides[get_worker_scheduler_service] = lambda: scheduler
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _register_mac_worker(registry: WorkerRegistryService, *, worker_id: str, now=None) -> None:
    from autoresearch.shared.models import WorkerRegisterRequest

    registry.register(
        WorkerRegisterRequest(
            worker_id=worker_id,
            worker_type=WorkerType.MAC,
            mode=WorkerMode.STANDBY,
            role="housekeeper",
            capabilities=["fs"],
        ),
        now=now,
    )


def test_claim_happy_path_creates_deterministic_lease(
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    current = utc_now()
    _register_mac_worker(registry, worker_id="mac-mini-01", now=current)
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_name="cleanup temp files"),
        now=current,
    )

    claimed = scheduler.claim(
        "mac-mini-01",
        WorkerClaimRequest(),
        now=current + timedelta(seconds=1),
    )

    assert claimed.claimed is True
    assert claimed.run is not None
    assert claimed.lease is not None
    assert claimed.run.run_id == queued.run_id
    assert claimed.run.assigned_worker_id == "mac-mini-01"
    assert claimed.lease.lease_id == f"wlease_{queued.run_id}"


def test_claim_returns_no_work_when_queue_is_empty(
    worker_scheduler_client: TestClient,
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, _ = worker_services
    _register_mac_worker(registry, worker_id="mac-mini-01", now=utc_now())

    response = worker_scheduler_client.post("/api/v1/workers/mac-mini-01/claim", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["claimed"] is False
    assert body["reason"] == "no_work_available"


def test_stale_worker_cannot_claim(
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    current = utc_now()
    _register_mac_worker(registry, worker_id="mac-mini-01", now=current)
    scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_name="cleanup temp files"),
        now=current,
    )

    with pytest.raises(WorkerClaimError) as exc:
        scheduler.claim(
            "mac-mini-01",
            WorkerClaimRequest(),
            now=current + timedelta(seconds=46),
        )
    assert str(exc.value) == "Worker is stale and cannot claim work"


def test_existing_active_lease_blocks_other_worker_and_is_idempotent_for_same_worker(
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    current = utc_now()
    _register_mac_worker(registry, worker_id="mac-mini-01", now=current)
    _register_mac_worker(registry, worker_id="mac-mini-02", now=current)
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_name="cleanup temp files"),
        now=current,
    )

    first_claim = scheduler.claim(
        "mac-mini-01",
        WorkerClaimRequest(),
        now=current + timedelta(seconds=1),
    )
    second_claim_same_worker = scheduler.claim(
        "mac-mini-01",
        WorkerClaimRequest(),
        now=current + timedelta(seconds=2),
    )
    blocked = scheduler.claim(
        "mac-mini-02",
        WorkerClaimRequest(),
        now=current + timedelta(seconds=2),
    )

    assert first_claim.claimed is True
    assert second_claim_same_worker.claimed is True
    assert second_claim_same_worker.run is not None
    assert second_claim_same_worker.lease is not None
    assert second_claim_same_worker.run.run_id == queued.run_id
    assert second_claim_same_worker.lease.lease_id == first_claim.lease.lease_id
    assert second_claim_same_worker.reason == "already_claimed"
    assert blocked.claimed is False
    assert blocked.reason == "no_work_available"


def test_expired_lease_allows_reclaim_by_another_worker(
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    registry, scheduler = worker_services
    current = utc_now()
    _register_mac_worker(registry, worker_id="mac-mini-01", now=current)
    _register_mac_worker(registry, worker_id="mac-mini-02", now=current)
    queued = scheduler.enqueue(
        WorkerQueueItemCreateRequest(task_name="cleanup temp files"),
        now=current,
    )

    first = scheduler.claim(
        "mac-mini-01",
        WorkerClaimRequest(),
        now=current + timedelta(seconds=1),
    )
    registry.heartbeat(
        "mac-mini-02",
        WorkerHeartbeatRequest(
            health="ok",
            load=0.0,
            queue_depth=0,
            disk_free_gb=128.0,
            accepting_work=True,
        ),
        now=current + timedelta(seconds=61),
    )
    reclaimed = scheduler.claim(
        "mac-mini-02",
        WorkerClaimRequest(),
        now=current + timedelta(seconds=62),
    )

    assert first.claimed is True
    assert reclaimed.claimed is True
    assert reclaimed.run is not None
    assert reclaimed.lease is not None
    assert reclaimed.run.run_id == queued.run_id
    assert reclaimed.run.assigned_worker_id == "mac-mini-02"
    assert reclaimed.lease.worker_id == "mac-mini-02"


def test_merge_queue_metadata_merges_into_existing(
    worker_services: tuple[WorkerRegistryService, WorkerSchedulerService],
) -> None:
    _, scheduler = worker_services
    item = scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_name="demo",
            metadata={"session_key": "telegram:personal:user:1"},
        ),
    )
    assert item.metadata.get("session_key") == "telegram:personal:user:1"

    updated = scheduler.merge_queue_metadata(
        item.run_id,
        {"telegram_queue_ack_message_id": 4242, "chat_id": "999"},
    )
    assert updated is not None
    assert updated.metadata["telegram_queue_ack_message_id"] == 4242
    assert updated.metadata["chat_id"] == "999"
    assert updated.metadata["session_key"] == "telegram:personal:user:1"
