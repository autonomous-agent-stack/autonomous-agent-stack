from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_variant_service
from autoresearch.core.services.variants import VariantService
from autoresearch.shared.models import VariantCreateRequest, VariantRead


router = APIRouter(prefix="/api/v1/generators", tags=["generators"])


@router.post(
    "",
    response_model=VariantRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_generator(
    payload: VariantCreateRequest,
    service: VariantService = Depends(get_variant_service),
) -> VariantRead:
    return service.create(payload)


@router.get("", response_model=list[VariantRead])
def list_generators(
    service: VariantService = Depends(get_variant_service),
) -> list[VariantRead]:
    return service.list()


@router.get("/{generator_id}", response_model=VariantRead)
def get_generator(
    generator_id: str,
    service: VariantService = Depends(get_variant_service),
) -> VariantRead:
    generated = service.get(generator_id)
    if generated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Generator task not found")
    return generated
