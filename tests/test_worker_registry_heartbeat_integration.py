"""Integration tests: WorkerRegistryService emits unified WorkerHeartbeat data.

These tests exercise the real disk-backed Linux supervisor state files under
``.masfactory_runtime/linux-housekeeper/state`` and assert that
``WorkerRegistryService`` exposes a unified ``WorkerHeartbeat``-compatible
shape for the real Linux worker.

They are expected to FAIL until ``supervisor_heartbeat_to_worker_heartbeat()``
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
from autoresearch.shared.worker_contract import WorkerHeartbeat, WorkerStatus


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
) -> None:
    process_hb = LinuxSupervisorProcessHeartbeatRead(
        observed_at=observed_at,
        pid=4242 if heartbeat_status != "stopped" else None,
        current_task_id=current_task_id,
        queue_depth=queue_depth,
        status=heartbeat_status,
    )
    process_state = LinuxSupervisorProcessStatusRead(
        status=process_status,
        pid=4242 if process_status != "stopped" else None,
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


class TestWorkerRegistryHeartbeatIntegration:
    def test_fresh_idle_heartbeat_is_unified_online(self, tmp_path: Path) -> None:
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

        assert isinstance(heartbeat, WorkerHeartbeat)
        assert heartbeat.worker_id == "linux_housekeeper"
        assert heartbeat.status is WorkerStatus.ONLINE
        assert heartbeat.metrics.active_tasks == 0
        assert heartbeat.active_task_ids == []
        assert heartbeat.metadata["queue_depth"] == 2
        assert heartbeat.metadata["process_status"] == "idle"

    def test_running_heartbeat_is_unified_busy_with_active_task(self, tmp_path: Path) -> None:
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

        assert heartbeat.status is WorkerStatus.BUSY
        assert heartbeat.metrics.active_tasks == 1
        assert heartbeat.active_task_ids == ["task-001"]

    def test_stale_heartbeat_is_unified_offline(self, tmp_path: Path) -> None:
        repo_root = tmp_path / "repo"
        runtime_root = repo_root / ".masfactory_runtime" / "linux-housekeeper"
        observed_at = datetime.now(timezone.utc) - timedelta(seconds=130)
        _seed_supervisor_state(
            runtime_root,
            observed_at=observed_at,
            heartbeat_status="idle",
            process_status="idle",
        )
        registry = WorkerRegistryService(repo_root=repo_root, linux_runtime_root=runtime_root)

        heartbeat = registry.get_worker_heartbeat("linux_housekeeper")

        assert heartbeat.status is WorkerStatus.OFFLINE

    def test_stopped_heartbeat_surfaces_unified_errors(self, tmp_path: Path) -> None:
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

        assert heartbeat.status is WorkerStatus.OFFLINE
        assert heartbeat.errors == ["worker crashed"]

    def test_unified_heartbeat_uses_expected_top_level_shape(self, tmp_path: Path) -> None:
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

        payload = registry.get_worker_heartbeat("linux_housekeeper").model_dump(mode="json")

        assert set(payload) == {
            "worker_id",
            "status",
            "metrics",
            "active_task_ids",
            "errors",
            "metadata",
        }
