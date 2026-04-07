from __future__ import annotations

from datetime import datetime, timedelta

from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.models import (
    JobStatus,
    WorkerClaimRead,
    WorkerClaimRequest,
    WorkerLeaseRead,
    WorkerMode,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerQueueName,
    WorkerRunReportRequest,
    WorkerRegistrationRead,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


class WorkerClaimError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class WorkerReportError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class WorkerSchedulerService:
    """Minimal queue + lease scheduler for worker claim flows."""

    def __init__(
        self,
        *,
        worker_registry: WorkerRegistryService,
        queue_repository: Repository[WorkerQueueItemRead],
        lease_repository: Repository[WorkerLeaseRead],
        lease_ttl_seconds: int = 60,
    ) -> None:
        self._worker_registry = worker_registry
        self._queue_repository = queue_repository
        self._lease_repository = lease_repository
        self._lease_ttl_seconds = max(1, lease_ttl_seconds)

    def enqueue(
        self,
        request: WorkerQueueItemCreateRequest,
        *,
        now: datetime | None = None,
    ) -> WorkerQueueItemRead:
        current = now or utc_now()
        item = WorkerQueueItemRead(
            run_id=create_resource_id("run"),
            queue_name=request.queue_name,
            task_name=request.task_name,
            task_type=request.task_type,
            payload=dict(request.payload),
            requested_by=request.requested_by,
            status=JobStatus.QUEUED,
            assigned_worker_id=None,
            message=None,
            progress=None,
            metrics={},
            result=None,
            error=None,
            started_at=None,
            completed_at=None,
            created_at=current,
            updated_at=current,
            metadata=dict(request.metadata),
        )
        return self._queue_repository.save(item.run_id, item)

    def claim(
        self,
        worker_id: str,
        request: WorkerClaimRequest,
        *,
        now: datetime | None = None,
    ) -> WorkerClaimRead:
        current = now or utc_now()
        worker = self._require_claimable_worker(worker_id=worker_id, now=current)
        active_leases = self._active_leases(now=current)

        # Idempotent polling: if the worker already holds an active lease, return it.
        for lease in active_leases.values():
            if lease.worker_id != worker_id or lease.queue_name != request.queue_name:
                continue
            run = self._queue_repository.get(lease.run_id)
            if run is None:
                continue
            return WorkerClaimRead(
                claimed=True,
                queue_name=request.queue_name,
                worker_id=worker_id,
                run=run,
                lease=lease,
                reason="already_claimed",
                created_at=current,
            )

        queued = self._queued_runs(queue_name=request.queue_name)
        # First pass: try to claim a run that matches this worker's sticky preference
        for run in queued:
            if run.run_id in active_leases:
                continue
            preferred_wid = run.metadata.get("preferred_worker_id") if run.metadata else None
            if preferred_wid and preferred_wid == worker_id:
                return self._finalize_claim(run, worker, request.queue_name, current)

        # Second pass: claim any non-sticky run, or sticky runs whose preferred
        # worker has not claimed them (fallback after waiting).
        for run in queued:
            if run.run_id in active_leases:
                continue
            preferred_wid = run.metadata.get("preferred_worker_id") if run.metadata else None
            if preferred_wid and preferred_wid != worker_id:
                # Check if the preferred worker is still active; if stale, allow fallback
                preferred_worker = self._worker_registry.get_worker(preferred_wid, as_of=current)
                if preferred_worker and not preferred_worker.is_stale and preferred_worker.accepting_work:
                    continue  # Preferred worker is still healthy, let it claim
            return self._finalize_claim(run, worker, request.queue_name, current)

        return WorkerClaimRead(
            claimed=False,
            queue_name=request.queue_name,
            worker_id=worker_id,
            reason="no_work_available",
            created_at=current,
        )

    def _finalize_claim(
        self,
        run: WorkerQueueItemRead,
        worker: WorkerRegistrationRead,
        queue_name: WorkerQueueName,
        current: datetime,
    ) -> WorkerClaimRead:
        claimed_run = run.model_copy(
            update={
                "assigned_worker_id": worker.worker_id,
                "updated_at": current,
            }
        )
        lease = WorkerLeaseRead(
            lease_id=self._lease_id_for_run(run.run_id),
            run_id=run.run_id,
            worker_id=worker.worker_id,
            queue_name=queue_name,
            lease_expires_at=current + timedelta(seconds=self._lease_ttl_seconds),
            active=True,
            created_at=current,
            updated_at=current,
            metadata={},
        )
        self._queue_repository.save(claimed_run.run_id, claimed_run)
        self._lease_repository.save(lease.lease_id, lease)
        is_sticky = bool(run.metadata and run.metadata.get("preferred_worker_id"))
        return WorkerClaimRead(
            claimed=True,
            queue_name=queue_name,
            worker_id=worker.worker_id,
            run=claimed_run,
            lease=lease,
            reason="sticky_match" if is_sticky else "claimed",
            created_at=current,
        )

    def report(
        self,
        worker_id: str,
        run_id: str,
        request: WorkerRunReportRequest,
        *,
        now: datetime | None = None,
    ) -> WorkerQueueItemRead:
        current = now or utc_now()
        run = self._queue_repository.get(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.INTERRUPTED}:
            raise WorkerReportError("Run is already in a terminal state")

        active_leases = self._active_leases(now=current)
        lease = active_leases.get(run_id)
        if lease is not None and lease.worker_id != worker_id:
            raise WorkerReportError("Run is leased to another worker")
        if lease is None and run.assigned_worker_id != worker_id:
            raise WorkerReportError("Run is not assigned to this worker")

        update_fields: dict[str, object] = {
            "status": request.status,
            "updated_at": current,
            "message": request.message if request.message is not None else run.message,
            "progress": request.progress if request.progress is not None else run.progress,
            "metrics": {
                **run.metrics,
                **request.metrics,
            },
            "result": request.result if request.result is not None else run.result,
            "error": request.error if request.error is not None else run.error,
        }

        if request.status == JobStatus.RUNNING:
            update_fields["started_at"] = run.started_at or current
            if lease is not None:
                lease = lease.model_copy(
                    update={
                        "lease_expires_at": current + timedelta(seconds=self._lease_ttl_seconds),
                        "updated_at": current,
                    }
                )
                self._lease_repository.save(lease.lease_id, lease)
        else:
            update_fields["started_at"] = run.started_at or current
            update_fields["completed_at"] = current
            if request.status == JobStatus.COMPLETED:
                update_fields["error"] = None
            if lease is not None:
                finished_lease = lease.model_copy(update={"active": False, "updated_at": current})
                self._lease_repository.save(finished_lease.lease_id, finished_lease)

        updated = run.model_copy(update=update_fields)
        return self._queue_repository.save(run_id, updated)

    def get_run(self, run_id: str) -> WorkerQueueItemRead | None:
        return self._queue_repository.get(run_id)

    def list_queue(self, *, queue_name: WorkerQueueName | None = None) -> list[WorkerQueueItemRead]:
        items = self._queue_repository.list()
        if queue_name is not None:
            items = [item for item in items if item.queue_name == queue_name]
        return sorted(items, key=lambda item: (item.created_at, item.run_id))

    def list_leases(self) -> list[WorkerLeaseRead]:
        return sorted(self._lease_repository.list(), key=lambda lease: (lease.created_at, lease.lease_id))

    def _require_claimable_worker(self, *, worker_id: str, now: datetime) -> WorkerRegistrationRead:
        worker = self._worker_registry.get_worker(worker_id, as_of=now)
        if worker is None:
            raise KeyError(worker_id)
        if worker.is_stale:
            raise WorkerClaimError("Worker is stale and cannot claim work")
        if not worker.accepting_work:
            raise WorkerClaimError("Worker is not accepting work")
        if worker.mode in {WorkerMode.DRAINING, WorkerMode.OFFLINE}:
            raise WorkerClaimError("Worker mode does not allow claiming work")
        return worker

    def _active_leases(self, *, now: datetime) -> dict[str, WorkerLeaseRead]:
        active: dict[str, WorkerLeaseRead] = {}
        for lease in self._lease_repository.list():
            if lease.active and lease.lease_expires_at > now:
                active[lease.run_id] = lease
                continue
            if lease.active:
                expired = lease.model_copy(update={"active": False, "updated_at": now})
                self._lease_repository.save(expired.lease_id, expired)
        return active

    def _queued_runs(self, *, queue_name: WorkerQueueName) -> list[WorkerQueueItemRead]:
        items = [
            item
            for item in self._queue_repository.list()
            if item.queue_name == queue_name and item.status == JobStatus.QUEUED
        ]
        return sorted(items, key=lambda item: (item.created_at, item.run_id))

    @staticmethod
    def _lease_id_for_run(run_id: str) -> str:
        return f"wlease_{run_id}"
