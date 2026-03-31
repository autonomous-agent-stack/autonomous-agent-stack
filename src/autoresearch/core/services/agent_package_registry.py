from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autoresearch.shared.housekeeper_contract import AgentPackageRecordRead, HousekeeperBackendKind


class AgentPackageRegistryService:
    """Load agent package manifests from the TypeScript control-plane tree."""

    def __init__(self, *, repo_root: Path) -> None:
        self._repo_root = repo_root.resolve()
        self._package_root = self._repo_root / "agent-control-plane" / "packages" / "agent-packages"

    def list_packages(self) -> list[AgentPackageRecordRead]:
        packages: list[AgentPackageRecordRead] = []
        if not self._package_root.is_dir():
            return packages
        for manifest_path in sorted(self._package_root.glob("*/manifest.json")):
            record = self._load_manifest(manifest_path)
            if record is not None:
                packages.append(record)
        return packages

    def get_package(self, package_id: str) -> AgentPackageRecordRead | None:
        normalized = package_id.strip()
        if not normalized:
            return None
        for record in self.list_packages():
            if record.package_id == normalized:
                return record
        return None

    def find_by_backend(self, backend_kind: HousekeeperBackendKind) -> list[AgentPackageRecordRead]:
        return [item for item in self.list_packages() if item.execution_backend is backend_kind]

    def _load_manifest(self, path: Path) -> AgentPackageRecordRead | None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not self._is_valid_manifest(payload):
            return None
        governance = payload.get("governance") or {}
        approval_rules = governance.get("approval_rules") or {}
        try:
            backend = HousekeeperBackendKind(str(payload["execution_backend"]).strip())
        except ValueError:
            return None
        return AgentPackageRecordRead(
            package_id=str(payload["id"]).strip(),
            name=str(payload["name"]).strip(),
            description=str(payload.get("description", "")).strip(),
            version=str(payload["version"]).strip(),
            manifest_path=str(path.resolve()),
            execution_backend=backend,
            supported_worker_types=self._string_list(payload.get("supported_worker_types")),
            required_capabilities=dict(payload.get("required_capabilities") or {}),
            risk_level=str(governance.get("risk_level", "medium")).strip() or "medium",
            requires_approval=bool(approval_rules.get("requires_approval_for_write", False)),
            raw_manifest=payload,
        )

    def _is_valid_manifest(self, payload: dict[str, Any]) -> bool:
        required = (
            "id",
            "name",
            "version",
            "input_schema",
            "output_schema",
            "required_capabilities",
            "supported_worker_types",
            "governance",
            "failure_handling",
            "execution",
            "execution_backend",
        )
        if not all(key in payload for key in required):
            return False
        if not isinstance(payload.get("supported_worker_types"), list):
            return False
        if not isinstance(payload.get("required_capabilities"), dict):
            return False
        governance = payload.get("governance")
        if not isinstance(governance, dict):
            return False
        approval_rules = governance.get("approval_rules")
        if not isinstance(approval_rules, dict):
            return False
        execution_backend = str(payload.get("execution_backend", "")).strip()
        return execution_backend in {item.value for item in HousekeeperBackendKind}

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        items: list[str] = []
        for item in value:
            candidate = str(item).strip()
            if candidate:
                items.append(candidate)
        return items
