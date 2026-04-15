from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, status

from autoresearch.api.dependencies import get_worker_registry_service
from autoresearch.api.dependencies import get_worker_scheduler_service
from autoresearch.core.services.worker_scheduler import (
    WorkerClaimError,
    WorkerReportError,
    WorkerSchedulerService,
)
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.models import (
    WorkerClaimRead,
    WorkerClaimRequest,
    WorkerHeartbeatRequest,
    WorkerQueueItemRead,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    WorkerRunReportRequest,
)


router = APIRouter(prefix="/api/v1/workers", tags=["workers"])


@router.post("/register", response_model=WorkerRegistrationRead, status_code=status.HTTP_200_OK)
def register_worker(
    payload: WorkerRegisterRequest,
    service: WorkerRegistryService = Depends(get_worker_registry_service),
) -> WorkerRegistrationRead:
    return service.register(payload)


@router.post("/{worker_id}/heartbeat", response_model=WorkerRegistrationRead, status_code=status.HTTP_200_OK)
def heartbeat_worker(
    worker_id: str,
    payload: WorkerHeartbeatRequest,
    service: WorkerRegistryService = Depends(get_worker_registry_service),
) -> WorkerRegistrationRead:
    try:
        return service.heartbeat(worker_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found") from exc


@router.post("/{worker_id}/claim", response_model=WorkerClaimRead, status_code=status.HTTP_200_OK)
def claim_worker_run(
    worker_id: str,
    payload: WorkerClaimRequest = Body(default_factory=WorkerClaimRequest),
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerClaimRead:
    try:
        return service.claim(worker_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found") from exc
    except WorkerClaimError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc


@router.post(
    "/{worker_id}/runs/{run_id}/report",
    response_model=WorkerQueueItemRead,
    status_code=status.HTTP_200_OK,
)
def report_worker_run(
    worker_id: str,
    run_id: str,
    payload: WorkerRunReportRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerQueueItemRead:
    try:
        return service.report(worker_id, run_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
    except WorkerReportError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc
