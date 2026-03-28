from __future__ import annotations

from typing import Any

from orchestrator.mcp_context import MCPContextBlock

from autoresearch.core.adapters.contracts import (
    CapabilityDomain,
    CapabilityProviderDescriptorRead,
    MCPProvider,
    MCPToolCallResultRead,
    MCPToolDescriptorRead,
    ProviderStatus,
)


class MCPContextProviderAdapter(MCPProvider):
    def __init__(self, context: MCPContextBlock | None = None) -> None:
        self._context = context or MCPContextBlock()

    def describe(self) -> CapabilityProviderDescriptorRead:
        return CapabilityProviderDescriptorRead(
            provider_id="mcp-context",
            domain=CapabilityDomain.MCP,
            display_name="MCP Context",
            capabilities=["list_tools", "call_tool"],
            metadata={"endpoint": self._context.mcp_endpoint},
        )

    def list_tools(self) -> list[MCPToolDescriptorRead]:
        descriptions: list[MCPToolDescriptorRead] = []
        registered = getattr(self._context, "tools", {})
        for tool_name in self._context.discover_tools():
            tool_config = registered.get(tool_name)
            description = ""
            if isinstance(tool_config, dict):
                description = str(tool_config.get("description", "")).strip()
            descriptions.append(
                MCPToolDescriptorRead(
                    name=tool_name,
                    description=description,
                    metadata={"registered": tool_name in registered},
                )
            )
        return descriptions

    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> MCPToolCallResultRead:
        try:
            result = await self._context.call_tool(tool_name, params)
        except Exception as exc:
            return MCPToolCallResultRead(
                provider_id="mcp-context",
                tool_name=tool_name,
                status=ProviderStatus.DEGRADED,
                result={},
                error=str(exc),
            )
        return MCPToolCallResultRead(
            provider_id="mcp-context",
            tool_name=tool_name,
            status=ProviderStatus.AVAILABLE,
            result=result,
        )
