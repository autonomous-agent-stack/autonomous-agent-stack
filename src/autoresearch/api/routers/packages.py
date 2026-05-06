from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from autoresearch.shared.models import StrictModel


router = APIRouter(prefix="/api/v2/packages", tags=["packages"])


class PackageRead(StrictModel):
    package_id: str
    stability: Literal["experimental", "beta", "stable"] = "experimental"
    installed: bool = False
    source: str = "registry"
    metadata: dict[str, object] = Field(default_factory=dict)


@router.get("", response_model=list[PackageRead])
def list_packages() -> list[PackageRead]:
    return [
        PackageRead(
            package_id="reference.furniture",
            stability="experimental",
            installed=False,
            metadata={"reason": "Reference package must install through Package Registry before GA."},
        )
    ]

