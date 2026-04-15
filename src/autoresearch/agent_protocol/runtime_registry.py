from __future__ import annotations

from pathlib import Path

from autoresearch.agent_protocol.registry import _load_yaml_like
from autoresearch.agent_protocol.runtime_models import RuntimeAdapterManifest


class RuntimeAdapterRegistry:
    def __init__(self, manifests_dir: Path) -> None:
        self._manifests_dir = manifests_dir

    def load(self, runtime_id: str) -> RuntimeAdapterManifest:
        manifest_path = self._manifests_dir / f"{runtime_id}.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"runtime manifest not found: {manifest_path}")
        payload = _load_yaml_like(manifest_path)
        return RuntimeAdapterManifest.model_validate(payload)
