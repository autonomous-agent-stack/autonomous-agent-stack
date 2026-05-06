from __future__ import annotations

from pathlib import Path
from typing import Any

from autoresearch.ga.contracts import CertificationStatus, GAStatusRead, Stability
from autoresearch.github_assistant.config import load_yaml_object


class AdapterCertificationRegistry:
    """Read and enforce the machine-readable adapter certification matrix."""

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self._payload = load_yaml_object(config_path) if config_path.exists() else {}

    @property
    def required_checks(self) -> list[str]:
        return [str(item).strip() for item in self._payload.get("required_checks") or [] if str(item).strip()]

    def list_statuses(self) -> list[GAStatusRead]:
        adapters = self._adapters()
        return [self.status_for(adapter_id) for adapter_id in sorted(adapters)]

    def status_for(self, adapter_id: str) -> GAStatusRead:
        raw = dict(self._adapters().get(adapter_id) or {})
        stability = _stability(raw.get("stability"))
        missing = self.missing_checks(adapter_id)
        certification = CertificationStatus.CERTIFIED if not missing else CertificationStatus.PARTIAL
        if stability == Stability.STABLE and missing:
            certification = CertificationStatus.MISSING
        return GAStatusRead(
            object_id=adapter_id,
            object_type="adapter",
            stability=stability,
            certification_status=certification,
            certification_profile="adapter-certification-matrix",
            live_test_command=_optional_string(raw.get("live_test_command")),
            missing_checks=missing,
        )

    def missing_checks(self, adapter_id: str) -> list[str]:
        raw = dict(self._adapters().get(adapter_id) or {})
        explicit_missing = raw.get("missing_checks")
        if explicit_missing == "all":
            return self.required_checks
        if isinstance(explicit_missing, list):
            return sorted({str(item).strip() for item in explicit_missing if str(item).strip()})
        passed = {str(item).strip() for item in raw.get("passed_checks") or [] if str(item).strip()}
        return [item for item in self.required_checks if item not in passed]

    def stable_violations(self) -> dict[str, list[str]]:
        violations: dict[str, list[str]] = {}
        for adapter_id in self._adapters():
            status = self.status_for(adapter_id)
            if status.stability == Stability.STABLE and status.missing_checks:
                violations[adapter_id] = status.missing_checks
        return violations

    def _adapters(self) -> dict[str, Any]:
        adapters = self._payload.get("adapters")
        return adapters if isinstance(adapters, dict) else {}


def _stability(value: object) -> Stability:
    try:
        return Stability(str(value or "experimental").strip().lower())
    except ValueError:
        return Stability.EXPERIMENTAL


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
