from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from autoresearch.api.dependencies import get_governed_mcp_service
from autoresearch.core.services.governed_mcp import (
    GovernedMCPService,
    GovernedMCPToolCallRead,
    GovernedMCPToolCallRequest,
    GovernedMCPToolRead,
    MCPServerRead,
)

router = APIRouter(prefix="/api/v1/mcp", tags=["governed-mcp"])


@router.get("/servers", response_model=list[MCPServerRead])
async def list_mcp_servers(
    service: GovernedMCPService = Depends(get_governed_mcp_service),
) -> list[MCPServerRead]:
    return service.list_servers()


@router.get("/tools", response_model=list[GovernedMCPToolRead])
async def list_mcp_tools(
    service: GovernedMCPService = Depends(get_governed_mcp_service),
) -> list[GovernedMCPToolRead]:
    return service.list_tools()


@router.post("/tools/{tool_id}/call", response_model=GovernedMCPToolCallRead)
async def call_mcp_tool(
    tool_id: str,
    body: dict[str, Any] = Body(default_factory=dict),
    service: GovernedMCPService = Depends(get_governed_mcp_service),
) -> GovernedMCPToolCallRead:
    request = GovernedMCPToolCallRequest.model_validate({**body, "tool_id": tool_id})
    result = service.call_tool(request)
    if result.status == "blocked":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=result.model_dump(mode="json"),
        )
    return result


@router.get("/doctor")
async def mcp_doctor(
    service: GovernedMCPService = Depends(get_governed_mcp_service),
) -> dict[str, object]:
    return service.doctor()
