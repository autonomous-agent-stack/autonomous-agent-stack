from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_worker_schedule_service
from autoresearch.core.services.worker_schedule_service import WorkerScheduleService
from autoresearch.shared.models import (
    WorkerQueueItemRead,
    WorkerRunScheduleCreateRequest,
    WorkerRunScheduleRead,
    WorkerRunScheduleResumeRequest,
    WorkerScheduleTickRead,
)


router = APIRouter(prefix="/api/v1/worker-schedules", tags=["worker-schedules"])


@router.post("", response_model=WorkerRunScheduleRead, status_code=status.HTTP_201_CREATED)
def create_worker_schedule(
    payload: WorkerRunScheduleCreateRequest,
    service: WorkerScheduleService = Depends(get_worker_schedule_service),
) -> WorkerRunScheduleRead:
    return service.create_schedule(payload)


@router.get("", response_model=list[WorkerRunScheduleRead], status_code=status.HTTP_200_OK)
def list_worker_schedules(
    service: WorkerScheduleService = Depends(get_worker_schedule_service),
) -> list[WorkerRunScheduleRead]:
    return service.list_schedules()


@router.get("/{schedule_id}", response_model=WorkerRunScheduleRead, status_code=status.HTTP_200_OK)
def get_worker_schedule(
    schedule_id: str,
    service: WorkerScheduleService = Depends(get_worker_schedule_service),
) -> WorkerRunScheduleRead:
    schedule = service.get_schedule(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return schedule


@router.post("/{schedule_id}/trigger", response_model=WorkerQueueItemRead, status_code=status.HTTP_201_CREATED)
def trigger_worker_schedule(
    schedule_id: str,
    service: WorkerScheduleService = Depends(get_worker_schedule_service),
) -> WorkerQueueItemRead:
    try:
        return service.trigger_schedule(schedule_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found") from exc


@router.post("/{schedule_id}/pause", response_model=WorkerRunScheduleRead, status_code=status.HTTP_200_OK)
def pause_worker_schedule(
    schedule_id: str,
    service: WorkerScheduleService = Depends(get_worker_schedule_service),
) -> WorkerRunScheduleRead:
    try:
        return service.pause_schedule(schedule_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found") from exc


@router.post("/{schedule_id}/resume", response_model=WorkerRunScheduleRead, status_code=status.HTTP_200_OK)
def resume_worker_schedule(
    schedule_id: str,
    payload: WorkerRunScheduleResumeRequest,
    service: WorkerScheduleService = Depends(get_worker_schedule_service),
) -> WorkerRunScheduleRead:
    try:
        return service.resume_schedule(schedule_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found") from exc


@router.post("/tick", response_model=WorkerScheduleTickRead, status_code=status.HTTP_200_OK)
def tick_worker_schedules(
    service: WorkerScheduleService = Depends(get_worker_schedule_service),
) -> WorkerScheduleTickRead:
    return service.trigger_due()
