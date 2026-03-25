from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_variant_service
from autoresearch.core.services.variants import VariantService
from autoresearch.shared.models import VariantCreateRequest, VariantRead


router = APIRouter(prefix="/api/v1/variants", tags=["variants"])


@router.post(
    "",
    response_model=VariantRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_variant(
    payload: VariantCreateRequest,
    service: VariantService = Depends(get_variant_service),
) -> VariantRead:
    return service.create(payload)


@router.get("", response_model=list[VariantRead])
def list_variants(
    service: VariantService = Depends(get_variant_service),
) -> list[VariantRead]:
    return service.list()


@router.get("/{variant_id}", response_model=VariantRead)
def get_variant(
    variant_id: str,
    service: VariantService = Depends(get_variant_service),
) -> VariantRead:
    variant = service.get(variant_id)
    if variant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    return variant
