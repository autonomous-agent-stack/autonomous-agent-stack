from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

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

logger = logging.getLogger(__name__)


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
        retry_backoff_seconds: int = 30,
    ) -> None:
        self._worker_registry = worker_registry
        self._queue_repository = queue_repository
        self._lease_repository = lease_repository
        self._lease_ttl_seconds = max(1, lease_ttl_seconds)
        self._retry_backoff_seconds = max(1, retry_backoff_seconds)

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
            priority=request.priority,
            retry_count=0,
            max_retries=request.max_retries,
            next_attempt_at=None,
            recovery_reason=None,
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

        queued = self._queued_runs(queue_name=request.queue_name, now=current)
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
                if (
                    preferred_worker
                    and not preferred_worker.is_stale
                    and preferred_worker.accepting_work
                    and not self._sticky_preference_expired(run, now=current)
                ):
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
            lease_expires_at=current + timedelta(seconds=self._lease_ttl_for_run(run)),
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
        if run.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.INTERRUPTED, JobStatus.CANCELLED}:
            raise WorkerReportError("Run is already in a terminal state")

        active_leases = self._active_leases(now=current)
        lease = active_leases.get(run_id)
        if lease is not None and lease.worker_id != worker_id:
            raise WorkerReportError("Run is leased to another worker")
        if lease is None and run.status == JobStatus.RUNNING:
            raise WorkerReportError("Run lease expired and must be reclaimed before reporting")
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
            "metadata": {
                **run.metadata,
                **request.metadata,
                "worker_id": worker_id,
                "run_id": run_id,
                "task_type": run.task_type.value,
                "status": request.status.value,
                "summary": request.message if request.message is not None else run.message,
            },
            "recovery_reason": run.recovery_reason,
        }

        if request.status == JobStatus.RUNNING:
            update_fields["started_at"] = run.started_at or current
            if lease is not None:
                lease = lease.model_copy(
                    update={
                        "lease_expires_at": current + timedelta(seconds=self._lease_ttl_for_run(run)),
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

    def requeue_run(
        self,
        run_id: str,
        *,
        reason: str,
        now: datetime | None = None,
        backoff_seconds: int | None = None,
    ) -> WorkerQueueItemRead:
        current = now or utc_now()
        run = self._queue_repository.get(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.status in {JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.INTERRUPTED}:
            raise WorkerReportError("Terminal run cannot be requeued")
        next_retry = current + timedelta(seconds=max(1, backoff_seconds or self._retry_backoff_seconds))
        updated = run.model_copy(
            update={
                "status": JobStatus.QUEUED,
                "assigned_worker_id": None,
                "retry_count": run.retry_count + 1,
                "next_attempt_at": next_retry,
                "recovery_reason": reason,
                "updated_at": current,
                "completed_at": None,
            }
        )
        lease = self._lease_repository.get(self._lease_id_for_run(run_id))
        if lease is not None and lease.active:
            self._lease_repository.save(
                lease.lease_id,
                lease.model_copy(update={"active": False, "updated_at": current}),
            )
        return self._queue_repository.save(run_id, updated)

    def force_fail_run(
        self,
        run_id: str,
        *,
        reason: str,
        now: datetime | None = None,
    ) -> WorkerQueueItemRead:
        current = now or utc_now()
        run = self._queue_repository.get(run_id)
        if run is None:
            raise KeyError(run_id)
        if run.status in {JobStatus.COMPLETED, JobStatus.CANCELLED, JobStatus.INTERRUPTED, JobStatus.FAILED}:
            raise WorkerReportError("Terminal run cannot be force-failed")
        updated = run.model_copy(
            update={
                "status": JobStatus.FAILED,
                "error": reason,
                "recovery_reason": reason,
                "completed_at": current,
                "updated_at": current,
            }
        )
        lease = self._lease_repository.get(self._lease_id_for_run(run_id))
        if lease is not None and lease.active:
            self._lease_repository.save(
                lease.lease_id,
                lease.model_copy(update={"active": False, "updated_at": current}),
            )
        return self._queue_repository.save(run_id, updated)

    def recover_stale_runs(self, *, now: datetime | None = None) -> list[WorkerQueueItemRead]:
        current = now or utc_now()
        recovered: list[WorkerQueueItemRead] = []
        for run in self._queue_repository.list():
            if run.status != JobStatus.RUNNING:
                continue
            lease = self._lease_repository.get(self._lease_id_for_run(run.run_id))
            if lease is None:
                logger.warning(
                    "recover_stale_runs observed RUNNING run without lease record run_id=%s",
                    run.run_id,
                )
            if lease is not None and lease.active and lease.lease_expires_at > current:
                continue
            if run.retry_count >= run.max_retries:
                recovered.append(self.force_fail_run(run.run_id, reason="retry_budget_exhausted", now=current))
                continue
            recovered.append(
                self.requeue_run(
                    run.run_id,
                    reason="lease_expired_or_worker_stale",
                    now=current,
                )
            )
        return recovered

    def get_run(self, run_id: str) -> WorkerQueueItemRead | None:
        return self._queue_repository.get(run_id)

    def merge_queue_metadata(
        self,
        run_id: str,
        patch: dict[str, Any],
        *,
        now: datetime | None = None,
    ) -> WorkerQueueItemRead | None:
        """Merge keys into queue item metadata (e.g. Telegram message_id for edit-in-place)."""
        current = now or utc_now()
        run = self._queue_repository.get(run_id)
        if run is None:
            return None
        merged = {**(run.metadata or {}), **dict(patch)}
        updated = run.model_copy(update={"metadata": merged, "updated_at": current})
        return self._queue_repository.save(run_id, updated)

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

    def _queued_runs(self, *, queue_name: WorkerQueueName, now: datetime) -> list[WorkerQueueItemRead]:
        items = [
            item
            for item in self._queue_repository.list()
            if item.queue_name == queue_name
            and item.status == JobStatus.QUEUED
            and (item.next_attempt_at is None or item.next_attempt_at <= now)
        ]
        return sorted(items, key=lambda item: (-item.priority, item.created_at, item.run_id))

    def _lease_ttl_for_run(self, run: WorkerQueueItemRead) -> int:
        raw = (run.metadata or {}).get("interactive_lease_ttl_seconds")
        if raw is None:
            raw = (run.payload or {}).get("interactive_lease_ttl_seconds")
        try:
            ttl = int(raw) if raw is not None else self._lease_ttl_seconds
        except (TypeError, ValueError):
            ttl = self._lease_ttl_seconds
        return max(self._lease_ttl_seconds, min(ttl, 24 * 60 * 60))

    @staticmethod
    def _sticky_preference_expired(run: WorkerQueueItemRead, *, now: datetime) -> bool:
        raw = (run.metadata or {}).get("sticky_deadline_at")
        if raw is None:
            raw = (run.payload or {}).get("sticky_deadline_at")
        if raw is None:
            return False
        if isinstance(raw, datetime):
            deadline = raw
        else:
            try:
                deadline = datetime.fromisoformat(str(raw))
            except ValueError:
                return False
        if deadline.tzinfo is None and now.tzinfo is not None:
            deadline = deadline.replace(tzinfo=now.tzinfo)
        return deadline <= now

    @staticmethod
    def _lease_id_for_run(run_id: str) -> str:
        return f"wlease_{run_id}"
