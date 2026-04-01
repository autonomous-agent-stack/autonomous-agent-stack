from __future__ import annotations

import json
from pathlib import Path

from autoresearch.shared.housekeeper_contract import (
    AgentPackageRecordRead,
    HousekeeperBackendKind,
    WorkerAvailabilityStatus,
    WorkerRegistrationRead,
)
from autoresearch.shared.linux_supervisor_bridge import (
    supervisor_heartbeat_to_worker_heartbeat,
    supervisor_heartbeat_to_worker_registration,
)
from autoresearch.shared.linux_supervisor_contract import (
    LinuxSupervisorProcessHeartbeatRead,
    LinuxSupervisorProcessStatusRead,
)
from autoresearch.shared.models import utc_now
from autoresearch.shared.worker_contract import (
    WorkerHeartbeat,
    WorkerRegistration,
    WorkerStatus,
    worker_status_rank,
)


class WorkerRegistryService:
    """Expose a small runtime view over available execution workers."""

    def __init__(self, *, repo_root: Path, linux_runtime_root: Path | None = None) -> None:
        self._repo_root = repo_root.resolve()
        self._linux_runtime_root = (
            linux_runtime_root or self._repo_root / ".masfactory_runtime" / "linux-housekeeper"
        ).resolve()

    def list_workers(self) -> list[WorkerRegistrationRead]:
        return [
            self._openclaw_frontdesk_worker(),
            self._openclaw_runtime_worker(),
            self._linux_housekeeper_worker(),
            self._win_yingdao_worker(),
        ]

    def get_worker(self, worker_id: str) -> WorkerRegistrationRead | None:
        normalized = worker_id.strip()
        if not normalized:
            return None
        for worker in self.list_workers():
            if worker.worker_id == normalized:
                return worker
        return None

    def get_worker_heartbeat(self, worker_id: str) -> WorkerHeartbeat | None:
        normalized = worker_id.strip()
        if normalized != "linux_housekeeper":
            return None
        process_status, heartbeat = self._read_linux_supervisor_state()
        if process_status is None or heartbeat is None:
            return None
        return supervisor_heartbeat_to_worker_heartbeat(
            heartbeat,
            process_status,
            worker_id="linux_housekeeper",
            now=utc_now(),
        )

    def get_worker_registration(self, worker_id: str) -> WorkerRegistration | None:
        normalized = worker_id.strip()
        if normalized != "linux_housekeeper":
            return None
        process_status, heartbeat = self._read_linux_supervisor_state()
        if process_status is None or heartbeat is None:
            return None
        errors = []
        if process_status.message and process_status.status == "stopped":
            errors.append(process_status.message)
        return supervisor_heartbeat_to_worker_registration(
            heartbeat,
            process_status,
            worker_id="linux_housekeeper",
        ).model_copy(
            update={
                "errors": errors,
                "metadata": self._linux_supervisor_metadata(
                    process_status=process_status,
                    process_heartbeat=heartbeat,
                ),
            }
        )

    def find_worker_for_backend(
        self, backend_kind: HousekeeperBackendKind
    ) -> WorkerRegistrationRead | None:
        candidates = [
            worker for worker in self.list_workers() if worker.backend_kind is backend_kind
        ]
        candidates.sort(key=lambda item: self._status_rank(item.status))
        return candidates[0] if candidates else None

    def find_worker_for_package(
        self, package: AgentPackageRecordRead
    ) -> WorkerRegistrationRead | None:
        if package.execution_backend is HousekeeperBackendKind.LINUX_SUPERVISOR:
            return self.find_worker_for_backend(HousekeeperBackendKind.LINUX_SUPERVISOR)
        if package.execution_backend is HousekeeperBackendKind.WIN_YINGDAO:
            return self.find_worker_for_backend(HousekeeperBackendKind.WIN_YINGDAO)
        if package.execution_backend is HousekeeperBackendKind.OPENCLAW_RUNTIME:
            return self.find_worker_for_backend(HousekeeperBackendKind.OPENCLAW_RUNTIME)

        candidates = [
            worker
            for worker in self.list_workers()
            if worker.worker_type in set(package.supported_worker_types)
        ]
        candidates.sort(key=self._package_worker_rank)
        return candidates[0] if candidates else None

    def _status_rank(self, status: WorkerAvailabilityStatus) -> int:
        unified = WorkerStatus(status.value)
        return worker_status_rank(unified)

    def _package_worker_rank(self, worker: WorkerRegistrationRead) -> tuple[int, int]:
        preferred_ids = {
            "openclaw_runtime": 0,
            "linux_housekeeper": 1,
            "openclaw_frontdesk": 2,
            "win_yingdao": 3,
        }
        return (self._status_rank(worker.status), preferred_ids.get(worker.worker_id, 99))

    def _openclaw_frontdesk_worker(self) -> WorkerRegistrationRead:
        now = utc_now()
        return WorkerRegistrationRead(
            worker_id="openclaw_frontdesk",
            name="OpenClaw Frontdesk",
            worker_type="openclaw",
            backend_kind=None,
            status=WorkerAvailabilityStatus.ONLINE,
            capabilities=["conversation", "session_memory", "skill_lookup", "task_translation"],
            last_heartbeat=now,
            metadata={"source": "static"},
        )

    def _linux_housekeeper_worker(self) -> WorkerRegistrationRead:
        registration = self.get_worker_registration("linux_housekeeper")
        if registration is not None:
            metadata = dict(registration.metadata)
            metadata["allowed_actions"] = [action.value for action in registration.allowed_actions]
            metadata["max_concurrent_tasks"] = registration.max_concurrent_tasks
            metadata["registered_at"] = registration.registered_at
            if registration.errors:
                metadata["errors"] = list(registration.errors)
            return WorkerRegistrationRead(
                worker_id=registration.worker_id,
                name=registration.name,
                worker_type=registration.worker_type.value,
                backend_kind=(
                    HousekeeperBackendKind(registration.backend_kind)
                    if registration.backend_kind
                    else None
                ),
                status=WorkerAvailabilityStatus(registration.status.value),
                capabilities=list(registration.capabilities),
                last_heartbeat=registration.last_heartbeat,
                metadata=metadata,
            )

        metadata: dict[str, object] = {"source": "linux_supervisor"}
        return WorkerRegistrationRead(
            worker_id="linux_housekeeper",
            name="Linux Housekeeper",
            worker_type="linux",
            backend_kind=HousekeeperBackendKind.LINUX_SUPERVISOR,
            status=WorkerAvailabilityStatus.OFFLINE,
            capabilities=["shell", "script_runner", "log_collection", "ops_inspection"],
            last_heartbeat=None,
            metadata=metadata,
        )

    def _linux_supervisor_metadata(
        self,
        *,
        process_status: LinuxSupervisorProcessStatusRead,
        process_heartbeat: LinuxSupervisorProcessHeartbeatRead,
    ) -> dict[str, object]:
        age_seconds = max(0.0, (utc_now() - process_heartbeat.observed_at).total_seconds())
        return {
            "source": "linux_supervisor",
            "heartbeat_age_seconds": age_seconds,
            "queue_depth": process_heartbeat.queue_depth,
            "process_status": process_status.status,
            "pid": process_status.pid if process_status.pid is not None else process_heartbeat.pid,
            "current_task_id": (
                process_status.current_task_id
                if process_status.current_task_id is not None
                else process_heartbeat.current_task_id
            ),
            "last_task_id": process_status.last_task_id,
            "message": process_status.message,
        }

    def _read_linux_supervisor_state(
        self,
    ) -> tuple[LinuxSupervisorProcessStatusRead | None, LinuxSupervisorProcessHeartbeatRead | None]:
        status_path = self._linux_runtime_root / "state" / "supervisor_status.json"
        heartbeat_path = self._linux_runtime_root / "state" / "supervisor_heartbeat.json"
        process_status = self._read_model(status_path, LinuxSupervisorProcessStatusRead)
        heartbeat = self._read_model(heartbeat_path, LinuxSupervisorProcessHeartbeatRead)
        return process_status, heartbeat

    def _openclaw_runtime_worker(self) -> WorkerRegistrationRead:
        now = utc_now()
        return WorkerRegistrationRead(
            worker_id="openclaw_runtime",
            name="OpenClaw Runtime",
            worker_type="openclaw",
            backend_kind=HousekeeperBackendKind.OPENCLAW_RUNTIME,
            status=WorkerAvailabilityStatus.DEGRADED,
            capabilities=["conversation", "skill_execution", "session_runtime"],
            last_heartbeat=now,
            metadata={"source": "static", "v0_priority": "low"},
        )

    def _win_yingdao_worker(self) -> WorkerRegistrationRead:
        return WorkerRegistrationRead(
            worker_id="win_yingdao",
            name="Win + Yingdao",
            worker_type="win_yingdao",
            backend_kind=HousekeeperBackendKind.WIN_YINGDAO,
            status=WorkerAvailabilityStatus.OFFLINE,
            capabilities=["yingdao_flow", "structured_data_entry", "erp_form_fill"],
            last_heartbeat=None,
            metadata={"source": "static", "implemented": False},
        )

    def _read_model(self, path: Path, model_cls: type):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            return model_cls.model_validate(payload)
        except Exception:
            return None
