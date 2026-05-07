from __future__ import annotations

import json
import re
import importlib.util
from pathlib import Path
from typing import Any

from autoresearch.ga.certification import AdapterCertificationRegistry
from autoresearch.ga.contracts import ReleaseGateCheckRead, ReleaseGateReportRead
from autoresearch.github_assistant.config import load_yaml_object


REQUIRED_BYPASS_CHECKS = {
    "direct_env_key_access",
    "direct_model_call",
    "direct_tool_call",
    "approval_rejected_but_action_continues",
    "federation_without_lease",
    "unauthorized_package_tool_registration",
    "direct_db_mutation",
    "artifact_promotion_bypass",
}

REQUIRED_FURNITURE_ARTIFACTS = {
    "quote.pdf",
    "quote.xlsx",
    "design_image.png",
    "design_prompt_audit.json",
    "approval_record.json",
    "audit_timeline.json",
    "cost_ledger.json",
    "commission_projection.json",
    "session_facts_replay.json",
}


class ReleaseGateService:
    def __init__(self, *, repo_root: Path) -> None:
        self.repo_root = repo_root

    def run(self) -> ReleaseGateReportRead:
        checks = [
            self._check_required_docs(),
            self._check_gap_report_outputs(),
            self._check_adapter_certification(),
            self._check_bypass_ga(),
            self._check_storage_profiles(),
            self._check_postgres_event_store(),
            self._check_runtime_isolation_profile(),
            self._check_connector_registry(),
            self._check_v1_compat_shims(),
            self._check_direct_secret_model_tool_paths(),
            self._check_furniture_e2e_artifacts(),
            self._check_external_write_default(),
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

    def _check_gap_report_outputs(self) -> ReleaseGateCheckRead:
        missing = [path for path in ("ga_gap_report.json", "ga_gap_report.md") if not (self.repo_root / path).exists()]
        payload = _load_json(self.repo_root / "ga_gap_report.json")
        report_status = str(payload.get("status") or "missing")
        missing_total = int(payload.get("missing_total") or 0) if payload else 0
        ok = not missing and report_status == "passed" and missing_total == 0
        return _check(
            "ga.gap_report",
            ok,
            "GA gap report exists and has no missing checks."
            if ok
            else "GA gap report must be emitted and pass before the release gate can pass.",
            {"missing_outputs": missing, "report_status": report_status, "missing_total": missing_total},
        )

    def _check_adapter_certification(self) -> ReleaseGateCheckRead:
        config_path = self.repo_root / "configs/certification/adapters.yaml"
        registry = AdapterCertificationRegistry(config_path)
        config = _load(config_path)
        adapters = config.get("adapters") if isinstance(config.get("adapters"), dict) else {}
        adapter_ids = sorted(str(adapter_id) for adapter_id in adapters)
        report = _load_json(self.repo_root / "adapter_certification_report.json")
        report_adapters = report.get("adapters") if isinstance(report.get("adapters"), dict) else {}
        locked = _load_stable_lock(self.repo_root / "stable_adapters.lock")
        violations = registry.stable_violations()
        missing: list[str] = []
        if not report:
            missing.append("adapter_certification_report.json is missing or invalid")
        if not (self.repo_root / "stable_adapters.lock").exists():
            missing.append("stable_adapters.lock is missing")
        blocked_adapters = [str(item) for item in report.get("blocked_adapters") or []]
        if blocked_adapters:
            missing.append(f"blocked adapters under full-adapter scope: {', '.join(sorted(blocked_adapters))}")
        for adapter_id in adapter_ids:
            item = report_adapters.get(adapter_id) if isinstance(report_adapters, dict) else None
            if not isinstance(item, dict):
                missing.append(f"{adapter_id}: missing certification report item")
                continue
            intent = str(item.get("intent_stability") or "experimental")
            derived = str(item.get("stability") or "experimental")
            status = str(item.get("certification_status") or "missing")
            if intent == "stable" and derived != "stable":
                missing.append(f"{adapter_id}: config stable intent lacks certification evidence")
            if derived != "stable" or status != "certified":
                missing.append(f"{adapter_id}: not certified stable")
            if item.get("live_evidence_present") is not True:
                missing.append(f"{adapter_id}: missing live_evidence.json")
            if item.get("blocked_reason"):
                missing.append(f"{adapter_id}: blocked - {item['blocked_reason']}")
            if item.get("missing_checks"):
                missing.append(f"{adapter_id}: missing checks {', '.join(map(str, item['missing_checks']))}")
        report_stable = {str(item) for item in report.get("stable_adapters") or []}
        if set(locked) != report_stable:
            missing.append("stable_adapters.lock does not match certification report stable adapters")
        if report_stable != set(adapter_ids):
            missing.append("full-adapter scope requires every configured adapter to be certified stable")
        statuses = [item.model_dump(mode="json") for item in registry.list_statuses()]
        return _check(
            "ga.adapter_certification",
            not violations and not missing,
            "All configured adapters are certified stable from live evidence."
            if not violations and not missing
            else "Adapter certification is incomplete or blocked under full-adapter scope.",
            {"violations": violations, "missing": missing, "statuses": statuses},
        )

    def _check_bypass_ga(self) -> ReleaseGateCheckRead:
        try:
            script_path = self.repo_root / "scripts/bypass_ga.py"
            spec = importlib.util.spec_from_file_location("aas_bypass_ga", script_path)
            if spec is None or spec.loader is None:
                raise RuntimeError("cannot load scripts/bypass_ga.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            run_bypass_checks = module.run_bypass_checks
            results = run_bypass_checks(self.repo_root)
        except Exception as exc:
            return _check(
                "ga.bypass_ga",
                False,
                "bypass-ga runner failed.",
                {"error": f"{type(exc).__name__}: {exc}"},
            )
        seen = {str(item.get("check")) for item in results}
        failed = [
            item
            for item in results
            if item.get("status") != "passed" or item.get("synthetic") is True
        ]
        missing = sorted(REQUIRED_BYPASS_CHECKS - seen)
        ok = not failed and not missing
        return _check(
            "ga.bypass_ga",
            ok,
            "bypass-ga performed real bypass attempts and all were blocked."
            if ok
            else "bypass-ga must block real bypass attempts without synthetic passes.",
            {"failed": failed, "missing_checks": missing, "results": results},
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

    def _check_postgres_event_store(self) -> ReleaseGateCheckRead:
        source = _read(self.repo_root / "src/autoresearch/storage/postgres.py")
        dependencies = _read(self.repo_root / "src/autoresearch/api/dependencies.py")
        markers = [
            "class PostgresSessionEventStore",
            "transactional",
            "session_event_sequences",
            "sequence_no",
            "idempotency_key",
            "content_hash",
            "verify_event_hash",
            "session_event_outbox",
            "session_event_inbox_dedupe",
            "def migrate",
            "def rollback",
            "def replay",
            "record_inbox",
            "backup_manifest",
            "restore_manifest",
        ]
        missing = [marker for marker in markers if marker not in source]
        if "PostgresSessionEventStore(postgres_dsn)" not in dependencies:
            missing.append("production dependency wiring")
        if "AUTORESEARCH_SESSION_EVENT_STORE" not in dependencies:
            missing.append("local/dev SQLite event-store selector")
        return _check(
            "ga.postgres_event_store",
            not missing,
            "PostgreSQL production SessionEvent store is implemented and wired."
            if not missing
            else "PostgreSQL production SessionEvent store is incomplete.",
            {"missing_markers": missing},
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

    def _check_v1_compat_shims(self) -> ReleaseGateCheckRead:
        router_root = self.repo_root / "src/autoresearch/api/routers"
        surfaces: list[str] = []
        for path in (sorted(router_root.rglob("*.py")) if router_root.exists() else []):
            text = _read(path)
            for match in re.finditer(r"APIRouter\(\s*prefix=[\"'](/api/v1[^\"']*)[\"']", text):
                surfaces.append(match.group(1))
        compat = _load(self.repo_root / "configs/ga/v1_compat_shims.yaml")
        shims = compat.get("compat_shims") if isinstance(compat.get("compat_shims"), dict) else {}
        listed = {str(item).strip() for item in shims if str(item).strip()}
        missing = sorted(set(surfaces) - listed)
        invalid: list[str] = []
        for route, raw in sorted(shims.items()):
            metadata = raw if isinstance(raw, dict) else {}
            for field in ("successor", "owner", "sunset_policy"):
                if not str(metadata.get(field) or "").strip():
                    invalid.append(f"{route}: missing {field}")
        ok = not missing and not invalid
        return _check(
            "ga.v1_compat_shims",
            ok,
            "All /api/v1 surfaces are declared compatibility shims."
            if ok
            else "New primary capability must not live under /api/v1.",
            {"surfaces": sorted(set(surfaces)), "missing_compat_shims": missing, "invalid_shims": invalid},
        )

    def _check_direct_secret_model_tool_paths(self) -> ReleaseGateCheckRead:
        findings = _direct_path_findings(self.repo_root)
        return _check(
            "ga.direct_secret_model_tool_paths",
            not findings,
            "No uncontrolled direct secret, model, or tool paths were found outside gateways."
            if not findings
            else "Direct secret/model/tool paths must be routed through Secret Vault, Model Gateway, or Tool Broker.",
            {"findings": findings[:200], "finding_count": len(findings), "truncated": len(findings) > 200},
        )

    def _check_furniture_e2e_artifacts(self) -> ReleaseGateCheckRead:
        root = self.repo_root / "artifacts/ga/furniture_e2e"
        missing = [name for name in sorted(REQUIRED_FURNITURE_ARTIFACTS) if not (root / name).exists()]
        invalid: list[str] = []
        if not missing:
            if not (root / "quote.pdf").read_bytes().startswith(b"%PDF-"):
                invalid.append("quote.pdf is not a PDF")
            if not (root / "quote.xlsx").read_bytes().startswith(b"PK"):
                invalid.append("quote.xlsx is not an XLSX archive")
            if not (root / "design_image.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
                invalid.append("design_image.png is not a PNG")
            approval = _load_json(root / "approval_record.json")
            if (((approval.get("denied_path") or {}).get("blocked")) is not True):
                invalid.append("approval-denied path did not block")
            approved = approval.get("approved_path") if isinstance(approval.get("approved_path"), dict) else {}
            if approved.get("write_status") != "succeeded" or approved.get("dry_run") is not True:
                invalid.append("approval-approved path did not produce dry-run write")
            design = _load_json(root / "design_prompt_audit.json")
            if design.get("pii_redaction_verified") is not True:
                invalid.append("design prompt PII redaction not verified")
            replay = _load_json(root / "session_facts_replay.json")
            if replay.get("content_hash_verified") is not True:
                invalid.append("session facts replay content hashes not verified")
        ok = not missing and not invalid
        return _check(
            "ga.furniture_e2e",
            ok,
            "Furniture E2E artifacts exist and validate denied/approved paths."
            if ok
            else "Furniture E2E artifacts are missing or invalid.",
            {"artifact_root": str(root.relative_to(self.repo_root)), "missing": missing, "invalid": invalid},
        )

    def _check_external_write_default(self) -> ReleaseGateCheckRead:
        source = _read(self.repo_root / "src/autoresearch/core/services/governed_mcp.py")
        markers = [
            "EXTERNAL_WRITE_LIVE",
            "live_credentials",
            "policy_decision_id",
            "recipient_allowlist",
            "audit_timeline_id",
            "session_facts_id",
            '"dry_run"',
        ]
        missing = [marker for marker in markers if marker not in source]
        return _check(
            "ga.external_write_dry_run",
            not missing,
            "External writes are dry-run by default with live-write preconditions."
            if not missing
            else "External write dry-run/live gate is incomplete.",
            {"missing_markers": missing},
        )


def _load(path: Path) -> dict:
    return load_yaml_object(path) if path.exists() else {}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _load_stable_lock(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _direct_path_findings(repo_root: Path) -> list[str]:
    patterns = {
        "direct model key/env access": re.compile(r"os\.getenv\([\"'](?:OPENAI|ANTHROPIC|GOOGLE).*?(?:API_KEY|TOKEN)", re.I),
        "direct model client": re.compile(r"\b(?:AsyncAnthropic|OpenAIBackend|GLMBackend|ClaudeBackend)\b"),
        "direct env copy into runtime": re.compile(r"os\.environ\.copy\(\)"),
        "direct tool network call": re.compile(r"httpx\.(?:Client|AsyncClient|post|get)\("),
    }
    allowed = {
        "src/autoresearch/core/services/model_gateway.py",
        "src/autoresearch/core/services/secret_vault.py",
        "src/autoresearch/core/services/governed_mcp.py",
        "src/autoresearch/core/services/butler_tool_broker.py",
        "src/autoresearch/core/services/release_gate.py",
    }
    findings: list[str] = []
    source_root = repo_root / "src/autoresearch"
    for path in (sorted(source_root.rglob("*.py")) if source_root.exists() else []):
        rel = path.relative_to(repo_root).as_posix()
        if rel in allowed:
            continue
        text = _read(path)
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append(f"{label}: {rel}")
                break
    return findings


def _check(check_id: str, ok: bool, message: str, evidence: dict) -> ReleaseGateCheckRead:
    return ReleaseGateCheckRead(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        evidence=evidence,
    )
