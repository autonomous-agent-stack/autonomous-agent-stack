from __future__ import annotations

from pathlib import Path

from autoresearch.ga.contracts import RuntimeIsolationPolicyRead, RuntimeIsolationReportRead, Stability
from autoresearch.github_assistant.config import load_yaml_object


class RuntimeIsolationViolation(PermissionError):
    pass


class RuntimeIsolationService:
    def __init__(self, config_path: Path | None = None) -> None:
        self._payload = load_yaml_object(config_path) if config_path and config_path.exists() else {}

    def policy_for(self, profile_id: str = "default_runtime_sandbox") -> RuntimeIsolationPolicyRead:
        profiles = self._payload.get("profiles") if isinstance(self._payload.get("profiles"), dict) else {}
        raw = dict(profiles.get(profile_id) or {})
        return RuntimeIsolationPolicyRead(profile_id=profile_id, **raw)

    def validate_runtime(
        self,
        *,
        runtime_id: str,
        stability: Stability = Stability.EXPERIMENTAL,
        profile_id: str = "default_runtime_sandbox",
    ) -> RuntimeIsolationReportRead:
        policy = self.policy_for(profile_id)
        violations = _policy_violations(policy)
        return RuntimeIsolationReportRead(
            runtime_id=runtime_id,
            stability=stability,
            policy=policy,
            passed=not violations,
            violations=violations,
        )

    def assert_runtime_path_allowed(self, *, path: str, workspace_root: str, artifact_root: str | None = None) -> None:
        target = Path(path).expanduser().resolve()
        workspace = Path(workspace_root).expanduser().resolve()
        artifact = Path(artifact_root).expanduser().resolve() if artifact_root else None
        allowed = target == workspace or workspace in target.parents
        if artifact is not None:
            allowed = allowed or target == artifact or artifact in target.parents
        if not allowed:
            raise RuntimeIsolationViolation("runtime path escapes governed workspace")
        if target.name == ".env" or ".env" in target.parts:
            raise RuntimeIsolationViolation("runtime direct .env access is forbidden")

    def assert_network_allowed(self, *, policy_decision: str | None) -> None:
        if policy_decision != "allow":
            raise RuntimeIsolationViolation("runtime external network requires PolicyDecision allow")

    def assert_control_plane_mutation_allowed(self, *, via_api: bool) -> None:
        if not via_api:
            raise RuntimeIsolationViolation("UI/CLI/SDK database mutation must go through /api/v2")


def _policy_violations(policy: RuntimeIsolationPolicyRead) -> list[str]:
    checks: dict[str, bool] = {
        "filesystem_sandbox": policy.filesystem_sandbox,
        "process_isolation": policy.process_isolation,
        "artifact_output_directory_only": policy.artifact_output_directory_only,
        "deny_dotenv": policy.deny_dotenv,
        "deny_host_home": policy.deny_host_home,
        "secret_injection_lease_only": policy.secret_injection == "lease_only",
        "network_deny_or_policy_required": policy.network_egress_policy in {"deny_by_default", "policy_required"},
    }
    return [name for name, passed in checks.items() if not passed]
