from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.butler_tool_broker import ButlerToolBroker
from autoresearch.core.services.federation import FederationService, FederationTaskCreateRequest
from autoresearch.core.services.git_promotion_gate import GitPromotionGateService, GitPromotionProvider
from autoresearch.core.services.governed_mcp import GovernedMCPToolCallRequest, GovernedMCPService, ToolPermissionService
from autoresearch.core.services.model_gateway import ModelGatewayDenied, ModelGatewayService, ModelProviderRead
from autoresearch.core.services.runtime_isolation import RuntimeIsolationService, RuntimeIsolationViolation
from autoresearch.core.services.secret_vault import SecretAccessDenied, SecretVaultService
from autoresearch.core.services.usage_quota import UsageLedgerEntryRead, UsageQuotaService
from autoresearch.ga.contracts import ModelInvocationRequest
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalStatus,
    GitPromotionMode,
    GitRemoteProbe,
    PromotionActorRole,
    PromotionIntent,
)
from autoresearch.shared.store import InMemoryRepository


class BypassBlocked(PermissionError):
    pass


def _expect_blocked(label: str, exc_type: type[Exception], fn: Callable[[], object]) -> dict[str, object]:
    try:
        fn()
    except exc_type as exc:
        return {"check": label, "status": "passed", "message": str(exc), "synthetic": False}
    except Exception as exc:
        return {
            "check": label,
            "status": "failed",
            "message": f"wrong exception: {type(exc).__name__}: {exc}",
            "synthetic": False,
        }
    return {"check": label, "status": "failed", "message": "bypass was not blocked", "synthetic": False}


def run_bypass_checks(repo_root: Path) -> list[dict[str, object]]:
    checks = [
        _expect_blocked("direct_env_key_access", SecretAccessDenied, lambda: _attempt_direct_env_key_access(repo_root)),
        _expect_blocked("direct_model_call", ModelGatewayDenied, _attempt_direct_model_call),
        _expect_blocked("direct_tool_call", BypassBlocked, _attempt_direct_tool_call),
        _expect_blocked(
            "approval_rejected_but_action_continues",
            BypassBlocked,
            _attempt_rejected_approval_continuation,
        ),
        _expect_blocked("federation_without_lease", KeyError, lambda: _attempt_federation_without_lease(repo_root)),
        _expect_blocked(
            "unauthorized_package_tool_registration",
            PermissionError,
            lambda: ButlerToolBroker(repo_root=repo_root).assert_package_tool_registration_allowed(
                package_id="reference.furniture",
                package_stable=False,
                policy_decision=None,
                approval_status=None,
            ),
        ),
        _expect_blocked("direct_db_mutation", RuntimeIsolationViolation, _attempt_direct_db_mutation),
        _expect_blocked("artifact_promotion_bypass", BypassBlocked, lambda: _attempt_artifact_promotion_bypass(repo_root)),
    ]
    return checks


def _attempt_direct_env_key_access(repo_root: Path) -> None:
    vault = SecretVaultService()
    vault.assert_no_direct_secret_access(attempted_path=str(repo_root / ".env"))
    ModelGatewayService().assert_no_direct_model_access(env_key="OPENAI_API_KEY")


def _attempt_direct_model_call() -> None:
    gateway = ModelGatewayService(
        providers=[ModelProviderRead(provider_id="local-dev", enabled=True, models=["noop"])]
    )
    gateway.invoke(ModelInvocationRequest(provider_id="local-dev", model_id="noop", prompt="hello"))


def _attempt_direct_tool_call() -> None:
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        servers = tmp / "mcp_servers.yaml"
        permissions = tmp / "tool_permissions.yaml"
        quota = tmp / "quota_policy.yaml"
        servers.write_text(
            """
servers:
  - server_id: local_demo
    display_name: Local demo
    transport: local
    enabled: true
    tools:
      - tool_id: local_demo.external_write
        name: external_write
        tier: external_write
        enabled: true
""",
            encoding="utf-8",
        )
        permissions.write_text(
            """
defaults:
  allowed_roles: [member]
  allowed_agents: ["*"]
tools:
  local_demo.external_write:
    enabled: true
    decision: approval_required
    allowed_roles: [owner]
""",
            encoding="utf-8",
        )
        quota.write_text("defaults:\n  max_units_per_period: 10\n", encoding="utf-8")
        service = GovernedMCPService(
            servers_path=servers,
            permission_service=ToolPermissionService(policy_path=permissions),
            quota_service=UsageQuotaService(
                repository=InMemoryRepository[UsageLedgerEntryRead](),
                policy_path=quota,
            ),
        )
        result = service.call_tool(
            GovernedMCPToolCallRequest(
                tool_id="local_demo.external_write",
                actor_id="member-1",
                actor_role="member",
            )
        )
        if result.status == "succeeded":
            return
        raise BypassBlocked(result.error or result.permission.reason)


def _attempt_rejected_approval_continuation() -> None:
    store = ApprovalStoreService(repository=InMemoryRepository())
    approval = store.create_request(ApprovalRequestCreateRequest(title="external write"))
    rejected = store.resolve_request(
        approval.approval_id,
        ApprovalDecisionRequest(decision="rejected", decided_by="ga-bypass"),
    )
    if rejected.status == ApprovalStatus.APPROVED:
        return
    raise BypassBlocked(f"approval is {rejected.status.value}")


def _attempt_federation_without_lease(repo_root: Path) -> None:
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        peers = tmp / "peers.yaml"
        peers.write_text(
            """
peers:
  - peer_id: peer-1
    display_name: Peer 1
    status: active
    allowed_capabilities: [echo]
published_capabilities:
  - capability_id: echo
    name: Echo
""",
            encoding="utf-8",
        )
        service = FederationService(
            peers_path=peers,
            lease_repository=InMemoryRepository(),
            task_repository=InMemoryRepository(),
            control_plane=_UnusedControlPlane(),
        )
        service.submit_task(
            FederationTaskCreateRequest(
                peer_id="peer-1",
                lease_id="missing-lease",
                capability_id="echo",
                task_name="run without lease",
            )
        )
    _ = repo_root


def _attempt_direct_db_mutation() -> None:
    RuntimeIsolationService().assert_control_plane_mutation_allowed(via_api=False)


def _attempt_artifact_promotion_bypass(repo_root: Path) -> None:
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp = Path(raw_tmp)
        patch = tmp / "change.patch"
        patch.write_text("diff --git a/src/demo.py b/src/demo.py\n", encoding="utf-8")
        service = GitPromotionGateService(repo_root=repo_root, provider=_HealthyPromotionProvider())
        preflight, _result = service.finalize(
            intent=PromotionIntent(
                run_id="ga-bypass",
                actor_role=PromotionActorRole.AGGREGATOR,
                patch_uri=str(patch),
                changed_files=["src/demo.py"],
                preferred_mode=GitPromotionMode.DRAFT_PR,
                target_base_branch="main",
                approval_granted=False,
                writer_lease_key="ga-bypass",
            ),
            artifacts_dir=tmp / "promotion",
        )
        if preflight.effective_mode == GitPromotionMode.DRAFT_PR:
            return
        raise BypassBlocked(preflight.reason or "draft PR promotion requires approval")


class _UnusedControlPlane:
    def list_capabilities(self) -> list[Any]:
        return []

    def create_task(self, _request: Any) -> Any:
        raise AssertionError("control plane should not be reached without a federation lease")


class _HealthyPromotionProvider(GitPromotionProvider):
    def probe_remote_health(self, repo_root: Path, *, base_branch: str) -> GitRemoteProbe:
        _ = repo_root, base_branch
        return GitRemoteProbe(healthy=True, credentials_available=True, base_branch_exists=True)

    def create_branch(self, repo_root: Path, *, branch_name: str, base_branch: str, workspace_dir: Path) -> None:
        raise NotImplementedError

    def commit_changes(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        patch_uri: Path,
        changed_files: list[str],
        commit_message: str,
        validator_commands: list[str] | None = None,
        validator_log_dir: Path | None = None,
    ) -> str:
        raise NotImplementedError

    def push_branch(self, repo_root: Path, *, workspace_dir: Path, branch_name: str) -> None:
        raise NotImplementedError

    def open_draft_pr(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> str:
        raise NotImplementedError


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    checks = run_bypass_checks(repo_root)
    failed = [check for check in checks if check["status"] != "passed" or check.get("synthetic") is True]
    for check in checks:
        print(f"{check['status']}: {check['check']} - {check['message']}")
    print(json.dumps({"status": "failed" if failed else "passed", "failed": failed}, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
