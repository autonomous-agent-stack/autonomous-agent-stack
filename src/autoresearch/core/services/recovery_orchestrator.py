from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Literal

from autoresearch.core.services.butler_dispatch import ButlerDoctorCheck


RecoveryFailureKind = Literal[
    "dependency_missing",
    "auth_required",
    "permission_required",
    "contract_error",
    "runtime_unavailable",
    "needs_user_decision",
    "unknown_complex",
]


_RECOVERABLE_FAILURE_KINDS = {
    "dependency_missing",
    "auth_required",
    "permission_required",
    "runtime_unavailable",
    "needs_user_decision",
}

_REQUIRED_CAPABILITY_RECOVERY_CONTRACTS = {
    "source_collect",
    "youtube_autoflow",
    "github_assistant",
    "excel_audit",
    "content_kb",
    "hermes_openclaw",
}

_IMPLEMENTED_RECOVERY_CONTRACTS: dict[str, dict[str, Any]] = {
    "source_collect": {
        "doctor": "xreach auth/setup preflight",
        "dependencies": ["xreach"],
        "offline_smoke": "fixture_path",
        "repair_probes": ["AUTORESEARCH_XREACH_BIN", "PATH", "known Homebrew paths"],
        "hermes_prompt": "xreach setup/auth recovery advisor",
        "user_actions": [
            "install_xreach",
            "set_AUTORESEARCH_XREACH_BIN",
            "restart_worker",
            "fixture_smoke",
            "resume",
            "cancel",
        ],
        "retry_policy": "requeue_original_run_after_user_fix",
    }
}

_AGENT_LIFECYCLE_VALUES = {"candidate", "shadow", "active", "merge", "retire"}


@dataclass(slots=True)
class ButlerRecoveryOrchestrator:
    """Shared recovery/governance doctor for Butler-routed capabilities.

    This service intentionally does not execute repairs. Workers still own
    deterministic local probes, Hermes owns advisory diagnosis, and AAS owns
    policy/audit state.
    """

    repo_root: Path

    def doctor_checks(self) -> list[ButlerDoctorCheck]:
        return [
            self.capability_recovery_contract_check(),
            self.agent_governance_check(),
        ]

    def capability_recovery_contract_check(self) -> ButlerDoctorCheck:
        missing = sorted(_REQUIRED_CAPABILITY_RECOVERY_CONTRACTS - set(_IMPLEMENTED_RECOVERY_CONTRACTS))
        status = "ok" if not missing else "degraded"
        detail = (
            "All key capabilities declare recovery contracts"
            if not missing
            else "Some key capabilities still need recovery contracts before unusual failures can self-recover"
        )
        return ButlerDoctorCheck(
            name="recovery contracts",
            status=status,
            detail=detail,
            metadata={
                "implemented": sorted(_IMPLEMENTED_RECOVERY_CONTRACTS),
                "missing": missing,
                "failure_taxonomy": [
                    "dependency_missing",
                    "auth_required",
                    "permission_required",
                    "contract_error",
                    "runtime_unavailable",
                    "needs_user_decision",
                ],
                "recoverable_failure_kinds": sorted(_RECOVERABLE_FAILURE_KINDS),
            },
        )

    def agent_governance_check(self) -> ButlerDoctorCheck:
        manifests = self._agent_manifests()
        missing_recovery: list[str] = []
        missing_lifecycle: list[str] = []
        merge_candidates: list[str] = []
        capability_to_agents: dict[str, list[str]] = {}

        for manifest in manifests:
            agent = manifest.get("agent") if isinstance(manifest.get("agent"), dict) else {}
            agent_id = str(agent.get("id") or manifest.get("id") or "unknown").strip() or "unknown"
            lifecycle = str(manifest.get("lifecycle") or "").strip().lower()
            if lifecycle not in _AGENT_LIFECYCLE_VALUES:
                missing_lifecycle.append(agent_id)
            if not isinstance(manifest.get("recovery_contract"), dict):
                missing_recovery.append(agent_id)
            capability = _agent_capability(manifest)
            if capability:
                capability_to_agents.setdefault(capability, []).append(agent_id)

        for capability, agents in capability_to_agents.items():
            if len(agents) > 1:
                merge_candidates.append(f"{capability}: {', '.join(sorted(agents))}")

        status = "ok" if not missing_recovery and not missing_lifecycle else "degraded"
        detail = (
            "Agent lifecycle and recovery metadata are complete"
            if status == "ok"
            else "Some agent manifests need lifecycle/recovery metadata; prefer capability actions over new agents"
        )
        return ButlerDoctorCheck(
            name="agent governance",
            status=status,
            detail=detail,
            metadata={
                "agent_count": len(manifests),
                "missing_recovery_contract": sorted(missing_recovery),
                "missing_lifecycle": sorted(missing_lifecycle),
                "merge_candidates": sorted(merge_candidates),
                "lifecycle_values": sorted(_AGENT_LIFECYCLE_VALUES),
                "admission_rule": (
                    "Create a capability first; promote to agent only with distinct tools, risk boundary, "
                    "artifact schema, and recovery contract."
                ),
            },
        )

    def _agent_manifests(self) -> list[dict[str, Any]]:
        root = self.repo_root / "agents"
        manifests: list[dict[str, Any]] = []
        if not root.exists():
            return manifests
        for path in sorted(root.glob("*/manifest.yaml")):
            try:
                payload = _load_manifest_object(path)
            except Exception:
                manifests.append({"id": path.parent.name, "manifest_error": True})
                continue
            if isinstance(payload, dict):
                manifests.append(payload)
        return manifests


def _load_manifest_object(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        raise ValueError(f"empty manifest: {path}")
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise ValueError(f"manifest {path} requires PyYAML for non-JSON YAML") from exc
        payload = yaml.safe_load(stripped)
    if not isinstance(payload, dict):
        raise ValueError(f"invalid manifest payload in {path}; expected object")
    return payload


def classify_recovery_failure_kind(
    *,
    error_kind: str | None,
    evidence: str | None = None,
) -> RecoveryFailureKind:
    text = f"{error_kind or ''} {evidence or ''}".strip().lower()
    if any(
        token in text
        for token in ("collector_missing", "binary_missing", "command not found", "not on path")
    ):
        return "dependency_missing"
    if any(token in text for token in ("auth", "login", "not authenticated", "unauthorized")):
        return "auth_required"
    if any(token in text for token in ("permission", "approval", "not allowed", "blocked")):
        return "permission_required"
    if any(token in text for token in ("validation", "field required", "contract", "payload")):
        return "contract_error"
    if any(token in text for token in ("runtime_unavailable", "adapter_missing", "bridge_unavailable")):
        return "runtime_unavailable"
    if any(token in text for token in ("ambiguous", "needs_user", "user_decision")):
        return "needs_user_decision"
    return "unknown_complex"


def _agent_capability(manifest: dict[str, Any]) -> str:
    capability = str(manifest.get("capability_id") or "").strip()
    if capability:
        return capability
    routing = manifest.get("routing") if isinstance(manifest.get("routing"), dict) else {}
    task_types = routing.get("task_types")
    if isinstance(task_types, list) and task_types:
        first = str(task_types[0] or "").strip()
        return first.split(".", 1)[0] if "." in first else first
    return ""
