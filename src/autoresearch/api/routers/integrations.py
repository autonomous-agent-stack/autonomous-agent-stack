from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_self_integration_service
from autoresearch.core.services.self_integration import SelfIntegrationService
from autoresearch.shared.models import (
    IntegrationDiscoverRequest,
    IntegrationDiscoveryRead,
    IntegrationPromoteRequest,
    IntegrationPromotionRead,
    IntegrationPrototypeRead,
    IntegrationPrototypeRequest,
)


router = APIRouter(prefix="/api/v1/integrations", tags=["self-integration"])


@router.post(
    "/discover",
    response_model=IntegrationDiscoveryRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def discover_integration(
    payload: IntegrationDiscoverRequest,
    service: SelfIntegrationService = Depends(get_self_integration_service),
) -> IntegrationDiscoveryRead:
    try:
        return service.discover(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/prototype",
    response_model=IntegrationPrototypeRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def prototype_integration(
    payload: IntegrationPrototypeRequest,
    service: SelfIntegrationService = Depends(get_self_integration_service),
) -> IntegrationPrototypeRead:
    try:
        return service.prototype(payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discovery not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/promote",
    response_model=IntegrationPromotionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def promote_integration(
    payload: IntegrationPromoteRequest,
    service: SelfIntegrationService = Depends(get_self_integration_service),
) -> IntegrationPromotionRead:
    try:
        return service.promote(payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prototype not found") from exc
