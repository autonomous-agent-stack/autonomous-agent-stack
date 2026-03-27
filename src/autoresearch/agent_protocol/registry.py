from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autoresearch.agent_protocol.models import AgentManifest


class AgentRegistry:
    def __init__(self, manifests_dir: Path) -> None:
        self._manifests_dir = manifests_dir

    def load(self, agent_id: str) -> AgentManifest:
        manifest_path = self._manifests_dir / f"{agent_id}.yaml"
        if not manifest_path.exists():
            raise FileNotFoundError(f"agent manifest not found: {manifest_path}")
        payload = _load_yaml_like(manifest_path)
        return AgentManifest.model_validate(payload)


def _load_yaml_like(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        raise ValueError(f"empty manifest: {path}")

    # YAML 1.2 is a superset of JSON. Prefer JSON-formatted YAML for zero dependency.
    try:
        loaded = json.loads(stripped)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ValueError(
                f"manifest {path} is not JSON and PyYAML is unavailable; "
                "use JSON-formatted YAML content"
            ) from exc
        loaded = yaml.safe_load(stripped)

    if not isinstance(loaded, dict):
        raise ValueError(f"invalid manifest payload in {path}; expected object")
    return loaded
