from __future__ import annotations

from fastapi import APIRouter, Depends, status

from autoresearch.api.dependencies import get_worker_scheduler_service
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    StandbyYouTubeAutoflowRequest,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerTaskType,
)


router = APIRouter(prefix="/api/v1/worker-runs", tags=["worker-runs"])


@router.post("", response_model=WorkerQueueItemRead, status_code=status.HTTP_201_CREATED)
def enqueue_worker_run(
    payload: WorkerQueueItemCreateRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    return service.enqueue(payload)


@router.post("/youtube-autoflow", response_model=WorkerQueueItemRead, status_code=status.HTTP_201_CREATED)
def enqueue_youtube_autoflow_run(
    payload: StandbyYouTubeAutoflowRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    return service.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.YOUTUBE_AUTOFLOW,
            payload=payload.model_dump(mode="json"),
            requested_by=payload.requested_by,
            metadata=payload.metadata,
        )
    )
