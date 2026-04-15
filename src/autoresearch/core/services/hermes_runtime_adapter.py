from __future__ import annotations

from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_runtime_adapter import OpenClawRuntimeAdapterService


class HermesRuntimeAdapterService(OpenClawRuntimeAdapterService):
    """Hermes runtime adapter behind a stable runtime contract.

    Hermes-specific protocol changes should be absorbed in this adapter layer so
    AAS callers keep using the same create_session/run/stream/cancel/status surface.
    """

    def __init__(
        self,
        openclaw_service: OpenClawCompatService,
        claude_service: ClaudeAgentService,
    ) -> None:
        super().__init__(
            openclaw_service=openclaw_service,
            claude_service=claude_service,
            runtime_id="hermes",
            metadata_namespace="hermes",
        )
