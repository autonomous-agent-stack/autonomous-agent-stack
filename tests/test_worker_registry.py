from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_worker_registry_service
from autoresearch.api.main import app
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.models import (
    WorkerHealth,
    WorkerHeartbeatRequest,
    WorkerMode,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    WorkerType,
    utc_now,
)
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def worker_service(tmp_path: Path) -> WorkerRegistryService:
    repository = SQLiteModelRepository(
        db_path=tmp_path / "worker-registry.sqlite3",
        table_name="worker_registrations_test",
        model_cls=WorkerRegistrationRead,
    )
    return WorkerRegistryService(repository=repository, stale_after_seconds=45)


@pytest.fixture
def worker_client(worker_service: WorkerRegistryService) -> TestClient:
    app.dependency_overrides[get_worker_registry_service] = lambda: worker_service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_worker_register_and_heartbeat_flow(worker_client: TestClient) -> None:
    registered = worker_client.post(
        "/api/v1/workers/register",
        json={
            "worker_id": "mac-mini-01",
            "worker_type": "mac",
            "name": "Mac Mini Standby",
            "host": "mac-mini.local",
            "mode": "standby",
            "role": "housekeeper",
            "capabilities": ["fs", "claude-cli", "fs", "telegram-poller"],
            "metadata": {"site": "home"},
        },
    )
    assert registered.status_code == 200
    body = registered.json()
    assert body["worker_type"] == "mac"
    assert body["mode"] == "standby"
    assert body["role"] == "housekeeper"
    assert body["capabilities"] == ["fs", "claude-cli", "telegram-poller"]
    assert body["is_stale"] is False

    heartbeat = worker_client.post(
        "/api/v1/workers/mac-mini-01/heartbeat",
        json={
            "health": "ok",
            "load": 0.21,
            "queue_depth": 2,
            "disk_free_gb": 412.7,
            "accepting_work": True,
            "metadata": {"pool": "ops_fallback"},
        },
    )
    assert heartbeat.status_code == 200
    updated = heartbeat.json()
    assert updated["health"] == "ok"
    assert updated["load"] == 0.21
    assert updated["queue_depth"] == 2
    assert updated["disk_free_gb"] == 412.7
    assert updated["metadata"]["site"] == "home"
    assert updated["metadata"]["pool"] == "ops_fallback"


def test_duplicate_registration_preserves_identity_and_updates_configuration(
    worker_service: WorkerRegistryService,
) -> None:
    initial = utc_now()
    first = worker_service.register(
        WorkerRegisterRequest(
            worker_id="mac-mini-01",
            worker_type=WorkerType.MAC,
            name="Mac Mini Standby",
            mode=WorkerMode.STANDBY,
            role="housekeeper",
            capabilities=["fs"],
        ),
        now=initial,
    )

    second = worker_service.register(
        WorkerRegisterRequest(
            worker_id="mac-mini-01",
            worker_type=WorkerType.MAC,
            name="Mac Mini Standby v2",
            host="mac-mini.local",
            mode=WorkerMode.STANDBY,
            role="backup",
            capabilities=["browser", "fs", "browser"],
            metadata={"site": "home"},
        ),
        now=initial + timedelta(seconds=5),
    )

    assert first.worker_id == second.worker_id
    assert second.registered_at == first.registered_at
    assert second.updated_at > first.updated_at
    assert second.name == "Mac Mini Standby v2"
    assert second.role == "backup"
    assert second.capabilities == ["browser", "fs"]
    assert len(worker_service.list_workers()) == 1


def test_worker_registry_marks_stale_workers_deterministically(
    worker_service: WorkerRegistryService,
) -> None:
    registered_at = utc_now()
    worker = worker_service.register(
        WorkerRegisterRequest(
            worker_id="mac-mini-01",
            worker_type=WorkerType.MAC,
            mode=WorkerMode.STANDBY,
            capabilities=["fs"],
        ),
        now=registered_at,
    )
    assert worker.is_stale is False

    stale = worker_service.get_worker(
        "mac-mini-01",
        as_of=registered_at + timedelta(seconds=46),
    )
    assert stale is not None
    assert stale.is_stale is True

    refreshed = worker_service.heartbeat(
        "mac-mini-01",
        WorkerHeartbeatRequest(
            health=WorkerHealth.OK,
            load=0.1,
            queue_depth=0,
            disk_free_gb=300.0,
            accepting_work=True,
        ),
        now=registered_at + timedelta(seconds=47),
    )
    assert refreshed.is_stale is False

    current = worker_service.get_worker(
        "mac-mini-01",
        as_of=registered_at + timedelta(seconds=47),
    )
    assert current is not None
    assert current.is_stale is False


def test_heartbeat_returns_404_for_unknown_worker(worker_client: TestClient) -> None:
    response = worker_client.post(
        "/api/v1/workers/missing-worker/heartbeat",
        json={
            "health": "degraded",
            "load": 0.9,
            "queue_depth": 3,
            "accepting_work": False,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Worker not found"
