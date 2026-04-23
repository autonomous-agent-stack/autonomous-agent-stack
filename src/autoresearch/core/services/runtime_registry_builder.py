"""Build RuntimeAdapterServiceRegistry for worker processes without FastAPI dependencies."""

from __future__ import annotations

from pathlib import Path

from autoresearch.agent_protocol.runtime_registry import RuntimeAdapterRegistry
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.claude_runtime_service import ClaudeRuntimeService
from autoresearch.core.services.hermes_runtime_adapter import HermesRuntimeAdapterService
from autoresearch.core.services.openclaw_runtime_adapter import OpenClawRuntimeAdapterService
from autoresearch.core.services.runtime_adapter_registry import RuntimeAdapterServiceRegistry


def build_runtime_adapter_registry_for_worker(
    *,
    repo_root: Path,
    claude_runtime: ClaudeRuntimeService,
) -> RuntimeAdapterServiceRegistry:
    """Wire openclaw + hermes adapters sharing the same ClaudeAgentService as claude_runtime."""
    agent_service: ClaudeAgentService = claude_runtime.agent_service
    openclaw_service = agent_service.openclaw_service
    manifests_dir = repo_root / "configs" / "runtime_agents"
    manifest_registry = RuntimeAdapterRegistry(manifests_dir)

    def openclaw_factory() -> OpenClawRuntimeAdapterService:
        return OpenClawRuntimeAdapterService(
            openclaw_service=openclaw_service,
            claude_service=agent_service,
        )

    def hermes_factory() -> HermesRuntimeAdapterService:
        return HermesRuntimeAdapterService(
            openclaw_service=openclaw_service,
            claude_service=agent_service,
        )

    return RuntimeAdapterServiceRegistry(
        manifest_registry=manifest_registry,
        factories={
            "openclaw": openclaw_factory,
            "hermes": hermes_factory,
        },
    )
