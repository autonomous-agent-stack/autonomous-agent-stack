from __future__ import annotations

from pathlib import Path

from autoresearch.ga.contracts import ConnectorDescriptorRead, ConnectorType, Stability
from autoresearch.github_assistant.config import load_yaml_object


class ConnectorRegistryService:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self._payload = load_yaml_object(config_path) if config_path.exists() else {}

    def list_connectors(self) -> list[ConnectorDescriptorRead]:
        connectors = self._payload.get("connectors")
        if not isinstance(connectors, dict):
            return []
        out: list[ConnectorDescriptorRead] = []
        for connector_id, raw_value in connectors.items():
            raw = dict(raw_value or {})
            out.append(
                ConnectorDescriptorRead(
                    connector_id=str(connector_id),
                    connector_type=_connector_type(raw.get("type")),
                    stability=_stability(raw.get("stability")),
                    secret_scope=str(raw.get("secret_scope") or f"connector:{connector_id}"),
                    metadata={k: v for k, v in raw.items() if k not in {"type", "stability", "secret_scope"}},
                )
            )
        return sorted(out, key=lambda item: item.connector_id)


def _connector_type(value: object) -> ConnectorType:
    raw = str(value or "tool").strip().lower()
    aliases = {"runtime": "runtime_adapter", "workflow": "workflow", "model": "model"}
    raw = aliases.get(raw, raw)
    try:
        return ConnectorType(raw)
    except ValueError:
        return ConnectorType.TOOL_CONNECTOR


def _stability(value: object) -> Stability:
    try:
        return Stability(str(value or "experimental").strip().lower())
    except ValueError:
        return Stability.EXPERIMENTAL
