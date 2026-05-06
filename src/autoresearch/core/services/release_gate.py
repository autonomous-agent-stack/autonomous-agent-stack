from __future__ import annotations

from pathlib import Path
from autoresearch.ga.certification import AdapterCertificationRegistry
from autoresearch.ga.contracts import ReleaseGateCheckRead, ReleaseGateReportRead
from autoresearch.github_assistant.config import load_yaml_object


class ReleaseGateService:
    def __init__(self, *, repo_root: Path) -> None:
        self.repo_root = repo_root

    def run(self) -> ReleaseGateReportRead:
        checks = [
            self._check_required_docs(),
            self._check_adapter_certification(),
            self._check_storage_profiles(),
            self._check_runtime_isolation_profile(),
            self._check_connector_registry(),
        ]
        status = "failed" if any(check.status == "failed" for check in checks) else "passed"
        return ReleaseGateReportRead(status=status, checks=checks)

    def _check_required_docs(self) -> ReleaseGateCheckRead:
        required = [
            "docs/ga-definition.md",
            "docs/ga-prohibitions.md",
            "docs/runtime-isolation.md",
            "docs/certification/adapter-certification-matrix.md",
        ]
        missing = [path for path in required if not (self.repo_root / path).exists()]
        return _check(
            "ga.required_docs",
            not missing,
            "GA blocking docs are present." if not missing else f"Missing GA docs: {', '.join(missing)}",
            {"missing": missing},
        )

    def _check_adapter_certification(self) -> ReleaseGateCheckRead:
        registry = AdapterCertificationRegistry(self.repo_root / "configs/certification/adapters.yaml")
        violations = registry.stable_violations()
        statuses = [item.model_dump(mode="json") for item in registry.list_statuses()]
        return _check(
            "ga.adapter_certification",
            not violations,
            "No uncertified adapter is marked stable."
            if not violations
            else f"Stable adapter certification violations: {violations}",
            {"violations": violations, "statuses": statuses},
        )

    def _check_storage_profiles(self) -> ReleaseGateCheckRead:
        payload = _load(self.repo_root / "configs/ga/storage_profiles.yaml")
        production = ((payload.get("profiles") or {}).get("production") or {})
        required = set(production.get("required_features") or [])
        expected = {
            "transactional_event_append",
            "sequence_no_allocation",
            "idempotency_key_unique_constraint",
            "content_hash_verification",
            "event_replay",
            "backup_restore",
            "migration_rollback",
            "outbox_table",
            "inbox_dedupe_table",
        }
        ok = production.get("driver") == "postgresql" and bool(production.get("allowed_for_ga")) and expected <= required
        return _check(
            "ga.storage_profiles",
            ok,
            "Production profile is PostgreSQL with required event-store features."
            if ok
            else "Production profile must be PostgreSQL and include all event-store GA features.",
            {"production": production, "missing_features": sorted(expected - required)},
        )

    def _check_runtime_isolation_profile(self) -> ReleaseGateCheckRead:
        payload = _load(self.repo_root / "configs/ga/runtime_isolation.yaml")
        profile = ((payload.get("profiles") or {}).get("default_runtime_sandbox") or {})
        required_true = [
            "filesystem_sandbox",
            "process_isolation",
            "artifact_output_directory_only",
            "deny_dotenv",
            "deny_host_home",
        ]
        missing = [key for key in required_true if profile.get(key) is not True]
        ok = not missing and profile.get("secret_injection") == "lease_only"
        return _check(
            "ga.runtime_isolation",
            ok,
            "Default runtime isolation profile is blocking by default."
            if ok
            else f"Runtime isolation profile is missing required gates: {missing}",
            {"profile": profile},
        )

    def _check_connector_registry(self) -> ReleaseGateCheckRead:
        payload = _load(self.repo_root / "configs/connectors/registry.yaml")
        connectors = payload.get("connectors") or {}
        missing_secret_scope = [
            connector_id for connector_id, raw in connectors.items() if not dict(raw or {}).get("secret_scope")
        ]
        stable = [
            connector_id
            for connector_id, raw in connectors.items()
            if str(dict(raw or {}).get("stability") or "").strip().lower() == "stable"
        ]
        ok = not missing_secret_scope and not stable
        return _check(
            "ga.connector_registry",
            ok,
            "Connectors are registered with secret scopes and no uncertified stable connector."
            if ok
            else "Connector registry has missing scopes or uncertified stable connectors.",
            {"missing_secret_scope": missing_secret_scope, "stable_connectors": stable},
        )


def _load(path: Path) -> dict:
    return load_yaml_object(path) if path.exists() else {}


def _check(check_id: str, ok: bool, message: str, evidence: dict) -> ReleaseGateCheckRead:
    return ReleaseGateCheckRead(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        evidence=evidence,
    )
