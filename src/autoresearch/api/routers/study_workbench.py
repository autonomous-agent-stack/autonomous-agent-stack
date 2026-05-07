from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from autoresearch.api.dependencies import get_study_workbench_service, get_worker_scheduler_service
from autoresearch.core.services.study_workbench import StudyWorkbenchService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import WorkerQueueItemCreateRequest, WorkerQueueItemRead, WorkerTaskType


router = APIRouter(prefix="/api/v1/study-workbench", tags=["study-workbench"])


class StudyPrepareRequest(BaseModel):
    title: str = ""
    markdown_text: str = ""
    markdown: str = ""
    markdown_path: str = ""
    targets: list[str] = Field(default_factory=list)
    items: list[dict[str, Any]] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)
    requested_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StudyIngestRequest(BaseModel):
    sources: list[str] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)
    source_kind: str = ""
    requested_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StudyGitSyncRequest(BaseModel):
    paths: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    message: str = ""
    requested_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("/health", status_code=status.HTTP_200_OK)
def study_workbench_health(
    service: StudyWorkbenchService = Depends(get_study_workbench_service),
) -> dict[str, Any]:
    return service.health()


@router.post("/prepare", response_model=WorkerQueueItemRead, status_code=status.HTTP_201_CREATED)
def enqueue_study_prepare(
    payload: StudyPrepareRequest,
    scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    return scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.STUDY_PREPARE,
            payload=payload.model_dump(exclude={"requested_by", "metadata"}),
            requested_by=payload.requested_by,
            metadata=payload.metadata,
        )
    )


@router.post("/ingest", response_model=WorkerQueueItemRead, status_code=status.HTTP_201_CREATED)
def enqueue_study_ingest(
    payload: StudyIngestRequest,
    scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    return scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.STUDY_INGEST,
            payload=payload.model_dump(exclude={"requested_by", "metadata"}),
            requested_by=payload.requested_by,
            metadata=payload.metadata,
        )
    )


@router.post("/git-sync", response_model=WorkerQueueItemRead, status_code=status.HTTP_201_CREATED)
def enqueue_study_git_sync(
    payload: StudyGitSyncRequest,
    scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    return scheduler.enqueue(
        WorkerQueueItemCreateRequest(
            task_type=WorkerTaskType.STUDY_GIT_SYNC,
            payload=payload.model_dump(exclude={"requested_by", "metadata"}),
            requested_by=payload.requested_by,
            metadata=payload.metadata,
        )
    )
