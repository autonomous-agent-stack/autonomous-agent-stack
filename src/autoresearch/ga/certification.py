from __future__ import annotations

from pathlib import Path
from typing import Any

from autoresearch.ga.contracts import CertificationStatus, GAStatusRead, Stability
from autoresearch.github_assistant.config import load_yaml_object


class AdapterCertificationRegistry:
    """Read and enforce the machine-readable adapter certification matrix."""

    def __init__(
        self,
        config_path: Path,
        *,
        report_path: Path | None = None,
        evidence_root: Path | None = None,
    ) -> None:
        self.config_path = config_path
        self._payload = load_yaml_object(config_path) if config_path.exists() else {}
        self._report_path = report_path or config_path.parents[2] / "adapter_certification_report.json"
        self._evidence_root = evidence_root or config_path.parents[2] / "artifacts" / "ga" / "adapter_certification"
        self._report = load_yaml_object(self._report_path) if self._report_path.exists() else {}

    @property
    def required_checks(self) -> list[str]:
        return [str(item).strip() for item in self._payload.get("required_checks") or [] if str(item).strip()]

    def list_statuses(self) -> list[GAStatusRead]:
        adapters = self._adapters()
        return [self.status_for(adapter_id) for adapter_id in sorted(adapters)]

    def status_for(self, adapter_id: str) -> GAStatusRead:
        raw = dict(self._adapters().get(adapter_id) or {})
        intent_stability = _stability(raw.get("stability"))
        missing = self.missing_checks(adapter_id)
        evidence_path = self._evidence_root / adapter_id / "live_evidence.json"
        report_item = self._report_item(adapter_id)
        derived_stability = _stability(report_item.get("stability")) if report_item else Stability.EXPERIMENTAL
        certification = _certification_status(report_item.get("certification_status")) if report_item else (
            CertificationStatus.PARTIAL if missing else CertificationStatus.MISSING
        )
        blocked_reason = _optional_string(report_item.get("blocked_reason")) if report_item else None
        if not report_item and not evidence_path.exists():
            certification = CertificationStatus.BLOCKED
            blocked_reason = "missing live_evidence.json"
        return GAStatusRead(
            object_id=adapter_id,
            object_type="adapter",
            stability=derived_stability,
            intent_stability=intent_stability,
            certification_status=certification,
            certification_profile="adapter-certification-matrix",
            live_test_command=_optional_string(raw.get("live_test_command")),
            missing_checks=missing,
            evidence_path=str(evidence_path),
            blocked_reason=blocked_reason,
        )

    def missing_checks(self, adapter_id: str) -> list[str]:
        report_item = self._report_item(adapter_id)
        if report_item:
            raw_missing = report_item.get("missing_checks")
            if isinstance(raw_missing, list):
                return sorted({str(item).strip() for item in raw_missing if str(item).strip()})
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
            if status.intent_stability == Stability.STABLE and status.stability != Stability.STABLE:
                violations[adapter_id] = status.missing_checks or [status.blocked_reason or "stable intent lacks certification evidence"]
            elif status.stability == Stability.STABLE and status.missing_checks:
                violations[adapter_id] = status.missing_checks
        return violations

    def _report_item(self, adapter_id: str) -> dict[str, Any]:
        adapters = self._report.get("adapters") if isinstance(self._report.get("adapters"), dict) else {}
        item = adapters.get(adapter_id) if isinstance(adapters, dict) else None
        return dict(item or {}) if isinstance(item, dict) else {}

    def _adapters(self) -> dict[str, Any]:
        adapters = self._payload.get("adapters")
        return adapters if isinstance(adapters, dict) else {}


def _stability(value: object) -> Stability:
    try:
        return Stability(str(value or "experimental").strip().lower())
    except ValueError:
        return Stability.EXPERIMENTAL


def _certification_status(value: object) -> CertificationStatus:
    try:
        return CertificationStatus(str(value or "missing").strip().lower())
    except ValueError:
        return CertificationStatus.MISSING


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
