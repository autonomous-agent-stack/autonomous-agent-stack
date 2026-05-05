from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol

from autoresearch.shared.governance_core import GovernanceAdapterRead, GovernanceTaskRead


@dataclass(frozen=True)
class GovernanceAdapterResult:
    output: dict[str, Any]
    artifacts: list[dict[str, Any]] = field(default_factory=list)


class GovernanceAdapter(Protocol):
    descriptor: GovernanceAdapterRead

    def execute(self, task: GovernanceTaskRead) -> GovernanceAdapterResult: ...


class EchoAdapter:
    """Deterministic local adapter used by the MVP closed loop."""

    descriptor = GovernanceAdapterRead(
        adapter_id="echo",
        name="Echo Adapter",
        type="local",
        enabled=True,
        description="Returns the submitted task payload without external calls.",
        capabilities=["deterministic_runner", "local_smoke_test"],
        external_calls_enabled=False,
    )

    def execute(self, task: GovernanceTaskRead) -> GovernanceAdapterResult:
        return GovernanceAdapterResult(
            output={
                "adapter_id": self.descriptor.adapter_id,
                "task_id": task.task_id,
                "name": task.name,
                "parameters": task.parameters,
                "risk_tags": task.risk_tags,
                "runner": "local_deterministic_sequential_runner",
            },
            artifacts=[
                {
                    "type": "json",
                    "uri": f"memory://governance-runs/{task.task_id}/echo-output",
                    "metadata": {"adapter_id": self.descriptor.adapter_id},
                }
            ],
        )


class A2AAdapter:
    """A2A boundary placeholder.

    Real network calls are intentionally disabled by default for the governance
    MVP. Set AUTORESEARCH_A2A_ENABLED=1 and provide a gateway URL before
    replacing this skeleton with a protocol client.
    """

    def __init__(self) -> None:
        self._enabled = os.getenv("AUTORESEARCH_A2A_ENABLED", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self._gateway_url = os.getenv("AUTORESEARCH_A2A_GATEWAY_URL", "").strip()
        self.descriptor = GovernanceAdapterRead(
            adapter_id="a2a",
            name="A2A Adapter",
            type="a2a",
            enabled=self._enabled and bool(self._gateway_url),
            description="Agent2Agent protocol adapter skeleton; external calls are disabled by default.",
            capabilities=["agent_card", "tasks_send"],
            external_calls_enabled=self._enabled and bool(self._gateway_url),
            metadata={"gateway_configured": bool(self._gateway_url)},
        )

    def execute(self, task: GovernanceTaskRead) -> GovernanceAdapterResult:
        if not self.descriptor.enabled:
            raise RuntimeError(
                "A2A adapter is disabled. Set AUTORESEARCH_A2A_ENABLED=1 and "
                "AUTORESEARCH_A2A_GATEWAY_URL to enable real protocol calls."
            )
        return GovernanceAdapterResult(
            output={
                "adapter_id": self.descriptor.adapter_id,
                "task_id": task.task_id,
                "gateway_url": self._gateway_url,
                "state": "not_sent",
                "reason": "MVP skeleton preserves the A2A boundary without making network calls.",
            }
        )


class GovernanceAdapterRegistry:
    def __init__(self, adapters: list[GovernanceAdapter] | None = None) -> None:
        configured = adapters or [EchoAdapter(), A2AAdapter()]
        self._adapters = {adapter.descriptor.adapter_id: adapter for adapter in configured}

    def list_descriptors(self) -> list[GovernanceAdapterRead]:
        return sorted(
            (adapter.descriptor for adapter in self._adapters.values()),
            key=lambda item: item.adapter_id,
        )

    def get(self, adapter_id: str) -> GovernanceAdapter:
        adapter = self._adapters.get(adapter_id)
        if adapter is None:
            raise KeyError(adapter_id)
        return adapter
