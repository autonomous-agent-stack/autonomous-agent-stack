"""Integration tests for legacy control-plane worker API views.

These tests exercise the real ``/api/v1/control-plane/workers`` and
``/api/v1/control-plane/workers/{worker_id}`` endpoints while seeding real
Linux supervisor state files. The API must keep returning the legacy
``WorkerRegistrationRead`` shape, but its Linux payload should remain a
projection of the unified heartbeat / registration sources.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_worker_registry_service
from autoresearch.api.main import app
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.linux_supervisor_contract import (
    LinuxSupervisorProcessHeartbeatRead,
    LinuxSupervisorProcessStatusRead,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _seed_supervisor_state(
    runtime_root: Path,
    *,
    observed_at: datetime,
    heartbeat_status: str,
    process_status: str,
    current_task_id: str | None = None,
    queue_depth: int = 0,
    message: str = "",
    pid: int | None = 4242,
) -> None:
    process_hb = LinuxSupervisorProcessHeartbeatRead(
        observed_at=observed_at,
        pid=pid if heartbeat_status != "stopped" else None,
        current_task_id=current_task_id,
        queue_depth=queue_depth,
        status=heartbeat_status,
    )
    process_state = LinuxSupervisorProcessStatusRead(
        status=process_status,
        pid=pid if process_status != "stopped" else None,
        current_task_id=current_task_id,
        last_task_id=current_task_id,
        queue_depth=queue_depth,
        updated_at=observed_at,
        message=message,
    )
    _write_json(
        runtime_root / "state" / "supervisor_heartbeat.json",
        process_hb.model_dump(mode="json"),
    )
    _write_json(
        runtime_root / "state" / "supervisor_status.json",
        process_state.model_dump(mode="json"),
    )


def _linux_worker_from_list(payload: list[dict[str, object]]) -> dict[str, object]:
    for worker in payload:
        if worker["worker_id"] == "linux_housekeeper":
            return worker
    raise AssertionError("linux_housekeeper not found in /workers payload")


def _client_for_registry(registry: WorkerRegistryService) -> TestClient:
    app.dependency_overrides[get_worker_registry_service] = lambda: registry
    return TestClient(app)


class TestControlPlaneWorkersApiIntegration:
    def test_workers_list_idle_status_matches_unified_heartbeat(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        runtime_root = repo_root / ".masfactory_runtime" / "linux-housekeeper"
        observed_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        _seed_supervisor_state(
            runtime_root,
            observed_at=observed_at,
            heartbeat_status="idle",
            process_status="idle",
            queue_depth=2,
        )
        registry = WorkerRegistryService(repo_root=repo_root, linux_runtime_root=runtime_root)
        heartbeat = registry.get_worker_heartbeat("linux_housekeeper")

        with _client_for_registry(registry) as client:
            response = client.get("/api/v1/control-plane/workers")

        app.dependency_overrides.clear()
        assert response.status_code == 200
        payload = _linux_worker_from_list(response.json())
        assert payload["status"] == heartbeat.status.value

    def test_workers_list_running_status_matches_unified_heartbeat(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        runtime_root = repo_root / ".masfactory_runtime" / "linux-housekeeper"
        observed_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        _seed_supervisor_state(
            runtime_root,
            observed_at=observed_at,
            heartbeat_status="running",
            process_status="running",
            current_task_id="task-001",
            queue_depth=1,
        )
        registry = WorkerRegistryService(repo_root=repo_root, linux_runtime_root=runtime_root)
        heartbeat = registry.get_worker_heartbeat("linux_housekeeper")

        with _client_for_registry(registry) as client:
            response = client.get("/api/v1/control-plane/workers")

        app.dependency_overrides.clear()
        assert response.status_code == 200
        payload = _linux_worker_from_list(response.json())
        assert payload["status"] == heartbeat.status.value

    def test_workers_list_stopped_status_matches_unified_heartbeat(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        runtime_root = repo_root / ".masfactory_runtime" / "linux-housekeeper"
        observed_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        _seed_supervisor_state(
            runtime_root,
            observed_at=observed_at,
            heartbeat_status="stopped",
            process_status="stopped",
            message="worker crashed",
        )
        registry = WorkerRegistryService(repo_root=repo_root, linux_runtime_root=runtime_root)
        heartbeat = registry.get_worker_heartbeat("linux_housekeeper")

        with _client_for_registry(registry) as client:
            response = client.get("/api/v1/control-plane/workers")

        app.dependency_overrides.clear()
        assert response.status_code == 200
        payload = _linux_worker_from_list(response.json())
        assert payload["status"] == heartbeat.status.value

    def test_worker_detail_matches_unified_registration_core_fields(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        runtime_root = repo_root / ".masfactory_runtime" / "linux-housekeeper"
        observed_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        _seed_supervisor_state(
            runtime_root,
            observed_at=observed_at,
            heartbeat_status="running",
            process_status="running",
            current_task_id="task-001",
            queue_depth=1,
            pid=4242,
        )
        registry = WorkerRegistryService(repo_root=repo_root, linux_runtime_root=runtime_root)
        registration = registry.get_worker_registration("linux_housekeeper")

        with _client_for_registry(registry) as client:
            response = client.get("/api/v1/control-plane/workers/linux_housekeeper")

        app.dependency_overrides.clear()
        assert response.status_code == 200
        payload = response.json()
        assert payload["worker_id"] == registration.worker_id
        assert payload["name"] == registration.name
        assert payload["worker_type"] == registration.worker_type.value
        assert payload["backend_kind"] == registration.backend_kind
        assert payload["status"] == registration.status.value
        assert payload["capabilities"] == registration.capabilities
        assert payload["last_heartbeat"] == registration.last_heartbeat.isoformat().replace(
            "+00:00", "Z"
        )

    def test_worker_detail_preserves_legacy_fields_and_unified_metadata(
        self, tmp_path: Path
    ) -> None:
        repo_root = tmp_path / "repo"
        runtime_root = repo_root / ".masfactory_runtime" / "linux-housekeeper"
        observed_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        _seed_supervisor_state(
            runtime_root,
            observed_at=observed_at,
            heartbeat_status="running",
            process_status="running",
            current_task_id="task-001",
            queue_depth=1,
            message="still working",
            pid=4242,
        )
        registry = WorkerRegistryService(repo_root=repo_root, linux_runtime_root=runtime_root)
        registration = registry.get_worker_registration("linux_housekeeper")

        with _client_for_registry(registry) as client:
            response = client.get("/api/v1/control-plane/workers/linux_housekeeper")

        app.dependency_overrides.clear()
        assert response.status_code == 200
        payload = response.json()
        assert set(payload) == {
            "worker_id",
            "name",
            "worker_type",
            "backend_kind",
            "status",
            "capabilities",
            "last_heartbeat",
            "metadata",
        }
        assert payload["metadata"]["queue_depth"] == registration.metadata["queue_depth"]
        assert payload["metadata"]["pid"] == registration.metadata["pid"]
        assert payload["metadata"]["current_task_id"] == registration.metadata["current_task_id"]
        assert payload["metadata"]["message"] == registration.metadata["message"]
        assert payload["metadata"]["allowed_actions"] == [
            action.value for action in registration.allowed_actions
        ]
        assert payload["metadata"]["max_concurrent_tasks"] == registration.max_concurrent_tasks
        assert payload["metadata"]["registered_at"] is not None
