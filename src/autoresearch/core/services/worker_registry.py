from __future__ import annotations

from datetime import datetime

from autoresearch.shared.models import (
    WorkerHealth,
    WorkerHeartbeatRequest,
    WorkerMode,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    utc_now,
)
from autoresearch.shared.store import Repository


class WorkerRegistryService:
    """Minimal worker registry for register + heartbeat on the Python control plane."""

    def __init__(
        self,
        *,
        repository: Repository[WorkerRegistrationRead],
        stale_after_seconds: int = 45,
    ) -> None:
        self._repository = repository
        self._stale_after_seconds = max(1, stale_after_seconds)

    def register(
        self,
        request: WorkerRegisterRequest,
        *,
        now: datetime | None = None,
    ) -> WorkerRegistrationRead:
        current = now or utc_now()
        existing = self._repository.get(request.worker_id)
        registered_at = existing.registered_at if existing is not None else current

        worker = WorkerRegistrationRead(
            worker_id=request.worker_id,
            worker_type=request.worker_type,
            name=request.name,
            host=request.host,
            mode=request.mode,
            role=request.role,
            capabilities=self._normalize_capabilities(request.capabilities),
            metadata=dict(request.metadata),
            health=WorkerHealth.OK,
            load=existing.load if existing is not None else None,
            queue_depth=existing.queue_depth if existing is not None else 0,
            disk_free_gb=existing.disk_free_gb if existing is not None else None,
            accepting_work=existing.accepting_work if existing is not None else request.mode != WorkerMode.OFFLINE,
            is_stale=False,
            registered_at=registered_at,
            last_heartbeat_at=current,
            updated_at=current,
        )
        return self._repository.save(request.worker_id, worker)

    def heartbeat(
        self,
        worker_id: str,
        request: WorkerHeartbeatRequest,
        *,
        now: datetime | None = None,
    ) -> WorkerRegistrationRead:
        existing = self._repository.get(worker_id)
        if existing is None:
            raise KeyError(worker_id)

        current = now or utc_now()
        worker = existing.model_copy(
            update={
                "health": request.health,
                "load": request.load,
                "queue_depth": request.queue_depth,
                "disk_free_gb": request.disk_free_gb,
                "accepting_work": request.accepting_work,
                "metadata": {
                    **existing.metadata,
                    **request.metadata,
                },
                "is_stale": False,
                "last_heartbeat_at": current,
                "updated_at": current,
            }
        )
        return self._repository.save(worker_id, worker)

    def get_worker(
        self,
        worker_id: str,
        *,
        as_of: datetime | None = None,
        stale_after_seconds: int | None = None,
    ) -> WorkerRegistrationRead | None:
        worker = self._repository.get(worker_id)
        if worker is None:
            return None
        return self._annotate(worker, as_of=as_of, stale_after_seconds=stale_after_seconds)

    def list_workers(
        self,
        *,
        as_of: datetime | None = None,
        stale_after_seconds: int | None = None,
    ) -> list[WorkerRegistrationRead]:
        return [
            self._annotate(worker, as_of=as_of, stale_after_seconds=stale_after_seconds)
            for worker in self._repository.list()
        ]

    def _annotate(
        self,
        worker: WorkerRegistrationRead,
        *,
        as_of: datetime | None,
        stale_after_seconds: int | None,
    ) -> WorkerRegistrationRead:
        current = as_of or utc_now()
        threshold = max(1, stale_after_seconds or self._stale_after_seconds)
        is_stale = (current - worker.last_heartbeat_at).total_seconds() > threshold
        if worker.is_stale == is_stale:
            return worker
        return worker.model_copy(update={"is_stale": is_stale})

    @staticmethod
    def _normalize_capabilities(values: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = str(raw).strip()
            if not value or value in seen:
                continue
            normalized.append(value)
            seen.add(value)
        return normalized
