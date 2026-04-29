from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerRunScheduleCreateRequest,
    WorkerRunScheduleRead,
    WorkerRunScheduleResumeRequest,
    WorkerScheduleDispatchRead,
    WorkerScheduleMode,
    WorkerScheduleTickRead,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


logger = logging.getLogger(__name__)


class WorkerScheduleError(RuntimeError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class WorkerScheduleService:
    """Persist and dispatch time-based worker run schedules on a single machine."""

    def __init__(
        self,
        *,
        worker_scheduler: WorkerSchedulerService,
        repository: Repository[WorkerRunScheduleRead],
    ) -> None:
        self._worker_scheduler = worker_scheduler
        self._repository = repository
        self._daemon: WorkerScheduleDaemon | None = None

    def create_schedule(
        self,
        request: WorkerRunScheduleCreateRequest,
        *,
        now: datetime | None = None,
    ) -> WorkerRunScheduleRead:
        current = now or utc_now()
        next_run_at = request.first_run_at or current
        schedule = WorkerRunScheduleRead(
            schedule_id=create_resource_id("wsched"),
            schedule_name=request.schedule_name or request.task_name or request.task_type.value,
            queue_name=request.queue_name,
            task_name=request.task_name or request.task_type.value,
            task_type=request.task_type,
            payload=dict(request.payload),
            requested_by=request.requested_by,
            priority=request.priority,
            max_retries=request.max_retries,
            metadata=dict(request.metadata),
            schedule_mode=request.schedule_mode,
            interval_seconds=request.interval_seconds,
            enabled=request.enabled,
            next_run_at=next_run_at,
            last_triggered_at=None,
            last_enqueued_run_id=None,
            run_count=0,
            last_error=None,
            created_at=current,
            updated_at=current,
        )
        persisted = self._repository.save(schedule.schedule_id, schedule)
        self._sync_daemon_schedule(persisted)
        return persisted

    def get_schedule(self, schedule_id: str) -> WorkerRunScheduleRead | None:
        return self._repository.get(schedule_id)

    def list_schedules(self) -> list[WorkerRunScheduleRead]:
        items = self._repository.list()
        return sorted(
            items,
            key=lambda item: (
                item.next_run_at is None,
                item.next_run_at or item.created_at,
                item.created_at,
                item.schedule_id,
            ),
        )

    def pause_schedule(
        self,
        schedule_id: str,
        *,
        now: datetime | None = None,
    ) -> WorkerRunScheduleRead:
        current = now or utc_now()
        schedule = self._require_schedule(schedule_id)
        updated = schedule.model_copy(
            update={
                "enabled": False,
                "updated_at": current,
            }
        )
        persisted = self._repository.save(updated.schedule_id, updated)
        self._sync_daemon_schedule(persisted)
        return persisted

    def resume_schedule(
        self,
        schedule_id: str,
        request: WorkerRunScheduleResumeRequest | None = None,
        *,
        now: datetime | None = None,
    ) -> WorkerRunScheduleRead:
        current = now or utc_now()
        schedule = self._require_schedule(schedule_id)
        next_run_at = request.next_run_at if request and request.next_run_at is not None else schedule.next_run_at or current
        updated = schedule.model_copy(
            update={
                "enabled": True,
                "next_run_at": next_run_at,
                "updated_at": current,
            }
        )
        persisted = self._repository.save(updated.schedule_id, updated)
        self._sync_daemon_schedule(persisted)
        return persisted

    def trigger_schedule(
        self,
        schedule_id: str,
        *,
        now: datetime | None = None,
        source: str = "manual",
    ) -> WorkerQueueItemRead:
        current = now or utc_now()
        schedule = self._require_schedule(schedule_id)
        queued = self._enqueue_schedule(schedule, source=source, now=current)
        persisted = self._update_after_trigger(schedule, queued=queued, now=current, source=source)
        self._repository.save(persisted.schedule_id, persisted)
        self._sync_daemon_schedule(persisted)
        return queued

    def trigger_due(
        self,
        *,
        now: datetime | None = None,
    ) -> WorkerScheduleTickRead:
        current = now or utc_now()
        dispatches: list[WorkerScheduleDispatchRead] = []
        failures: dict[str, str] = {}
        due_schedules = [
            item
            for item in self.list_schedules()
            if item.enabled and item.next_run_at is not None and item.next_run_at <= current
        ]

        for schedule in due_schedules:
            try:
                queued = self._enqueue_schedule(schedule, source="due", now=current)
                updated = self._update_after_trigger(schedule, queued=queued, now=current, source="due")
                persisted = self._repository.save(updated.schedule_id, updated)
                self._sync_daemon_schedule(persisted)
                dispatches.append(
                    WorkerScheduleDispatchRead(
                        schedule_id=schedule.schedule_id,
                        run_id=queued.run_id,
                        task_type=queued.task_type,
                        queued_at=queued.created_at,
                    )
                )
            except Exception as exc:
                failures[schedule.schedule_id] = str(exc)
                failed = schedule.model_copy(
                    update={
                        "last_error": str(exc),
                        "updated_at": current,
                    }
                )
                persisted = self._repository.save(failed.schedule_id, failed)
                self._sync_daemon_schedule(persisted)
                logger.warning("Failed to dispatch worker schedule %s: %s", schedule.schedule_id, exc)

        return WorkerScheduleTickRead(
            scanned=len(due_schedules),
            dispatches=dispatches,
            failures=failures,
            created_at=current,
        )

    def _enqueue_schedule(
        self,
        schedule: WorkerRunScheduleRead,
        *,
        source: str,
        now: datetime,
    ) -> WorkerQueueItemRead:
        metadata = {
            **schedule.metadata,
            "schedule_id": schedule.schedule_id,
            "schedule_name": schedule.schedule_name,
            "scheduled_trigger_source": source,
        }
        return self._worker_scheduler.enqueue(
            WorkerQueueItemCreateRequest(
                queue_name=schedule.queue_name,
                task_name=schedule.task_name,
                task_type=schedule.task_type,
                payload=dict(schedule.payload),
                requested_by=schedule.requested_by,
                priority=schedule.priority,
                max_retries=schedule.max_retries,
                metadata=metadata,
            ),
            now=now,
        )

    def _update_after_trigger(
        self,
        schedule: WorkerRunScheduleRead,
        *,
        queued: WorkerQueueItemRead,
        now: datetime,
        source: str,
    ) -> WorkerRunScheduleRead:
        updates: dict[str, object] = {
            "last_triggered_at": now,
            "last_enqueued_run_id": queued.run_id,
            "last_error": None,
            "run_count": schedule.run_count + 1,
            "updated_at": now,
        }
        if source in {"due", "apscheduler"}:
            if schedule.schedule_mode == WorkerScheduleMode.ONCE:
                updates["enabled"] = False
                updates["next_run_at"] = None
            elif schedule.interval_seconds is not None:
                updates["next_run_at"] = self._next_run_from_trigger(
                    schedule=schedule,
                    fired_at=schedule.next_run_at or now,
                )
        return schedule.model_copy(update=updates)

    @staticmethod
    def _normalize_timezone(dt: datetime) -> timezone:
        return dt.tzinfo if dt.tzinfo is not None else timezone.utc

    def _next_run_from_trigger(
        self,
        *,
        schedule: WorkerRunScheduleRead,
        fired_at: datetime,
    ) -> datetime | None:
        timezone_hint = self._normalize_timezone(fired_at)
        if schedule.schedule_mode == WorkerScheduleMode.ONCE:
            trigger = DateTrigger(run_date=fired_at, timezone=timezone_hint)
            return trigger.get_next_fire_time(fired_at, fired_at)
        if schedule.interval_seconds is None:
            return None
        trigger = IntervalTrigger(
            seconds=max(1, schedule.interval_seconds),
            start_date=fired_at,
            timezone=timezone_hint,
        )
        return trigger.get_next_fire_time(fired_at, fired_at)

    def _require_schedule(self, schedule_id: str) -> WorkerRunScheduleRead:
        schedule = self.get_schedule(schedule_id)
        if schedule is None:
            raise KeyError(schedule_id)
        return schedule

    def bind_daemon(self, daemon: WorkerScheduleDaemon | None) -> None:
        self._daemon = daemon

    def _sync_daemon_schedule(self, schedule: WorkerRunScheduleRead) -> None:
        if self._daemon is not None:
            self._daemon.sync_schedule(schedule)


class WorkerScheduleDaemon:
    """APScheduler-backed background dispatcher for persisted worker schedules."""

    def __init__(
        self,
        *,
        service: WorkerScheduleService,
        poll_seconds: int = 30,
    ) -> None:
        self._service = service
        self._scheduler = AsyncIOScheduler(timezone=timezone.utc)
        self._misfire_grace_seconds = max(30, poll_seconds * 2)
        self._started = False
        self._service.bind_daemon(self)

    async def start(self) -> None:
        if self._started:
            return
        self._service.bind_daemon(self)
        self._scheduler.start()
        self._started = True
        for schedule in self._service.list_schedules():
            self.sync_schedule(schedule)

    async def stop(self) -> None:
        if not self._started:
            return
        logger.info("Worker schedule daemon stopping, waiting for in-flight jobs...")
        self._scheduler.shutdown(wait=True)
        self._started = False
        self._service.bind_daemon(None)
        logger.info("Worker schedule daemon stopped cleanly")

    def sync_schedule(self, schedule: WorkerRunScheduleRead) -> None:
        if self._started and self._job_exists(schedule.schedule_id):
            self._scheduler.remove_job(schedule.schedule_id)
        if not self._started or not schedule.enabled or schedule.next_run_at is None:
            return
        self._scheduler.add_job(
            self._run_schedule,
            trigger=DateTrigger(
                run_date=schedule.next_run_at,
                timezone=self._service._normalize_timezone(schedule.next_run_at),
            ),
            args=[schedule.schedule_id],
            id=schedule.schedule_id,
            replace_existing=True,
            coalesce=True,
            misfire_grace_time=self._misfire_grace_seconds,
        )

    def _job_exists(self, schedule_id: str) -> bool:
        return self._scheduler.get_job(schedule_id) is not None

    def _run_schedule(self, schedule_id: str) -> None:
        try:
            self._service.trigger_schedule(schedule_id, source="apscheduler")
        except Exception:
            logger.exception("APScheduler failed to dispatch worker schedule %s", schedule_id)
