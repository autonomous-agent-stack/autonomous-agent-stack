from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from autoresearch.api.dependencies import get_federation_service
from autoresearch.control_plane.contracts import ControlPlaneOperatorActionRequest
from autoresearch.core.services.federation import (
    FederationCapabilityRead,
    FederationLeaseCreateRequest,
    FederationLeaseRead,
    FederationPeerRead,
    FederationService,
    FederationTaskCreateRequest,
    FederationTaskRead,
)

router = APIRouter(prefix="/api/v1/federation", tags=["federation"])


@router.get("/peers", response_model=list[FederationPeerRead])
async def list_federation_peers(
    service: FederationService = Depends(get_federation_service),
) -> list[FederationPeerRead]:
    return service.list_peers()


@router.get("/capabilities", response_model=list[FederationCapabilityRead])
async def list_federation_capabilities(
    service: FederationService = Depends(get_federation_service),
) -> list[FederationCapabilityRead]:
    return service.list_capabilities()


@router.get("/leases", response_model=list[FederationLeaseRead])
async def list_federation_leases(
    peer_id: str | None = Query(default=None),
    service: FederationService = Depends(get_federation_service),
) -> list[FederationLeaseRead]:
    return service.list_leases(peer_id=peer_id)


@router.post("/leases", response_model=FederationLeaseRead, status_code=status.HTTP_201_CREATED)
async def create_federation_lease(
    request: FederationLeaseCreateRequest,
    service: FederationService = Depends(get_federation_service),
) -> FederationLeaseRead:
    try:
        return service.create_lease(request)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/leases/{lease_id}/revoke", response_model=FederationLeaseRead)
async def revoke_federation_lease(
    lease_id: str,
    request: ControlPlaneOperatorActionRequest,
    service: FederationService = Depends(get_federation_service),
) -> FederationLeaseRead:
    try:
        return service.revoke_lease(
            lease_id,
            requested_by=request.requested_by,
            reason=request.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/tasks", response_model=FederationTaskRead, status_code=status.HTTP_202_ACCEPTED)
async def create_federation_task(
    request: FederationTaskCreateRequest,
    service: FederationService = Depends(get_federation_service),
) -> FederationTaskRead:
    try:
        result = service.submit_task(request)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    if result.status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.model_dump(mode="json"),
        )
    return result


@router.get("/tasks/{task_id}", response_model=FederationTaskRead)
async def get_federation_task(
    task_id: str,
    service: FederationService = Depends(get_federation_service),
) -> FederationTaskRead:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="federation task not found")
    return task


@router.get("/doctor")
async def federation_doctor(
    service: FederationService = Depends(get_federation_service),
) -> dict[str, object]:
    return service.doctor()
