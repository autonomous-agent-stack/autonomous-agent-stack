from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from autoresearch.api.dependencies import (
    get_telegram_notifier_service,
    get_telegram_settings,
    get_worker_scheduler_service,
)
from autoresearch.api.settings import TelegramSettings
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.worker_scheduler import WorkerReportError
from autoresearch.shared.models import (
    JobStatus,
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


@router.get("/{run_id}", response_model=WorkerQueueItemRead, status_code=status.HTTP_200_OK)
def get_worker_run(
    run_id: str,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return run


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


@router.post("/{run_id}/cancel", response_model=WorkerQueueItemRead, status_code=status.HTTP_200_OK)
def cancel_worker_run(
    run_id: str,
    payload: WorkerRunOpsRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
    telegram_settings: TelegramSettings = Depends(get_telegram_settings),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
) -> WorkerQueueItemRead:
    try:
        stored = service.cancel_run(run_id, reason=payload.reason)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
    except WorkerReportError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    if stored.status == JobStatus.CANCELLED and telegram_settings.butler_api_completion_enabled:
        from autoresearch.api.routers.workers import (
            _maybe_send_butler_completion_fallback,
            _try_deliver_butler_completion_primary,
        )

        _try_deliver_butler_completion_primary(stored, notifier=notifier, scheduler=service)
        refreshed = service.get_run(stored.run_id)
        if refreshed is not None:
            stored = refreshed
        if telegram_settings.butler_completion_fallback_enabled:
            _maybe_send_butler_completion_fallback(
                stored,
                notifier=notifier,
                settings=telegram_settings,
                scheduler=service,
            )
    elif stored.status == JobStatus.RUNNING:
        _try_edit_cancel_requested_card(stored, notifier=notifier, scheduler=service)
        refreshed = service.get_run(stored.run_id)
        if refreshed is not None:
            stored = refreshed
    return stored


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


def _try_edit_cancel_requested_card(
    run: WorkerQueueItemRead,
    *,
    notifier: TelegramNotifierService,
    scheduler: WorkerSchedulerService,
) -> None:
    if not notifier.enabled:
        return
    metadata: dict[str, Any] = run.metadata or {}
    if metadata.get("telegram_cancel_requested_sent"):
        return
    if not metadata.get("telegram_completion_via_api"):
        return
    payload: dict[str, Any] = run.payload or {}
    chat_id = str(payload.get("chat_id") or metadata.get("chat_id") or "").strip()
    if not chat_id:
        return
    try:
        ack_message_id = int(metadata.get("telegram_queue_ack_message_id"))
    except (TypeError, ValueError):
        return
    thread_raw = payload.get("message_thread_id")
    try:
        thread_id = int(thread_raw) if thread_raw is not None and str(thread_raw).strip() else None
    except (TypeError, ValueError):
        thread_id = None
    reason = str(metadata.get("cancel_reason") or "cancelled by user").strip()
    text = "\n".join(
        [
            "已请求取消，worker 会在安全检查点停止。 / Cancellation requested; the worker will stop at a safe checkpoint.",
            "",
            "| 项 | 值 |",
            "| --- | --- |",
            f"| run_id | {run.run_id} |",
            "| 状态 | cancel_requested |",
            f"| 原因 | {reason[:500]} |",
        ]
    )
    if notifier.edit_message_text(
        chat_id=chat_id,
        message_id=ack_message_id,
        text=text[:3900],
        message_thread_id=thread_id,
    ):
        scheduler.merge_queue_metadata(run.run_id, {"telegram_cancel_requested_sent": True})
