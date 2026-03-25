from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_optimization_service
from autoresearch.shared.models import OptimizationCreateRequest, OptimizationRead
from autoresearch.train.services.optimizations import OptimizationService


router = APIRouter(prefix="/api/v1/loops", tags=["loop-control"])


@router.post(
    "",
    response_model=OptimizationRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_loop(
    payload: OptimizationCreateRequest,
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRead:
    return service.create(payload)


@router.get("", response_model=list[OptimizationRead])
def list_loops(
    service: OptimizationService = Depends(get_optimization_service),
) -> list[OptimizationRead]:
    return service.list()


@router.get("/{loop_id}", response_model=OptimizationRead)
def get_loop(
    loop_id: str,
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRead:
    loop = service.get(loop_id)
    if loop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Loop not found")
    return loop
