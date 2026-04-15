from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from autoresearch.api.dependencies import get_personal_housekeeper_service
from autoresearch.core.services.personal_housekeeper import PersonalHousekeeperService
from autoresearch.shared.housekeeper_contract import (
    HousekeeperApprovalRequest,
    HousekeeperDispatchRequest,
    HousekeeperTaskRead,
)

router = APIRouter(prefix="/api/v1/openclaw/housekeeper", tags=["openclaw-housekeeper"])


@router.post("/dispatch", response_model=HousekeeperTaskRead, status_code=status.HTTP_202_ACCEPTED)
def dispatch_housekeeper_task(
    payload: HousekeeperDispatchRequest,
    service: PersonalHousekeeperService = Depends(get_personal_housekeeper_service),
) -> HousekeeperTaskRead:
    try:
        return service.dispatch(payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OpenClaw session not found"
        ) from exc


@router.get("/tasks", response_model=list[HousekeeperTaskRead])
def list_housekeeper_tasks(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    service: PersonalHousekeeperService = Depends(get_personal_housekeeper_service),
) -> list[HousekeeperTaskRead]:
    return service.list_tasks(session_id=session_id, limit=limit)


@router.get("/tasks/{task_id}", response_model=HousekeeperTaskRead)
def get_housekeeper_task(
    task_id: str,
    service: PersonalHousekeeperService = Depends(get_personal_housekeeper_service),
) -> HousekeeperTaskRead:
    item = service.get_task(task_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="housekeeper task not found"
        )
    return item


@router.post("/tasks/{task_id}/approve", response_model=HousekeeperTaskRead)
def approve_housekeeper_task(
    task_id: str,
    payload: HousekeeperApprovalRequest,
    service: PersonalHousekeeperService = Depends(get_personal_housekeeper_service),
) -> HousekeeperTaskRead:
    try:
        return service.approve_task(task_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="housekeeper task not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/tasks/{task_id}/reject", response_model=HousekeeperTaskRead)
def reject_housekeeper_task(
    task_id: str,
    payload: HousekeeperApprovalRequest,
    service: PersonalHousekeeperService = Depends(get_personal_housekeeper_service),
) -> HousekeeperTaskRead:
    try:
        return service.reject_task(task_id, payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="housekeeper task not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
