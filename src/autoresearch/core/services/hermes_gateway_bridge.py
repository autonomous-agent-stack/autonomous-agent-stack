from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from autoresearch.core.services.claude_runtime_service import ClaudeRuntimeExecutionResult
from autoresearch.shared.models import JobStatus


class HermesGatewayBridge(Protocol):
    """Interactive Hermes bridge contract for worker runtime dispatch."""

    def execute_interactive(self, payload: dict[str, Any]) -> ClaudeRuntimeExecutionResult:
        """Execute a Hermes task via interactive bridge transport."""


@dataclass(slots=True)
class HermesGatewayDisabledBridge:
    """Explicit disabled bridge used when interactive mode is requested."""

    reason: str = "Hermes interactive bridge is not configured on this worker."

    def execute_interactive(self, payload: dict[str, Any]) -> ClaudeRuntimeExecutionResult:
        runtime_id = str(payload.get("runtime_id") or "hermes").strip().lower() or "hermes"
        return ClaudeRuntimeExecutionResult(
            message="hermes_interactive unavailable",
            status=JobStatus.FAILED,
            error=self.reason,
            result={
                "runtime_id": runtime_id,
                "execution_mode": "interactive",
                "error_kind": "interactive_bridge_unavailable",
                "telegram_hint": (
                    "当前 worker 未启用 Hermes interactive bridge。"
                    " / Hermes interactive bridge is not enabled on this worker."
                ),
            },
        )

