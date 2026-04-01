"""Integration tests: WorkerRegistryService emits unified WorkerRegistration data.

These tests exercise the real disk-backed Linux supervisor state files under
``.masfactory_runtime/linux-housekeeper/state`` and assert that
``WorkerRegistryService`` exposes a unified ``WorkerRegistration``-compatible
shape for the real Linux worker while remaining consistent with
``get_worker_heartbeat()`` and ``list_workers()``.

They are expected to FAIL until ``supervisor_heartbeat_to_worker_registration()``
is wired into the production registry path.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.linux_supervisor_contract import (
    LinuxSupervisorProcessHeartbeatRead,
    LinuxSupervisorProcessStatusRead,
)
from autoresearch.shared.worker_contract import (
    AllowedAction,
    WorkerRegistration,
    WorkerStatus,
    WorkerType,
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


def _linux_worker_from_list(registry: WorkerRegistryService):
    for worker in registry.list_workers():
        if worker.worker_id == "linux_housekeeper":
            return worker
    raise AssertionError("linux_housekeeper not found in list_workers()")


class TestWorkerRegistryRegistrationIntegration:
    def test_fresh_idle_registration_reflects_real_status(self, tmp_path: Path) -> None:
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

        registration = registry.get_worker_registration("linux_housekeeper")

        assert isinstance(registration, WorkerRegistration)
        assert registration.worker_id == "linux_housekeeper"
        assert registration.worker_type is WorkerType.LINUX
        assert registration.status is WorkerStatus.ONLINE
        assert registration.last_heartbeat == observed_at

    def test_running_registration_reflects_real_status_and_queue_pid_metadata(
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
            pid=4242,
        )
        registry = WorkerRegistryService(repo_root=repo_root, linux_runtime_root=runtime_root)

        registration = registry.get_worker_registration("linux_housekeeper")

        assert registration.status is WorkerStatus.BUSY
        assert registration.metadata["queue_depth"] == 1
        assert registration.metadata["process_status"] == "running"
        assert registration.metadata["pid"] == 4242
        assert registration.metadata["current_task_id"] == "task-001"

    def test_stopped_registration_reflects_real_status(self, tmp_path: Path) -> None:
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

        registration = registry.get_worker_registration("linux_housekeeper")

        assert registration.status is WorkerStatus.OFFLINE
        assert registration.metadata["process_status"] == "stopped"

    def test_registration_status_matches_heartbeat_and_list_workers(self, tmp_path: Path) -> None:
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

        registration = registry.get_worker_registration("linux_housekeeper")
        heartbeat = registry.get_worker_heartbeat("linux_housekeeper")
        worker = _linux_worker_from_list(registry)

        assert registration.status.value == heartbeat.status.value
        assert registration.status.value == worker.status.value

    def test_registration_shape_includes_unified_compat_fields(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        runtime_root = repo_root / ".masfactory_runtime" / "linux-housekeeper"
        observed_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        _seed_supervisor_state(
            runtime_root,
            observed_at=observed_at,
            heartbeat_status="idle",
            process_status="idle",
        )
        registry = WorkerRegistryService(repo_root=repo_root, linux_runtime_root=runtime_root)

        registration = registry.get_worker_registration("linux_housekeeper")

        assert registration.backend_kind == "linux_supervisor"
        assert "shell" in registration.capabilities
        assert "script_runner" in registration.capabilities
        assert "log_collection" in registration.capabilities
        assert AllowedAction.EXECUTE_TASK in registration.allowed_actions
        assert AllowedAction.RUN_SCRIPT in registration.allowed_actions
        assert AllowedAction.COLLECT_LOGS in registration.allowed_actions
        assert registration.max_concurrent_tasks == 1
        assert registration.registered_at is not None
