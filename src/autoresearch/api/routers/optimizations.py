from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_optimization_service
from autoresearch.shared.models import OptimizationCreateRequest, OptimizationRead
from autoresearch.train.services.optimizations import OptimizationService

router = APIRouter(prefix="/api/v1/optimizations", tags=["optimizations"])


@router.post(
    "",
    response_model=OptimizationRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_optimization(
    payload: OptimizationCreateRequest,
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRead:
    return service.create(payload)


@router.get("", response_model=list[OptimizationRead])
def list_optimizations(
    service: OptimizationService = Depends(get_optimization_service),
) -> list[OptimizationRead]:
    return service.list()


@router.get("/{optimization_id}", response_model=OptimizationRead)
def get_optimization(
    optimization_id: str,
    service: OptimizationService = Depends(get_optimization_service),
) -> OptimizationRead:
    optimization = service.get(optimization_id)
    if optimization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Optimization not found")
    return optimization
