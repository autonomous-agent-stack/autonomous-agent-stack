from __future__ import annotations

from collections.abc import Callable, Mapping

from autoresearch.agent_protocol.runtime_registry import RuntimeAdapterRegistry
from autoresearch.core.services.runtime_adapter_contract import RuntimeAdapterContract


class RuntimeAdapterServiceRegistry:
    """Unified runtime adapter selector by runtime_id."""

    def __init__(
        self,
        *,
        manifest_registry: RuntimeAdapterRegistry,
        factories: Mapping[str, Callable[[], RuntimeAdapterContract]],
    ) -> None:
        self._manifest_registry = manifest_registry
        self._factories = dict(factories)
        self._instances: dict[str, RuntimeAdapterContract] = {}

    def get(self, runtime_id: str) -> RuntimeAdapterContract:
        normalized_runtime_id = runtime_id.strip().lower()
        if not normalized_runtime_id:
            raise KeyError("runtime_id is required")

        try:
            manifest = self._manifest_registry.load(normalized_runtime_id)
        except FileNotFoundError as exc:
            raise KeyError(f"runtime adapter manifest not found: {normalized_runtime_id}") from exc

        factory = self._factories.get(manifest.id)
        if factory is None:
            raise KeyError(f"runtime adapter is not wired: {manifest.id}")

        if manifest.id not in self._instances:
            self._instances[manifest.id] = factory()
        return self._instances[manifest.id]

    def list_runtime_ids(self) -> list[str]:
        return sorted(self._factories.keys())
