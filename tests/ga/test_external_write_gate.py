from __future__ import annotations

from pathlib import Path

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.governed_mcp import (
    GovernedMCPService,
    GovernedMCPToolCallRequest,
    ToolPermissionService,
)
from autoresearch.core.services.usage_quota import UsageLedgerEntryRead, UsageQuotaService
from autoresearch.shared.models import ApprovalDecisionRequest, ApprovalRequestRead
from autoresearch.shared.store import InMemoryRepository


ROOT = Path(__file__).resolve().parents[2]


def _service() -> tuple[GovernedMCPService, ApprovalStoreService]:
    approvals = ApprovalStoreService(repository=InMemoryRepository[ApprovalRequestRead]())
    service = GovernedMCPService(
        servers_path=ROOT / "configs/mcp_servers.yaml",
        permission_service=ToolPermissionService(policy_path=ROOT / "configs/tool_permissions.yaml"),
        quota_service=UsageQuotaService(
            repository=InMemoryRepository[UsageLedgerEntryRead](),
            policy_path=ROOT / "configs/quota_policy.yaml",
        ),
        approval_store=approvals,
    )
    return service, approvals


def test_external_write_defaults_to_dry_run_after_approval(monkeypatch) -> None:
    monkeypatch.delenv("EXTERNAL_WRITE_LIVE", raising=False)
    service, approvals = _service()
    pending = service.call_tool(
        GovernedMCPToolCallRequest(
            tool_id="local_demo.external_write",
            actor_role="supervisor",
            params={"recipient": "customer@example.com"},
        )
    )
    approved = approvals.resolve_request(
        pending.approval_id or "",
        ApprovalDecisionRequest(decision="approved", decided_by="test"),
    )

    result = service.call_tool(
        GovernedMCPToolCallRequest(
            tool_id="local_demo.external_write",
            actor_role="supervisor",
            approval_id=approved.approval_id,
            params={"recipient": "customer@example.com"},
        )
    )

    assert result.status == "succeeded"
    assert result.result["dry_run"] is True


def test_live_external_write_requires_all_gate_inputs(monkeypatch) -> None:
    monkeypatch.setenv("EXTERNAL_WRITE_LIVE", "1")
    service, approvals = _service()
    pending = service.call_tool(
        GovernedMCPToolCallRequest(
            tool_id="local_demo.external_write",
            actor_role="supervisor",
            params={"recipient": "customer@example.com"},
        )
    )
    approved = approvals.resolve_request(
        pending.approval_id or "",
        ApprovalDecisionRequest(decision="approved", decided_by="test"),
    )

    result = service.call_tool(
        GovernedMCPToolCallRequest(
            tool_id="local_demo.external_write",
            actor_role="supervisor",
            approval_id=approved.approval_id,
            params={"recipient": "customer@example.com"},
        )
    )

    assert result.status == "failed"
    assert "external write live gate missing" in (result.error or "")
