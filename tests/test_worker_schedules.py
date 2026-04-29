from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import (
    get_worker_registry_service,
    get_worker_schedule_service,
    get_worker_scheduler_service,
)
from autoresearch.api.main import app
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_schedule_service import WorkerScheduleService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    WorkerLeaseRead,
    WorkerQueueItemRead,
    WorkerRegistrationRead,
    WorkerRunScheduleCreateRequest,
    WorkerRunScheduleRead,
    WorkerRunScheduleResumeRequest,
    WorkerScheduleMode,
    WorkerTaskType,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def worker_schedule_services(
    tmp_path: Path,
) -> tuple[WorkerRegistryService, WorkerSchedulerService, WorkerScheduleService]:
    db_path = tmp_path / "worker-schedules.sqlite3"
    registry = WorkerRegistryService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_registrations_schedule_test",
            model_cls=WorkerRegistrationRead,
        ),
        stale_after_seconds=45,
    )
    scheduler = WorkerSchedulerService(
        worker_registry=registry,
        queue_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_run_queue_schedule_test",
            model_cls=WorkerQueueItemRead,
        ),
        lease_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_leases_schedule_test",
            model_cls=WorkerLeaseRead,
        ),
        lease_ttl_seconds=60,
    )
    schedules = WorkerScheduleService(
        worker_scheduler=scheduler,
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="worker_schedules_test",
            model_cls=WorkerRunScheduleRead,
        ),
    )
    return registry, scheduler, schedules


@pytest.fixture
def worker_schedule_client(
    worker_schedule_services: tuple[WorkerRegistryService, WorkerSchedulerService, WorkerScheduleService],
) -> TestClient:
    registry, scheduler, schedules = worker_schedule_services
    app.dependency_overrides[get_worker_registry_service] = lambda: registry
    app.dependency_overrides[get_worker_scheduler_service] = lambda: scheduler
    app.dependency_overrides[get_worker_schedule_service] = lambda: schedules
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_trigger_due_interval_schedule_enqueues_run_and_rolls_forward(
    worker_schedule_services: tuple[WorkerRegistryService, WorkerSchedulerService, WorkerScheduleService],
) -> None:
    _, scheduler, schedules = worker_schedule_services
    current = utc_now()
    created = schedules.create_schedule(
        WorkerRunScheduleCreateRequest(
            schedule_name="nightly noop",
            task_type=WorkerTaskType.NOOP,
            priority=7,
            max_retries=4,
            schedule_mode=WorkerScheduleMode.INTERVAL,
            interval_seconds=300,
            first_run_at=current,
            metadata={"lane": "pilot"},
        ),
        now=current,
    )

    tick = schedules.trigger_due(now=current)

    assert tick.scanned == 1
    assert len(tick.dispatches) == 1
    queued = scheduler.list_queue()
    assert len(queued) == 1
    assert queued[0].priority == 7
    assert queued[0].max_retries == 4
    assert queued[0].metadata["schedule_id"] == created.schedule_id
    assert queued[0].metadata["scheduled_trigger_source"] == "due"
    refreshed = schedules.get_schedule(created.schedule_id)
    assert refreshed is not None
    assert refreshed.enabled is True
    assert refreshed.run_count == 1
    assert refreshed.last_enqueued_run_id == queued[0].run_id
    assert refreshed.next_run_at == current + timedelta(seconds=300)


def test_once_schedule_disables_after_due_tick(
    worker_schedule_services: tuple[WorkerRegistryService, WorkerSchedulerService, WorkerScheduleService],
) -> None:
    _, scheduler, schedules = worker_schedule_services
    current = utc_now()
    created = schedules.create_schedule(
        WorkerRunScheduleCreateRequest(
            schedule_name="one-shot noop",
            task_type=WorkerTaskType.NOOP,
            schedule_mode=WorkerScheduleMode.ONCE,
            first_run_at=current,
        ),
        now=current,
    )

    tick = schedules.trigger_due(now=current)

    assert tick.scanned == 1
    assert len(tick.dispatches) == 1
    assert len(scheduler.list_queue()) == 1
    refreshed = schedules.get_schedule(created.schedule_id)
    assert refreshed is not None
    assert refreshed.enabled is False
    assert refreshed.next_run_at is None


def test_apscheduler_source_advances_interval_schedule(
    worker_schedule_services: tuple[WorkerRegistryService, WorkerSchedulerService, WorkerScheduleService],
) -> None:
    _, scheduler, schedules = worker_schedule_services
    current = utc_now()
    created = schedules.create_schedule(
        WorkerRunScheduleCreateRequest(
            schedule_name="aps interval noop",
            task_type=WorkerTaskType.NOOP,
            schedule_mode=WorkerScheduleMode.INTERVAL,
            interval_seconds=120,
            first_run_at=current,
        ),
        now=current,
    )

    queued = schedules.trigger_schedule(created.schedule_id, now=current, source="apscheduler")

    assert queued.metadata["scheduled_trigger_source"] == "apscheduler"
    assert len(scheduler.list_queue()) == 1
    refreshed = schedules.get_schedule(created.schedule_id)
    assert refreshed is not None
    assert refreshed.enabled is True
    assert refreshed.run_count == 1
    assert refreshed.next_run_at == current + timedelta(seconds=120)


def test_worker_schedule_api_pause_resume_trigger_and_tick(
    worker_schedule_client: TestClient,
    worker_schedule_services: tuple[WorkerRegistryService, WorkerSchedulerService, WorkerScheduleService],
) -> None:
    _, scheduler, schedules = worker_schedule_services
    current = utc_now()
    create_response = worker_schedule_client.post(
        "/api/v1/worker-schedules",
        json={
            "schedule_name": "api interval noop",
            "task_type": "noop",
            "schedule_mode": "interval",
            "interval_seconds": 600,
            "first_run_at": current.isoformat(),
        },
    )
    assert create_response.status_code == 201
    schedule_id = create_response.json()["schedule_id"]

    pause_response = worker_schedule_client.post(f"/api/v1/worker-schedules/{schedule_id}/pause")
    assert pause_response.status_code == 200
    assert pause_response.json()["enabled"] is False

    manual_trigger = worker_schedule_client.post(f"/api/v1/worker-schedules/{schedule_id}/trigger")
    assert manual_trigger.status_code == 201
    assert manual_trigger.json()["metadata"]["schedule_id"] == schedule_id

    resume_response = worker_schedule_client.post(
        f"/api/v1/worker-schedules/{schedule_id}/resume",
        json=WorkerRunScheduleResumeRequest(next_run_at=current).model_dump(mode="json"),
    )
    assert resume_response.status_code == 200
    assert resume_response.json()["enabled"] is True

    tick_response = worker_schedule_client.post("/api/v1/worker-schedules/tick")
    assert tick_response.status_code == 200
    body = tick_response.json()
    assert body["scanned"] == 1
    assert len(body["dispatches"]) == 1

    queued = scheduler.list_queue()
    assert len(queued) == 2
    refreshed = schedules.get_schedule(schedule_id)
    assert refreshed is not None
    assert refreshed.run_count == 2
