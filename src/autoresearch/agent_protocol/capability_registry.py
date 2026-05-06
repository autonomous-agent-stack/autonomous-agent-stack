from __future__ import annotations

from pathlib import Path

from autoresearch.agent_protocol.capability_models import CapabilityManifest
from autoresearch.agent_protocol.registry import _load_yaml_like


class CapabilityManifestRegistry:
    def __init__(self, manifests_dir: Path) -> None:
        self._manifests_dir = manifests_dir

    def load(self, capability_id: str) -> CapabilityManifest:
        manifest_path = self._manifests_dir / f"{capability_id}.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"capability manifest not found: {manifest_path}")
        payload = _load_yaml_like(manifest_path)
        return CapabilityManifest.model_validate(payload)

    def load_all(self) -> list[CapabilityManifest]:
        if not self._manifests_dir.exists():
            return []
        manifests: list[CapabilityManifest] = []
        for path in sorted(self._manifests_dir.glob("*.yaml")):
            payload = _load_yaml_like(path)
            manifests.append(CapabilityManifest.model_validate(payload))
        return manifests
