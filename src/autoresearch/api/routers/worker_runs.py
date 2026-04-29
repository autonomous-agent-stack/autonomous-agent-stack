from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from autoresearch.api.dependencies import get_worker_scheduler_service
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.worker_scheduler import WorkerReportError
from autoresearch.shared.models import (
    StandbyYouTubeAutoflowRequest,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
    WorkerTaskType,
)


router = APIRouter(prefix="/api/v1/worker-runs", tags=["worker-runs"])


class ContentKBClassifyRequest(BaseModel):
    """Request body for content_kb_classify task."""

    text: str = Field(..., min_length=1, description="Text to classify")
    requested_by: str | None = None
    metadata: dict = Field(default_factory=dict)


class ContentKBIngestRequest(BaseModel):
    """Request body for content_kb_ingest task."""

    subtitle_text_path: str = Field(..., min_length=1, description="Path to SRT subtitle file")
    title: str = Field("", description="Content title (defaults to filename stem)")
    topic: str = Field("", description="Content topic (auto-classified if empty)")
    source_url: str = Field("", description="Optional source URL")
    speakers: list[str] = Field(default_factory=list, description="Speaker names")
    created_at: str = Field("", description="Content date (ISO format)")
    owner: str = Field("knowledge-base", description="GitHub owner/org")
    default_repo: str = Field("knowledge-base", description="Default target repo name")
    open_draft_pr: bool = Field(False, description="Signal draft PR creation intent")
    requested_by: str | None = None
    metadata: dict = Field(default_factory=dict)


class WorkerRunOpsRequest(BaseModel):
    reason: str = Field(default="manual operation")
    backoff_seconds: int | None = Field(default=None, ge=1, le=3600)


@router.post("", response_model=WorkerQueueItemRead, status_code=status.HTTP_201_CREATED)
def enqueue_worker_run(
    payload: WorkerQueueItemCreateRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    return service.enqueue(payload)


@router.get("", response_model=list[WorkerQueueItemRead], status_code=status.HTTP_200_OK)
def list_worker_runs(
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> list[WorkerQueueItemRead]:
    return service.list_queue()


@router.post("/{run_id}/requeue", response_model=WorkerQueueItemRead, status_code=status.HTTP_200_OK)
def requeue_worker_run(
    run_id: str,
    payload: WorkerRunOpsRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    try:
        return service.requeue_run(
            run_id,
            reason=payload.reason,
            backoff_seconds=payload.backoff_seconds,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
    except WorkerReportError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc


@router.post("/{run_id}/force-fail", response_model=WorkerQueueItemRead, status_code=status.HTTP_200_OK)
def force_fail_worker_run(
    run_id: str,
    payload: WorkerRunOpsRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    try:
        return service.force_fail_run(run_id, reason=payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
    except WorkerReportError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc


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


@router.post("/content-kb-classify", response_model=WorkerQueueItemRead, status_code=status.HTTP_201_CREATED)
def enqueue_content_kb_classify_run(
    payload: ContentKBClassifyRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    return service.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_CLASSIFY,
            payload={"text": payload.text},
            requested_by=payload.requested_by,
            metadata=payload.metadata,
        )
    )


@router.post("/content-kb-ingest", response_model=WorkerQueueItemRead, status_code=status.HTTP_201_CREATED)
def enqueue_content_kb_ingest_run(
    payload: ContentKBIngestRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    return service.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload=payload.model_dump(exclude={"requested_by", "metadata"}),
            requested_by=payload.requested_by,
            metadata=payload.metadata,
        )
    )
