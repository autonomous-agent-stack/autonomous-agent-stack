from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from autoresearch.core.services.connector_registry import ConnectorRegistryService
from autoresearch.ga.contracts import ConnectorDescriptorRead


router = APIRouter(prefix="/api/v2/connectors", tags=["connectors"])

_REPO_ROOT = Path(__file__).resolve().parents[4]


@router.get("", response_model=list[ConnectorDescriptorRead])
def list_connectors() -> list[ConnectorDescriptorRead]:
    return ConnectorRegistryService(_REPO_ROOT / "configs/connectors/registry.yaml").list_connectors()

