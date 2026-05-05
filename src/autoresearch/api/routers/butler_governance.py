from __future__ import annotations

from fastapi import APIRouter, Depends

from autoresearch.api.dependencies import get_butler_tool_broker_service
from autoresearch.core.services.butler_tool_broker import (
    ButlerRegistryRead,
    ButlerToolBroker,
    ButlerToolDescriptorRead,
    ButlerToolResolutionRead,
    ButlerToolResolveRequest,
)


router = APIRouter(prefix="/api/v2", tags=["butler-governance"])


@router.get("/butler/registry", response_model=ButlerRegistryRead)
def get_butler_registry(
    broker: ButlerToolBroker = Depends(get_butler_tool_broker_service),
) -> ButlerRegistryRead:
    return broker.registry()


@router.get("/butler/tools", response_model=list[ButlerToolDescriptorRead])
def list_butler_tools(
    broker: ButlerToolBroker = Depends(get_butler_tool_broker_service),
) -> list[ButlerToolDescriptorRead]:
    return broker.list_tools()


@router.post("/butler/tools/resolve", response_model=ButlerToolResolutionRead)
def resolve_butler_tools(
    payload: ButlerToolResolveRequest,
    broker: ButlerToolBroker = Depends(get_butler_tool_broker_service),
) -> ButlerToolResolutionRead:
    return broker.resolve(payload)
