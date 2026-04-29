from __future__ import annotations

import asyncio
import logging

from autoresearch.core.services.worker_scheduler import WorkerSchedulerService

logger = logging.getLogger(__name__)


class WorkerRecoveryDaemon:
    def __init__(self, *, scheduler: WorkerSchedulerService, poll_seconds: int = 20) -> None:
        self._scheduler = scheduler
        self._poll_seconds = max(1, poll_seconds)
        self._task: asyncio.Task[None] | None = None
        self._stop: asyncio.Event | None = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._stop = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="worker-recovery-daemon")

    async def stop(self) -> None:
        if self._stop is not None:
            self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None

    async def _run(self) -> None:
        if self._stop is None:
            return
        while not self._stop.is_set():
            try:
                recovered = self._scheduler.recover_stale_runs()
                if recovered:
                    logger.info("Worker recovery daemon reconciled runs=%s", len(recovered))
            except Exception:
                logger.exception("Worker recovery daemon tick failed")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self._poll_seconds)
            except asyncio.TimeoutError:
                continue
