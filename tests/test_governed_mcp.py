from __future__ import annotations

from pathlib import Path

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.governed_mcp import (
    GovernedMCPService,
    GovernedMCPToolCallRequest,
    ToolPermissionService,
)
from autoresearch.core.services.usage_quota import UsageLedgerEntryRead, UsageQuotaService
from autoresearch.shared.models import ApprovalRequestRead, ApprovalStatus
from autoresearch.shared.store import InMemoryRepository


def _write_configs(root: Path, *, member_limit: int = 10) -> tuple[Path, Path, Path]:
    servers = root / "mcp_servers.yaml"
    permissions = root / "tool_permissions.yaml"
    quota = root / "quota_policy.yaml"
    servers.write_text(
        """
servers:
  - server_id: local_demo
    display_name: Local demo
    transport: local
    enabled: true
    tools:
      - tool_id: local_demo.echo
        name: echo
        tier: common_read
        enabled: true
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
  allowed_roles: [owner, supervisor, member, peer]
  allowed_agents: ["*"]
tools:
  local_demo.echo:
    enabled: true
    decision: auto
    allowed_roles: [owner, supervisor, member, peer]
    allowed_agents: ["*"]
  local_demo.external_write:
    enabled: true
    decision: approval_required
    allowed_roles: [owner, supervisor]
    allowed_agents: ["*"]
""",
        encoding="utf-8",
    )
    quota.write_text(
        f"""
defaults:
  period_seconds: 86400
  max_units_per_period: {member_limit}
roles:
  member:
    max_units_per_period: {member_limit}
  supervisor:
    max_units_per_period: 100
""",
        encoding="utf-8",
    )
    return servers, permissions, quota


def _build_service(root: Path, *, member_limit: int = 10) -> tuple[GovernedMCPService, ApprovalStoreService, UsageQuotaService]:
    servers, permissions, quota = _write_configs(root, member_limit=member_limit)
    quota_service = UsageQuotaService(
        repository=InMemoryRepository[UsageLedgerEntryRead](),
        policy_path=quota,
    )
    approvals = ApprovalStoreService(repository=InMemoryRepository[ApprovalRequestRead]())
    return (
        GovernedMCPService(
            servers_path=servers,
            permission_service=ToolPermissionService(policy_path=permissions),
            quota_service=quota_service,
            approval_store=approvals,
        ),
        approvals,
        quota_service,
    )


def test_common_read_mcp_tool_auto_runs_and_commits_quota(tmp_path: Path) -> None:
    service, _approvals, quota = _build_service(tmp_path)

    result = service.call_tool(
        GovernedMCPToolCallRequest(
            tool_id="local_demo.echo",
            params={"message": "hello"},
            actor_id="u1",
            actor_role="member",
        )
    )

    assert result.status == "succeeded"
    assert result.usage_entry_id is not None
    ledger = quota.list_entries(subject_id="u1")
    assert [entry.status for entry in ledger] == ["committed"]


def test_external_write_mcp_tool_creates_approval_before_call(tmp_path: Path) -> None:
    service, approvals, quota = _build_service(tmp_path)

    result = service.call_tool(
        GovernedMCPToolCallRequest(
            tool_id="local_demo.external_write",
            params={"message": "write"},
            actor_id="u2",
            actor_role="supervisor",
        )
    )

    assert result.status == "awaiting_approval"
    assert result.approval_id is not None
    assert approvals.get_request(result.approval_id).status == ApprovalStatus.PENDING
    assert [entry.status for entry in quota.list_entries(subject_id="u2")] == ["released"]


def test_mcp_tool_call_blocks_when_quota_is_exhausted(tmp_path: Path) -> None:
    service, _approvals, quota = _build_service(tmp_path, member_limit=1)

    first = service.call_tool(
        GovernedMCPToolCallRequest(
            tool_id="local_demo.echo",
            actor_id="u3",
            actor_role="member",
        )
    )
    second = service.call_tool(
        GovernedMCPToolCallRequest(
            tool_id="local_demo.echo",
            actor_id="u3",
            actor_role="member",
        )
    )

    assert first.status == "succeeded"
    assert second.status == "blocked"
    assert [entry.status for entry in quota.list_entries(subject_id="u3")] == [
        "committed",
        "rejected",
    ]


def test_stdio_mcp_tool_discovery_and_call(tmp_path: Path) -> None:
    server_script = tmp_path / "stdio_mcp_server.py"
    server_script.write_text(
        r'''
import json
import sys

def read_frame():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if line in (b"\r\n", b"\n", b""):
            break
        key, value = line.decode("ascii").split(":", 1)
        headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if not length:
        return None
    return json.loads(sys.stdin.buffer.read(length).decode("utf-8"))

def write_frame(payload):
    raw = json.dumps(payload).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(raw)}\r\n\r\n".encode("ascii") + raw)
    sys.stdout.buffer.flush()

while True:
    msg = read_frame()
    if msg is None:
        break
    method = msg.get("method")
    if method == "notifications/initialized":
        continue
    if method == "initialize":
        write_frame({"jsonrpc": "2.0", "id": msg["id"], "result": {"capabilities": {"tools": {}}}})
    elif method == "tools/list":
        write_frame({"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": [{"name": "ping", "description": "Ping", "inputSchema": {"type": "object"}}]}})
    elif method == "tools/call":
        write_frame({"jsonrpc": "2.0", "id": msg["id"], "result": {"content": [{"type": "text", "text": "pong"}], "isError": False}})
''',
        encoding="utf-8",
    )
    servers = tmp_path / "mcp_servers.yaml"
    permissions = tmp_path / "tool_permissions.yaml"
    quota = tmp_path / "quota_policy.yaml"
    servers.write_text(
        f"""
servers:
  - server_id: stdio_demo
    display_name: stdio demo
    transport: stdio
    command: python3
    args: ["{server_script}"]
    enabled: true
    tool_allowlist: [ping]
    tools: []
""",
        encoding="utf-8",
    )
    permissions.write_text(
        """
defaults:
  allowed_roles: [member]
  allowed_agents: ["*"]
tools:
  stdio_demo.ping:
    enabled: true
    decision: auto
""",
        encoding="utf-8",
    )
    quota.write_text("defaults:\n  max_units_per_period: 10\n", encoding="utf-8")
    quota_service = UsageQuotaService(
        repository=InMemoryRepository[UsageLedgerEntryRead](),
        policy_path=quota,
    )
    service = GovernedMCPService(
        servers_path=servers,
        permission_service=ToolPermissionService(policy_path=permissions),
        quota_service=quota_service,
    )

    tools = service.list_tools()
    assert [tool.tool_id for tool in tools] == ["stdio_demo.ping"]
    result = service.call_tool(
        GovernedMCPToolCallRequest(tool_id="stdio_demo.ping", actor_id="u4", actor_role="member")
    )

    assert result.status == "succeeded"
    assert result.result["isError"] is False
