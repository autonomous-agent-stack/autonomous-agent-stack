from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_study_dashboard_service, get_worker_scheduler_service
from autoresearch.core.services.study_dashboard import StudyDashboardError, StudyDashboardService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    WorkerQueueItemCreateRequest,
    WorkerTaskType,
    StudyDashboardBriefRead,
    StudyDashboardDailyBriefRequest,
    StudyDashboardExportRead,
    StudyDashboardExportRequest,
    StudyDashboardItemActionRead,
    StudyDashboardItemActionRequest,
    StudyDashboardRefreshRead,
    StudyDashboardRefreshRequest,
    StudyDashboardStateRead,
    StudyDashboardSourceKind,
)


router = APIRouter(prefix="/api/v1/study-dashboard", tags=["study-dashboard"])


@router.get("/state", response_model=StudyDashboardStateRead, status_code=status.HTTP_200_OK)
def get_study_dashboard_state(
    service: StudyDashboardService = Depends(get_study_dashboard_service),
) -> StudyDashboardStateRead:
    return service.state()


@router.post("/refresh", response_model=StudyDashboardRefreshRead, status_code=status.HTTP_200_OK)
def refresh_study_dashboard(
    payload: StudyDashboardRefreshRequest,
    service: StudyDashboardService = Depends(get_study_dashboard_service),
) -> StudyDashboardRefreshRead:
    return service.refresh(payload)


@router.post("/briefs/daily", response_model=StudyDashboardBriefRead, status_code=status.HTTP_201_CREATED)
def create_daily_study_brief(
    payload: StudyDashboardDailyBriefRequest,
    service: StudyDashboardService = Depends(get_study_dashboard_service),
) -> StudyDashboardBriefRead:
    try:
        return service.create_daily_brief(payload)
    except StudyDashboardError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post(
    "/briefs/{brief_id}/export",
    response_model=StudyDashboardExportRead,
    status_code=status.HTTP_200_OK,
)
def export_study_brief(
    brief_id: str,
    payload: StudyDashboardExportRequest,
    service: StudyDashboardService = Depends(get_study_dashboard_service),
) -> StudyDashboardExportRead:
    try:
        return service.export_brief(brief_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found") from exc


@router.post(
    "/items/{item_id}/actions",
    response_model=StudyDashboardItemActionRead,
    status_code=status.HTTP_200_OK,
)
def apply_study_item_action(
    item_id: str,
    payload: StudyDashboardItemActionRequest,
    service: StudyDashboardService = Depends(get_study_dashboard_service),
    scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> StudyDashboardItemActionRead:
    try:
        result = service.apply_item_action(item_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found") from exc

    if (
        payload.action == "deep_dive"
        and result.item.source_kind == StudyDashboardSourceKind.YOUTUBE_PLAYLIST
        and result.item.source_url
    ):
        queued = scheduler.enqueue(
            WorkerQueueItemCreateRequest(
                task_name=f"study_dashboard_youtube_deep_dive:{result.item.item_id}",
                task_type=WorkerTaskType.YOUTUBE_AUTOFLOW,
                payload={
                    "source_url": result.item.source_url,
                    "repo_hint": "study-dashboard",
                    "metadata": {
                        "source": "study_dashboard",
                        "study_item_id": result.item.item_id,
                        "target_agent": "youtube_ops",
                        "marginnote4": True,
                    },
                },
                requested_by="study-dashboard",
                metadata={"study_item_id": result.item.item_id, "source_url": result.item.source_url},
            )
        )
        return result.model_copy(
            update={
                "message": "YouTube deep-dive worker queued",
                "artifacts": [
                    *result.artifacts,
                    {
                        "kind": "worker_run",
                        "run_id": queued.run_id,
                        "task_type": queued.task_type.value,
                    },
                ],
            }
        )
    return result
