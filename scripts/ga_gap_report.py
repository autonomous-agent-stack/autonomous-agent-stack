from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from autoresearch.github_assistant.config import load_yaml_object


REPORT_JSON = "ga_gap_report.json"
REPORT_MD = "ga_gap_report.md"
EVIDENCE_ROOT = Path("artifacts/ga/adapter_certification")
FURNITURE_ROOT = Path("artifacts/ga/furniture_e2e")

REQUIRED_ADAPTER_CHECKS = {
    "real_doctor",
    "session_binding",
    "real_run",
    "real_stream",
    "real_cancel",
    "real_status",
    "artifact_collection",
    "error_taxonomy",
    "policy_hook",
    "approval_hook",
    "tool_broker_enforcement",
    "model_gateway_enforcement",
    "secret_lease_enforcement",
    "session_event_mapping",
    "live_integration_test",
    "failure_drill",
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

EXPECTED_BYPASS_CHECKS = {
    "direct_env_key_access",
    "direct_model_call",
    "direct_tool_call",
    "approval_rejected_but_action_continues",
    "federation_without_lease",
    "unauthorized_package_tool_registration",
    "direct_db_mutation",
    "artifact_promotion_bypass",
}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    report = build_gap_report(repo_root)
    (repo_root / REPORT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (repo_root / REPORT_MD).write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "outputs": [REPORT_JSON, REPORT_MD]}, sort_keys=True))
    return 0


def build_gap_report(repo_root: Path) -> dict[str, Any]:
    sections = [
        _release_gate_section(repo_root),
        _bypass_section(repo_root),
        _adapter_certification_section(repo_root),
        _postgres_event_store_section(repo_root),
        _direct_path_section(repo_root),
        _v1_surface_section(repo_root),
        _furniture_e2e_section(repo_root),
    ]
    missing_total = sum(len(section["missing_checks"]) for section in sections)
    return {
        "report_id": "evergreen-os-ga-v1-gap-report",
        "generated_at": datetime.now(UTC).isoformat(),
        "status": "failed" if missing_total else "passed",
        "missing_total": missing_total,
        "sections": sections,
        "outputs": [REPORT_JSON, REPORT_MD],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Evergreen OS GA v1.0 Gap Report",
        "",
        f"- status: `{report['status']}`",
        f"- generated_at: `{report['generated_at']}`",
        f"- missing_total: `{report['missing_total']}`",
        "",
    ]
    for section in report["sections"]:
        lines.extend(
            [
                f"## {section['title']}",
                "",
                f"- status: `{section['status']}`",
                f"- missing_checks: `{len(section['missing_checks'])}`",
            ]
        )
        if section["missing_checks"]:
            lines.append("")
            for item in section["missing_checks"]:
                lines.append(f"- {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _release_gate_section(repo_root: Path) -> dict[str, Any]:
    makefile = _read(repo_root / "Makefile")
    script = _read(repo_root / "scripts/ga_release_gate.py")
    service = _read(repo_root / "src/autoresearch/core/services/release_gate.py")
    missing: list[str] = []
    if "ga-gap-report:" not in makefile:
        missing.append("make ga-gap-report target is missing")
    if "ga-release-gate:" not in makefile:
        missing.append("make ga-release-gate target is missing")
    for output in (REPORT_JSON, REPORT_MD):
        if not (repo_root / output).exists():
            missing.append(f"{output} has not been emitted yet")
    expected_markers = [
        "adapter_certification_report.json",
        "stable_adapters.lock",
        "live_evidence.json",
        "furniture_e2e",
        "bypass",
        "v1",
    ]
    for marker in expected_markers:
        if marker not in script and marker not in service:
            missing.append(f"release gate does not yet enforce {marker}")
    return _section("release_gate", "Release Gate", missing, {"script": "scripts/ga_release_gate.py"})


def _bypass_section(repo_root: Path) -> dict[str, Any]:
    script = _read(repo_root / "scripts/bypass_ga.py")
    missing: list[str] = []
    if "synthetic_denies" in script or "blocked by GA release gate policy" in script:
        missing.append("bypass-ga still contains synthetic pass results")
    for check_id in sorted(EXPECTED_BYPASS_CHECKS):
        if check_id not in script:
            missing.append(f"bypass-ga does not implement real attempt: {check_id}")
    return _section("bypass_ga", "Bypass GA", missing, {"script": "scripts/bypass_ga.py"})


def _adapter_certification_section(repo_root: Path) -> dict[str, Any]:
    payload = _yaml(repo_root / "configs/certification/adapters.yaml")
    required = set(payload.get("required_checks") or []) or REQUIRED_ADAPTER_CHECKS
    adapters = payload.get("adapters") if isinstance(payload.get("adapters"), dict) else {}
    missing: list[str] = []
    for adapter_id, raw in sorted(adapters.items()):
        item = dict(raw or {})
        explicit_missing = item.get("missing_checks")
        if explicit_missing == "all":
            missing.append(f"{adapter_id}: missing all certification checks")
        elif isinstance(explicit_missing, list) and explicit_missing:
            missing.append(f"{adapter_id}: missing checks {', '.join(sorted(map(str, explicit_missing)))}")
        passed = {str(value).strip() for value in item.get("passed_checks") or [] if str(value).strip()}
        implicit_missing = sorted(required - passed)
        if implicit_missing and not explicit_missing:
            missing.append(f"{adapter_id}: missing checks {', '.join(implicit_missing)}")
        evidence_path = repo_root / EVIDENCE_ROOT / str(adapter_id) / "live_evidence.json"
        if not evidence_path.exists():
            missing.append(f"{adapter_id}: missing {evidence_path.relative_to(repo_root)}")
    for output in ("adapter_certification_report.json", "stable_adapters.lock"):
        if not (repo_root / output).exists():
            missing.append(f"{output} has not been generated")
    return _section(
        "adapter_certification",
        "Adapter Certification",
        missing,
        {"adapter_count": len(adapters), "evidence_root": str(EVIDENCE_ROOT)},
    )


def _postgres_event_store_section(repo_root: Path) -> dict[str, Any]:
    source = _read(repo_root / "src/autoresearch/storage/postgres.py")
    deps = _read(repo_root / "src/autoresearch/api/dependencies.py")
    required_markers = [
        "class PostgresSessionEventStore",
        "transactional",
        "sequence_no",
        "idempotency_key",
        "content_hash",
        "session_event_outbox",
        "session_event_inbox_dedupe",
        "migrate",
        "rollback",
        "replay",
    ]
    missing = [f"postgres event store missing marker: {marker}" for marker in required_markers if marker not in source]
    if "PostgresSessionEventStore" not in deps:
        missing.append("production dependencies do not wire PostgresSessionEventStore")
    return _section("postgres_event_store", "PostgreSQL Event Store", missing, {})


def _direct_path_section(repo_root: Path) -> dict[str, Any]:
    findings: list[str] = []
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
    for path in sorted((repo_root / "src/autoresearch").rglob("*.py")):
        rel = path.relative_to(repo_root).as_posix()
        if rel in allowed:
            continue
        text = _read(path)
        for label, pattern in patterns.items():
            if pattern.search(text):
                findings.append(f"{label}: {rel}")
                break
    return _section(
        "direct_secret_model_tool_paths",
        "Direct Secret/Model/Tool Paths",
        findings[:200],
        {"truncated": len(findings) > 200, "finding_count": len(findings)},
    )


def _v1_surface_section(repo_root: Path) -> dict[str, Any]:
    surfaces: list[str] = []
    for path in sorted((repo_root / "src/autoresearch/api/routers").rglob("*.py")):
        text = _read(path)
        for match in re.finditer(r"APIRouter\(\s*prefix=[\"'](/api/v1[^\"']*)[\"']", text):
            surfaces.append(f"{match.group(1)} in {path.relative_to(repo_root).as_posix()}")
    compat = _yaml(repo_root / "configs/ga/v1_compat_shims.yaml")
    listed = set(compat.get("compat_shims") or [])
    missing = [surface for surface in surfaces if surface.split(" in ", 1)[0] not in listed]
    return _section(
        "v1_primary_surfaces",
        "V1 Primary Surfaces",
        missing,
        {"surface_count": len(surfaces), "compat_shims": sorted(listed)},
    )


def _furniture_e2e_section(repo_root: Path) -> dict[str, Any]:
    makefile = _read(repo_root / "Makefile")
    missing: list[str] = []
    if "furniture-e2e:" not in makefile:
        missing.append("make furniture-e2e target is missing")
    for artifact in sorted(REQUIRED_FURNITURE_ARTIFACTS):
        if not (repo_root / FURNITURE_ROOT / artifact).exists():
            missing.append(f"missing furniture artifact: {FURNITURE_ROOT / artifact}")
    return _section("furniture_e2e", "Furniture E2E", missing, {"artifact_root": str(FURNITURE_ROOT)})


def _section(section_id: str, title: str, missing: list[str], evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": section_id,
        "title": title,
        "status": "failed" if missing else "passed",
        "missing_checks": missing,
        "evidence": evidence,
    }


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_yaml_object(path)
    return payload if isinstance(payload, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
