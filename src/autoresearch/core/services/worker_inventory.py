from __future__ import annotations

from datetime import datetime

from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    JobStatus,
    WorkerDispatchRulesRead,
    WorkerHealth,
    WorkerInventoryListRead,
    WorkerInventoryRead,
    WorkerInventorySummaryRead,
    WorkerLatestTaskSummaryRead,
    WorkerLocationRead,
    WorkerMode,
    utc_now,
)


class WorkerInventoryService:
    """Read-only worker inventory aggregated from registry and scheduler state."""

    def __init__(
        self,
        *,
        worker_registry: WorkerRegistryService,
        worker_scheduler: WorkerSchedulerService,
    ) -> None:
        self._worker_registry = worker_registry
        self._worker_scheduler = worker_scheduler

    def list_workers(
        self,
        *,
        as_of: datetime | None = None,
    ) -> WorkerInventoryListRead:
        current = as_of or utc_now()
        workers = [
            self._build_inventory_item(worker, as_of=current)
            for worker in self._worker_registry.list_workers(as_of=current)
        ]
        workers.sort(key=lambda item: (item.display_status, item.worker_id))
        return WorkerInventoryListRead(
            summary=self._build_summary(workers, issued_at=current),
            workers=workers,
        )

    def get_worker(
        self,
        worker_id: str,
        *,
        as_of: datetime | None = None,
    ) -> WorkerInventoryRead | None:
        current = as_of or utc_now()
        worker = self._worker_registry.get_worker(worker_id, as_of=current)
        if worker is None:
            return None
        return self._build_inventory_item(worker, as_of=current)

    def summary(
        self,
        *,
        as_of: datetime | None = None,
    ) -> WorkerInventorySummaryRead:
        current = as_of or utc_now()
        workers = [
            self._build_inventory_item(worker, as_of=current)
            for worker in self._worker_registry.list_workers(as_of=current)
        ]
        return self._build_summary(workers, issued_at=current)

    def _build_inventory_item(self, worker, *, as_of: datetime) -> WorkerInventoryRead:
        runs = [item for item in self._worker_scheduler.list_queue() if item.assigned_worker_id == worker.worker_id]
        active_tasks = sum(1 for item in runs if item.status in {JobStatus.QUEUED, JobStatus.RUNNING})
        latest_run = max(runs, key=lambda item: (item.updated_at, item.run_id), default=None)
        queued_task_types = sorted({item.task_type.value for item in runs if item.status in {JobStatus.QUEUED, JobStatus.RUNNING}})
        queue_names = sorted({item.queue_name.value for item in runs if item.status in {JobStatus.QUEUED, JobStatus.RUNNING}})
        preferred_run_ids = sorted(
            item.run_id
            for item in runs
            if str(item.metadata.get("preferred_worker_id") or "") == worker.worker_id
        )

        location = WorkerLocationRead(
            host=worker.host or self._metadata_string(worker.metadata, "runtime_host"),
            runtime=self._metadata_string(worker.metadata, "runtime_family")
            or self._metadata_string(worker.metadata, "runtime_platform")
            or self._metadata_string(worker.metadata, "runtime_display"),
            work_dir=self._metadata_string(worker.metadata, "work_dir"),
        )
        dispatch_rules = WorkerDispatchRulesRead(
            accepting_work=worker.accepting_work,
            mode=worker.mode,
            queue_names=queue_names,
            task_types=queued_task_types,
            preferred_run_ids=preferred_run_ids,
            capability_tags=list(worker.capabilities),
        )
        latest_task_summary = self._build_latest_task_summary(latest_run)

        return WorkerInventoryRead(
            **worker.model_dump(mode="python"),
            active_tasks=active_tasks,
            latest_task_summary=latest_task_summary,
            location=location,
            dispatch_rules=dispatch_rules,
            display_status=self._display_status(worker=worker, active_tasks=active_tasks, as_of=as_of),
        )

    @staticmethod
    def _build_latest_task_summary(run) -> WorkerLatestTaskSummaryRead | None:
        if run is None:
            return None
        return WorkerLatestTaskSummaryRead(
            run_id=run.run_id,
            task_name=run.task_name,
            task_type=run.task_type,
            status=run.status,
            message=run.message,
            updated_at=run.updated_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
            result=run.result,
            error=run.error,
            metrics=dict(run.metrics),
            metadata=dict(run.metadata),
        )

    @staticmethod
    def _metadata_string(metadata: dict[str, object], key: str) -> str | None:
        value = metadata.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _display_status(*, worker, active_tasks: int, as_of: datetime) -> str:
        if worker.mode == WorkerMode.OFFLINE or worker.is_stale:
            return "offline"
        if worker.health in {WorkerHealth.DEGRADED, WorkerHealth.ERROR}:
            return "degraded"
        if not worker.accepting_work or worker.mode == WorkerMode.DRAINING:
            return "degraded"
        if active_tasks > 0 or worker.queue_depth > 0:
            return "busy"
        return "online"

    @staticmethod
    def _build_summary(workers: list[WorkerInventoryRead], *, issued_at: datetime) -> WorkerInventorySummaryRead:
        return WorkerInventorySummaryRead(
            total_workers=len(workers),
            online_workers=sum(1 for item in workers if item.display_status == "online"),
            busy_workers=sum(1 for item in workers if item.display_status == "busy"),
            degraded_workers=sum(1 for item in workers if item.display_status == "degraded"),
            offline_workers=sum(1 for item in workers if item.display_status == "offline"),
            issued_at=issued_at,
        )
