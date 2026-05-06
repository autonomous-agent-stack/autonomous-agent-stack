from __future__ import annotations

from collections.abc import Callable, Mapping
from importlib.util import find_spec

from autoresearch.agent_protocol.runtime_registry import RuntimeAdapterRegistry
from autoresearch.agent_protocol.runtime_models import RuntimeAdapterManifest, RuntimeDoctorRead
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
        manifest_ids = [item.id for item in self.list_manifests()]
        return sorted(set(manifest_ids) | set(self._factories.keys()))

    def list_manifests(self) -> list[RuntimeAdapterManifest]:
        if hasattr(self._manifest_registry, "load_all"):
            return self._manifest_registry.load_all()
        return []

    def manifest(self, runtime_id: str) -> RuntimeAdapterManifest:
        return self._manifest_registry.load(runtime_id.strip().lower())

    def doctor(self, runtime_id: str) -> RuntimeDoctorRead:
        manifest = self.manifest(runtime_id)
        if not manifest.enabled:
            return RuntimeDoctorRead(
                runtime_id=manifest.id,
                status="disabled",
                detail="runtime adapter is disabled by manifest",
                manifest=manifest,
            )
        missing = [
            dependency
            for dependency in manifest.optional_dependencies
            if find_spec(dependency) is None
        ]
        if manifest.id not in self._factories:
            return RuntimeDoctorRead(
                runtime_id=manifest.id,
                status="failed",
                detail="runtime manifest exists but no service factory is wired",
                manifest=manifest,
                missing_dependencies=missing,
            )
        adapter = self.get(manifest.id)
        base = adapter.doctor()
        status = base.status
        detail = base.detail
        if missing and status == "ok":
            status = "degraded"
            detail = "runtime adapter is wired; optional dependencies are missing"
        return base.model_copy(
            update={
                "runtime_id": manifest.id,
                "status": status,
                "detail": detail,
                "manifest": manifest,
                "missing_dependencies": sorted(set(base.missing_dependencies + missing)),
            }
        )

    def doctor_all(self) -> list[RuntimeDoctorRead]:
        return [self.doctor(item.id) for item in self.list_manifests()]
