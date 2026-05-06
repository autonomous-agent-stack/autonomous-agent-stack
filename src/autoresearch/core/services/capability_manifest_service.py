from __future__ import annotations

from autoresearch.agent_protocol.capability_models import (
    CapabilityManifest,
    CapabilityRunRead,
    CapabilityRunRequest,
)
from autoresearch.agent_protocol.capability_registry import CapabilityManifestRegistry
from autoresearch.agent_protocol.runtime_models import RuntimeRunRequest
from autoresearch.core.services.runtime_adapter_registry import RuntimeAdapterServiceRegistry


class CapabilityManifestService:
    """Capability registry that keeps AAS capability contracts above runtimes."""

    def __init__(
        self,
        *,
        registry: CapabilityManifestRegistry,
        runtime_registry: RuntimeAdapterServiceRegistry,
    ) -> None:
        self._registry = registry
        self._runtime_registry = runtime_registry

    def list_manifests(self) -> list[CapabilityManifest]:
        return sorted(self._registry.load_all(), key=lambda item: item.capability_id)

    def get(self, capability_id: str) -> CapabilityManifest:
        return self._registry.load(capability_id.strip())

    def doctor(self) -> dict[str, object]:
        manifests = self.list_manifests()
        runtime_ids = set(self._runtime_registry.list_runtime_ids())
        missing_runtime = [
            item.capability_id for item in manifests if item.provided_by not in runtime_ids
        ]
        return {
            "status": "ok" if not missing_runtime else "degraded",
            "capability_count": len(manifests),
            "enabled_capability_count": len([item for item in manifests if item.enabled]),
            "missing_runtime_capabilities": missing_runtime,
        }

    def run_capability(
        self,
        capability_id: str,
        request: CapabilityRunRequest,
    ) -> CapabilityRunRead:
        manifest = self.get(capability_id)
        if not manifest.enabled:
            raise ValueError(f"capability is disabled: {capability_id}")
        prompt = request.prompt or str(request.parameters.get("prompt") or request.task_name)
        runtime_request = RuntimeRunRequest(
            runtime_id=manifest.provided_by,
            session_id=request.session_id,
            task_name=request.task_name,
            prompt=prompt,
            timeout_seconds=request.timeout_seconds,
            metadata={
                **request.metadata,
                "capability_id": manifest.capability_id,
                "capability_kind": manifest.kind,
                "risk_tier": manifest.risk_tier,
                "policy_refs": list(manifest.policy_refs),
                "actor_id": request.actor_id,
                "actor_role": request.actor_role,
                "requested_by": request.requested_by,
                "parameters": request.parameters,
            },
        )
        runtime = self._runtime_registry.get(manifest.provided_by)
        runtime_run = runtime.run(runtime_request)
        return CapabilityRunRead(
            capability_id=manifest.capability_id,
            runtime_id=manifest.provided_by,
            manifest=manifest,
            runtime_request=runtime_request,
            runtime_run=runtime_run,
        )
