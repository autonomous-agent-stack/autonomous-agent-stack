from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import Field

from autoresearch.api.settings import get_runtime_settings
from autoresearch.personal_packages import PERSONAL_PACKAGE_DEFINITIONS
from autoresearch.shared.models import StrictModel


router = APIRouter(prefix="/api/v2/packages", tags=["packages"])


class PackageRead(StrictModel):
    package_id: str
    stability: Literal["experimental", "beta", "stable"] = "experimental"
    installed: bool = False
    enabled: bool = False
    source: str = "registry"
    route_prefixes: list[str] = Field(default_factory=list)
    capability_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


@router.get("", response_model=list[PackageRead])
def list_packages() -> list[PackageRead]:
    settings = get_runtime_settings()
    personal_packages = [
        PackageRead(
            package_id=definition.package_id,
            stability=definition.stability,
            installed=True,
            enabled=settings.is_personal_package_enabled(definition.package_id),
            source="local_personal_package",
            route_prefixes=list(definition.route_prefixes),
            capability_ids=list(definition.capability_ids),
            metadata=definition.metadata or {},
        )
        for definition in PERSONAL_PACKAGE_DEFINITIONS
    ]
    return [
        *personal_packages,
        PackageRead(
            package_id="reference.furniture",
            stability="experimental",
            installed=False,
            enabled=False,
            metadata={"reason": "Reference package must install through Package Registry before GA."},
        )
    ]
