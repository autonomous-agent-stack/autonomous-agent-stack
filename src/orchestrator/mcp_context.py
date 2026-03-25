"""
MCP ContextBlock - 无缝挂载 MCP 网关

包含 Dynamic Tool Synthesis:
生成工具代码 -> 沙盒验证 -> 工具池注册 -> 调用复用。
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any, Callable, Optional

from .tool_synthesis import ToolSynthesisError, ToolSynthesisPolicy, ToolSynthesizer


class MCPContextBlock:
    """
    MCP 上下文块

    将 InfoQuest/MCP 的工具链统一桥接到 MASFactory。
    """

    def __init__(self, mcp_endpoint: str = "https://mcp.infoquest.bytepluses.com/mcp") -> None:
        self.mcp_endpoint = mcp_endpoint
        self.tools: dict[str, Any] = {}
        self.cache: dict[str, Any] = {}
        self.session_token: Optional[str] = None
        self._synthesizer: ToolSynthesizer | None = None

    def register_tool(self, tool_name: str, tool_config: Any) -> None:
        """
        注册工具（可为配置字典或可调用对象）。
        """
        self.tools[tool_name] = tool_config
        print(f"✅ 注册 MCP 工具: {tool_name}")

    def enable_dynamic_tool_synthesis(
        self,
        workspace: str | Path = ".generated_tools",
        max_tools: int = 20,
        timeout_seconds: int = 10,
        execution_backend: str = "docker",
        docker_image: str = "python:3.12-alpine",
        docker_cpus: str = "1.0",
        docker_memory: str = "512m",
        docker_pids_limit: int = 128,
    ) -> None:
        self._synthesizer = ToolSynthesizer(
            workspace=Path(workspace),
            policy=ToolSynthesisPolicy(
                max_tools=max_tools,
                timeout_seconds=timeout_seconds,
                execution_backend=execution_backend,
                docker_image=docker_image,
                docker_cpus=docker_cpus,
                docker_memory=docker_memory,
                docker_pids_limit=docker_pids_limit,
            ),
        )

    def synthesize_tool(
        self,
        tool_name: str,
        source_code: str,
        entrypoint: str = "run",
        sample_input: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        动态合成工具并注册到当前 MCPContextBlock。
        """
        if self._synthesizer is None:
            self.enable_dynamic_tool_synthesis()

        assert self._synthesizer is not None
        synthesized = self._synthesizer.synthesize(
            tool_name=tool_name,
            source_code=source_code,
            entrypoint=entrypoint,
            sample_input=sample_input or {},
        )
        self.register_tool(tool_name, self._build_synthesized_tool_handler(tool_name))
        return synthesized.to_dict()

    def list_synthesized_tools(self) -> list[dict[str, Any]]:
        if self._synthesizer is None:
            return []
        return [tool.to_dict() for tool in self._synthesizer.list_tools()]

    async def call_tool(
        self,
        tool_name: str,
        params: dict[str, Any],
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        调用 MCP 工具。
        """
        cache_key = f"{tool_name}:{json.dumps(params, sort_keys=True)}"
        if use_cache and cache_key in self.cache:
            print(f"📦 使用缓存: {tool_name}")
            return self.cache[cache_key]

        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not registered")

        print(f"🔧 调用 MCP 工具: {tool_name}")
        handler = self.tools[tool_name]

        result: dict[str, Any]
        if callable(handler):
            result = await self._call_callable_tool(handler, params)
        elif isinstance(handler, dict) and callable(handler.get("handler")):
            result = await self._call_callable_tool(handler["handler"], params)
        else:
            # 兼容旧的配置型工具（模拟 MCP 调用占位）
            result = {
                "tool": tool_name,
                "params": params,
                "result": "success",
                "data": f"Processed {params}",
            }

        if use_cache:
            self.cache[cache_key] = result

        return result

    def discover_tools(self) -> list[str]:
        """
        动态发现 MCP 工具。
        """
        baseline_tools = [
            "web_search",
            "link_reader",
            "file_reader",
            "code_analyzer",
            "data_processor",
        ]
        merged = sorted(set(baseline_tools + list(self.tools.keys())))
        print(f"🔍 发现 {len(merged)} 个 MCP 工具")
        return merged

    def set_session_token(self, token: str) -> None:
        self.session_token = token

    def clear_cache(self) -> None:
        self.cache.clear()
        print("🗑️ 缓存已清空")

    async def _call_callable_tool(
        self,
        handler: Callable[..., Any],
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if inspect.iscoroutinefunction(handler):
            raw = await handler(params)
        else:
            try:
                raw = handler(params)
            except TypeError:
                raw = handler(**params)

        if isinstance(raw, dict):
            return raw
        return {"result": raw}

    def _build_synthesized_tool_handler(self, tool_name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def _handler(payload: dict[str, Any]) -> dict[str, Any]:
            if self._synthesizer is None:
                raise ToolSynthesisError("dynamic tool synthesizer not enabled")
            return self._synthesizer.invoke(tool_name, payload)

        return _handler


class MCPToolRegistry:
    """
    MCP 工具注册表
    """

    def __init__(self) -> None:
        self.tools: dict[str, dict[str, Any]] = {}

    def register(self, name: str, description: str, endpoint: str, auth_required: bool = False) -> None:
        self.tools[name] = {
            "name": name,
            "description": description,
            "endpoint": endpoint,
            "auth_required": auth_required,
        }

    def get(self, name: str) -> Optional[dict[str, Any]]:
        return self.tools.get(name)

    def list_all(self) -> list[str]:
        return list(self.tools.keys())


def create_default_mcp_registry() -> MCPToolRegistry:
    registry = MCPToolRegistry()
    registry.register(
        name="web_search",
        description="网络搜索工具",
        endpoint="https://mcp.infoquest.bytepluses.com/mcp/web_search",
        auth_required=False,
    )
    registry.register(
        name="link_reader",
        description="链接读取工具",
        endpoint="https://mcp.infoquest.bytepluses.com/mcp/link_reader",
        auth_required=False,
    )
    registry.register(
        name="file_reader",
        description="文件读取工具",
        endpoint="https://mcp.infoquest.bytepluses.com/mcp/file_reader",
        auth_required=True,
    )
    registry.register(
        name="code_analyzer",
        description="代码分析工具",
        endpoint="https://mcp.infoquest.bytepluses.com/mcp/code_analyzer",
        auth_required=False,
    )
    return registry
