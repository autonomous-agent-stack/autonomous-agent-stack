from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import Field, field_validator

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.butler_failure_review import (
    ButlerFailureReviewRequest,
    ButlerFailureReviewService,
)
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.usage_quota import UsageQuotaCheckRequest, UsageQuotaService
from autoresearch.github_assistant.config import load_yaml_object
from autoresearch.shared.models import (
    ApprovalRequestCreateRequest,
    ApprovalRisk,
    ApprovalStatus,
    SessionEventCreateRequest,
    StrictModel,
)
from autoresearch.shared.store import create_resource_id


ToolRiskTier = Literal["common_read", "sensitive_read", "external_write", "destructive"]
ToolPermissionDecisionValue = Literal["auto", "approval_required", "blocked"]
GovernedMCPCallStatus = Literal["succeeded", "awaiting_approval", "blocked", "failed"]


class MCPServerRead(StrictModel):
    server_id: str
    display_name: str
    transport: Literal["local", "http"] = "local"
    endpoint: str | None = None
    enabled: bool = False
    auth_env: str | None = None
    tool_allowlist: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernedMCPToolRead(StrictModel):
    tool_id: str
    server_id: str
    name: str
    description: str = ""
    tier: ToolRiskTier = "common_read"
    enabled: bool = True
    input_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolPermissionDecisionRead(StrictModel):
    decision: ToolPermissionDecisionValue
    reason: str
    risk_tier: ToolRiskTier
    risk_tags: list[str] = Field(default_factory=list)
    required_role: str | None = None


class GovernedMCPToolCallRequest(StrictModel):
    tool_id: str = Field(..., min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)
    actor_id: str = "local-user"
    actor_role: str = "member"
    agent_name: str = "butler_orchestrator"
    session_id: str | None = None
    task_id: str | None = None
    approval_id: str | None = None
    quota_units: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tool_id", "actor_id", "actor_role", "agent_name", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("session_id", "task_id", "approval_id", mode="before")
    @classmethod
    def _strip_optional(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class GovernedMCPToolCallRead(StrictModel):
    call_id: str
    tool_id: str
    status: GovernedMCPCallStatus
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    permission: ToolPermissionDecisionRead
    approval_id: str | None = None
    usage_entry_id: str | None = None
    audit_event_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolPermissionService:
    def __init__(self, *, policy_path: Path) -> None:
        self._policy_path = policy_path
        self._policy = self._load_policy()

    def decide(
        self,
        *,
        tool: GovernedMCPToolRead,
        actor_role: str,
        agent_name: str,
    ) -> ToolPermissionDecisionRead:
        tier = tool.tier
        tool_policy = self._tool_policy(tool.tool_id)
        if tool_policy.get("enabled") is False or not tool.enabled:
            return ToolPermissionDecisionRead(
                decision="blocked",
                reason="tool is disabled by policy",
                risk_tier=tier,
                risk_tags=self._risk_tags(tier, tool_policy),
            )
        if tier == "destructive":
            return ToolPermissionDecisionRead(
                decision="blocked",
                reason="destructive MCP tools are blocked by default",
                risk_tier=tier,
                risk_tags=sorted(set(self._risk_tags(tier, tool_policy)) | {"destructive"}),
            )
        if not self._role_allowed(actor_role, tool_policy):
            return ToolPermissionDecisionRead(
                decision="blocked",
                reason=f"role {actor_role or 'unknown'} is not allowed for {tool.tool_id}",
                risk_tier=tier,
                risk_tags=self._risk_tags(tier, tool_policy),
            )
        if not self._agent_allowed(agent_name, tool_policy):
            return ToolPermissionDecisionRead(
                decision="blocked",
                reason=f"agent {agent_name or 'unknown'} is not allowed for {tool.tool_id}",
                risk_tier=tier,
                risk_tags=self._risk_tags(tier, tool_policy),
            )
        raw_decision = str(tool_policy.get("decision") or self._tier_default_decision(tier)).strip().lower()
        if raw_decision not in {"auto", "approval_required", "blocked"}:
            raw_decision = "blocked"
        return ToolPermissionDecisionRead(
            decision=raw_decision,  # type: ignore[arg-type]
            reason=str(tool_policy.get("reason") or f"{tier} policy"),
            risk_tier=tier,
            risk_tags=self._risk_tags(tier, tool_policy),
            required_role=tool_policy.get("required_role"),
        )

    def doctor(self) -> dict[str, Any]:
        return {
            "policy_path": str(self._policy_path),
            "policy_loaded": self._policy_path.exists(),
            "tools": sorted((self._policy.get("tools") or {}).keys()),
        }

    def _load_policy(self) -> dict[str, Any]:
        if not self._policy_path.exists():
            return {}
        return load_yaml_object(self._policy_path)

    def _tool_policy(self, tool_id: str) -> dict[str, Any]:
        tools = self._policy.get("tools") if isinstance(self._policy.get("tools"), dict) else {}
        return dict(tools.get(tool_id) or {}) if isinstance(tools, dict) else {}

    def _role_allowed(self, actor_role: str, policy: dict[str, Any]) -> bool:
        allowed = policy.get("allowed_roles")
        if allowed is None:
            allowed = (self._policy.get("defaults") or {}).get("allowed_roles", ["owner", "supervisor", "operator", "member"])
        return _matches(actor_role.strip().lower() or "unknown", allowed)

    def _agent_allowed(self, agent_name: str, policy: dict[str, Any]) -> bool:
        allowed = policy.get("allowed_agents")
        if allowed is None:
            allowed = (self._policy.get("defaults") or {}).get("allowed_agents", ["*"])
        return _matches(agent_name.strip() or "unknown", allowed)

    @staticmethod
    def _tier_default_decision(tier: ToolRiskTier) -> ToolPermissionDecisionValue:
        if tier == "common_read":
            return "auto"
        if tier in {"sensitive_read", "external_write"}:
            return "approval_required"
        return "blocked"

    @staticmethod
    def _risk_tags(tier: ToolRiskTier, policy: dict[str, Any]) -> list[str]:
        tags = set(str(item).strip() for item in policy.get("risk_tags") or [] if str(item).strip())
        if tier == "sensitive_read":
            tags.add("sensitive_read")
        elif tier == "external_write":
            tags.update({"external_api", "external_write"})
        elif tier == "destructive":
            tags.update({"external_api", "destructive"})
        return sorted(tags)


class GovernedMCPService:
    """MCP tool gateway with permission, quota, approval, and audit gates."""

    def __init__(
        self,
        *,
        servers_path: Path,
        permission_service: ToolPermissionService,
        quota_service: UsageQuotaService,
        approval_store: ApprovalStoreService | None = None,
        session_events: SessionEventService | None = None,
        failure_review_service: ButlerFailureReviewService | None = None,
    ) -> None:
        self._servers_path = servers_path
        self._permission_service = permission_service
        self._quota_service = quota_service
        self._approval_store = approval_store
        self._session_events = session_events
        self._failure_review_service = failure_review_service
        self._payload = self._load_servers()

    @property
    def servers_path(self) -> Path:
        return self._servers_path

    def list_servers(self) -> list[MCPServerRead]:
        return [self._server_from_payload(item) for item in self._server_items()]

    def list_tools(self) -> list[GovernedMCPToolRead]:
        tools: list[GovernedMCPToolRead] = []
        for server in self.list_servers():
            tools.extend(self._configured_tools_for_server(server))
            if server.enabled and server.transport == "http":
                tools.extend(self._discover_http_tools(server))
        tools.sort(key=lambda item: (item.server_id, item.tool_id))
        return _dedupe_tools(tools)

    def call_tool(self, request: GovernedMCPToolCallRequest) -> GovernedMCPToolCallRead:
        call_id = create_resource_id("mcp_call")
        tool = self._find_tool(request.tool_id)
        if tool is None:
            permission = ToolPermissionDecisionRead(
                decision="blocked",
                reason="tool not found",
                risk_tier="common_read",
            )
            return self._finish_call(call_id, request, permission=permission, status="blocked", error="tool not found")

        permission = self._permission_service.decide(
            tool=tool,
            actor_role=request.actor_role,
            agent_name=request.agent_name,
        )
        quota_units = request.quota_units if request.quota_units is not None else self._quota_units_for(tool.tier)
        reserve = self._quota_service.reserve(
            UsageQuotaCheckRequest(
                subject_id=request.actor_id,
                subject_type="peer" if request.actor_role == "peer" else "user",
                actor_role=request.actor_role,
                agent_name=request.agent_name,
                tool_id=tool.tool_id,
                task_id=request.task_id,
                quota_units=quota_units,
                session_id=request.session_id,
                metadata={
                    **request.metadata,
                    "session_id": request.session_id,
                    "mcp_call_id": call_id,
                    "risk_tier": tool.tier,
                },
            )
        )
        usage_entry_id = reserve.entry.entry_id if reserve.entry else None
        if not reserve.allowed:
            return self._finish_call(
                call_id,
                request,
                permission=permission,
                status="blocked",
                error=reserve.reason,
                usage_entry_id=usage_entry_id,
            )
        if permission.decision == "blocked":
            if usage_entry_id:
                self._quota_service.release(usage_entry_id, metadata={"release_reason": "permission_blocked"})
            return self._finish_call(
                call_id,
                request,
                permission=permission,
                status="blocked",
                error=permission.reason,
                usage_entry_id=usage_entry_id,
            )
        approval_id = request.approval_id
        if permission.decision == "approval_required":
            if not self._approval_satisfied(approval_id):
                if usage_entry_id:
                    self._quota_service.release(usage_entry_id, metadata={"release_reason": "awaiting_approval"})
                created_id = self._create_approval(request, tool=tool, permission=permission)
                return self._finish_call(
                    call_id,
                    request,
                    permission=permission,
                    status="awaiting_approval",
                    approval_id=created_id,
                    usage_entry_id=usage_entry_id,
                    metadata={"approval_required": True},
                )

        try:
            result = self._execute_tool(tool, request.params)
        except Exception as exc:
            if usage_entry_id:
                self._quota_service.release(usage_entry_id, metadata={"release_reason": "tool_failed"})
            return self._finish_call(
                call_id,
                request,
                permission=permission,
                status="failed",
                error=str(exc),
                usage_entry_id=usage_entry_id,
            )

        if usage_entry_id:
            self._quota_service.commit(usage_entry_id, metadata={"commit_reason": "tool_succeeded"})
        return self._finish_call(
            call_id,
            request,
            permission=permission,
            status="succeeded",
            result=result,
            approval_id=approval_id,
            usage_entry_id=usage_entry_id,
        )

    def doctor(self) -> dict[str, Any]:
        servers = self.list_servers()
        tools = self.list_tools()
        return {
            "status": "ok",
            "servers_path": str(self._servers_path),
            "servers_loaded": self._servers_path.exists(),
            "server_count": len(servers),
            "enabled_server_count": len([item for item in servers if item.enabled]),
            "tool_count": len(tools),
            "enabled_tool_count": len([item for item in tools if item.enabled]),
            "permission": self._permission_service.doctor(),
        }

    def _load_servers(self) -> dict[str, Any]:
        if not self._servers_path.exists():
            return {"servers": []}
        return load_yaml_object(self._servers_path)

    def _server_items(self) -> list[dict[str, Any]]:
        raw = self._payload.get("servers")
        return [dict(item) for item in raw] if isinstance(raw, list) else []

    def _server_from_payload(self, payload: dict[str, Any]) -> MCPServerRead:
        return MCPServerRead(
            server_id=str(payload.get("server_id") or payload.get("id") or "").strip(),
            display_name=str(payload.get("display_name") or payload.get("name") or payload.get("server_id") or "").strip(),
            transport=str(payload.get("transport") or "local").strip().lower(),
            endpoint=_optional_string(payload.get("endpoint")),
            enabled=bool(payload.get("enabled", False)),
            auth_env=_optional_string(payload.get("auth_env")),
            tool_allowlist=[str(item).strip() for item in payload.get("tool_allowlist") or [] if str(item).strip()],
            metadata={k: v for k, v in payload.items() if k not in {"server_id", "id", "display_name", "name", "transport", "endpoint", "enabled", "auth_env", "tool_allowlist", "tools"}},
        )

    def _configured_tools_for_server(self, server: MCPServerRead) -> list[GovernedMCPToolRead]:
        out: list[GovernedMCPToolRead] = []
        raw_server = next((item for item in self._server_items() if (item.get("server_id") or item.get("id")) == server.server_id), {})
        for raw in raw_server.get("tools") or []:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or raw.get("tool_id") or "").strip()
            if not name:
                continue
            tool_id = str(raw.get("tool_id") or f"{server.server_id}.{name}").strip()
            out.append(
                GovernedMCPToolRead(
                    tool_id=tool_id,
                    server_id=server.server_id,
                    name=name,
                    description=str(raw.get("description") or "").strip(),
                    tier=str(raw.get("tier") or "common_read").strip().lower(),
                    enabled=server.enabled and bool(raw.get("enabled", True)),
                    input_schema=dict(raw.get("input_schema") or raw.get("inputSchema") or {}),
                    metadata={**dict(raw.get("metadata") or {}), "transport": server.transport},
                )
            )
        return out

    def _discover_http_tools(self, server: MCPServerRead) -> list[GovernedMCPToolRead]:
        if not server.endpoint:
            return []
        try:
            payload = self._post_json_rpc(server, {"jsonrpc": "2.0", "id": "tools-list", "method": "tools/list", "params": {}})
        except Exception:
            return []
        raw_tools = ((payload.get("result") or {}).get("tools") if isinstance(payload.get("result"), dict) else None) or []
        out: list[GovernedMCPToolRead] = []
        for raw in raw_tools:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "").strip()
            if not name:
                continue
            if server.tool_allowlist and name not in server.tool_allowlist and f"{server.server_id}.{name}" not in server.tool_allowlist:
                continue
            out.append(
                GovernedMCPToolRead(
                    tool_id=f"{server.server_id}.{name}",
                    server_id=server.server_id,
                    name=name,
                    description=str(raw.get("description") or "").strip(),
                    tier="common_read",
                    enabled=True,
                    input_schema=dict(raw.get("inputSchema") or {}),
                    metadata={"transport": "http", "discovered": True},
                )
            )
        return out

    def _find_tool(self, tool_id: str) -> GovernedMCPToolRead | None:
        normalized = tool_id.strip()
        for tool in self.list_tools():
            if tool.tool_id == normalized or tool.name == normalized:
                return tool
        return None

    def _execute_tool(self, tool: GovernedMCPToolRead, params: dict[str, Any]) -> dict[str, Any]:
        if not tool.enabled:
            raise RuntimeError("tool is disabled")
        server = next((item for item in self.list_servers() if item.server_id == tool.server_id), None)
        if server is None:
            raise RuntimeError(f"MCP server not found: {tool.server_id}")
        if server.transport == "local":
            return {
                "tool": tool.tool_id,
                "server_id": server.server_id,
                "params": params,
                "result": "ok",
                "data": f"local MCP tool {tool.name} processed request",
            }
        if server.transport == "http":
            payload = self._post_json_rpc(
                server,
                {
                    "jsonrpc": "2.0",
                    "id": create_resource_id("mcp_rpc"),
                    "method": "tools/call",
                    "params": {"name": tool.name, "arguments": params},
                },
            )
            if payload.get("error"):
                raise RuntimeError(str(payload["error"]))
            result = payload.get("result")
            return result if isinstance(result, dict) else {"result": result}
        raise RuntimeError(f"unsupported MCP transport: {server.transport}")

    def _post_json_rpc(self, server: MCPServerRead, payload: dict[str, Any]) -> dict[str, Any]:
        if not server.endpoint:
            raise RuntimeError("MCP endpoint is not configured")
        headers: dict[str, str] = {}
        if server.auth_env:
            token = os.getenv(server.auth_env)
            if not token:
                raise RuntimeError(f"MCP auth env is not set: {server.auth_env}")
            headers["Authorization"] = f"Bearer {token}"
        with httpx.Client(timeout=10.0) as client:
            response = client.post(server.endpoint, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return data if isinstance(data, dict) else {"result": data}

    def _approval_satisfied(self, approval_id: str | None) -> bool:
        if not approval_id or self._approval_store is None:
            return False
        approval = self._approval_store.get_request(approval_id)
        return approval is not None and approval.status == ApprovalStatus.APPROVED

    def _create_approval(
        self,
        request: GovernedMCPToolCallRequest,
        *,
        tool: GovernedMCPToolRead,
        permission: ToolPermissionDecisionRead,
    ) -> str | None:
        if self._approval_store is None:
            return None
        approval = self._approval_store.create_request(
            ApprovalRequestCreateRequest(
                title=f"MCP tool approval: {tool.tool_id}",
                summary=f"{request.actor_id} requested {tool.tool_id} via {request.agent_name}.",
                risk=ApprovalRisk.EXTERNAL if tool.tier == "external_write" else ApprovalRisk.WRITE,
                source="governed_mcp",
                session_id=request.session_id,
                metadata={
                    "action_type": "mcp_tool_call",
                    "tool_id": tool.tool_id,
                    "server_id": tool.server_id,
                    "actor_id": request.actor_id,
                    "actor_role": request.actor_role,
                    "agent_name": request.agent_name,
                    "risk_tier": tool.tier,
                    "risk_tags": permission.risk_tags,
                    "params_digest": _digest(request.params),
                },
            )
        )
        return approval.approval_id

    def _finish_call(
        self,
        call_id: str,
        request: GovernedMCPToolCallRequest,
        *,
        permission: ToolPermissionDecisionRead,
        status: GovernedMCPCallStatus,
        result: dict[str, Any] | None = None,
        error: str | None = None,
        approval_id: str | None = None,
        usage_entry_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GovernedMCPToolCallRead:
        metadata_out = dict(metadata or {})
        if status in {"blocked", "failed"}:
            metadata_out.update(
                self._maybe_review_failed_call(
                    call_id=call_id,
                    request=request,
                    permission=permission,
                    status=status,
                    error=error,
                    usage_entry_id=usage_entry_id,
                    metadata=metadata_out,
                )
            )
        audit_event_id = self._record_call_event(
            call_id=call_id,
            request=request,
            permission=permission,
            status=status,
            error=error,
            approval_id=approval_id,
            usage_entry_id=usage_entry_id,
            metadata=metadata_out,
        )
        return GovernedMCPToolCallRead(
            call_id=call_id,
            tool_id=request.tool_id,
            status=status,
            result=dict(result or {}),
            error=error,
            permission=permission,
            approval_id=approval_id,
            usage_entry_id=usage_entry_id,
            audit_event_id=audit_event_id,
            metadata=metadata_out,
        )

    def _maybe_review_failed_call(
        self,
        *,
        call_id: str,
        request: GovernedMCPToolCallRequest,
        permission: ToolPermissionDecisionRead,
        status: GovernedMCPCallStatus,
        error: str | None,
        usage_entry_id: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        if self._failure_review_service is None:
            return {}
        review = self._failure_review_service.review(
            ButlerFailureReviewRequest(
                message=f"MCP tool {request.tool_id} {status}",
                task_id=request.task_id,
                run_id=call_id,
                capability_id="mcp",
                worker_error=error,
                worker_message=f"MCP tool call {status}",
                worker_result={"permission": permission.model_dump(mode="json")},
                worker_metrics={"status": status, "tool_id": request.tool_id},
                session_id=request.session_id,
                usage_entry_id=usage_entry_id,
                metadata={
                    **metadata,
                    "mcp_call_id": call_id,
                    "permission_decision": permission.decision,
                    "risk_tier": permission.risk_tier,
                },
            )
        )
        return {
            "failure_review_id": review.review_id,
            "failure_kind": review.failure_kind,
            "route_repair_suggestion": review.suggested_route,
            "candidate_skill_summary": review.candidate_skill_summary,
        }

    def _record_call_event(
        self,
        *,
        call_id: str,
        request: GovernedMCPToolCallRequest,
        permission: ToolPermissionDecisionRead,
        status: GovernedMCPCallStatus,
        error: str | None,
        approval_id: str | None,
        usage_entry_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> str | None:
        if self._session_events is None or not request.session_id:
            return None
        event_id = create_resource_id("mcp_event")
        self._session_events.append(
            SessionEventCreateRequest(
                session_id=request.session_id,
                source="governed_mcp",
                event_type=f"mcp.tool.{status}",
                role="tool" if status == "succeeded" else "status",
                content=f"MCP tool {request.tool_id} {status}.",
                status=status,
                approval_id=approval_id,
                idempotency_key=f"mcp:{call_id}:{status}",
                metadata={
                    "event_id": event_id,
                    "call_id": call_id,
                    "tool_id": request.tool_id,
                    "actor_id": request.actor_id,
                    "actor_role": request.actor_role,
                    "agent_name": request.agent_name,
                    "risk_tier": permission.risk_tier,
                    "risk_tags": permission.risk_tags,
                    "permission_decision": permission.decision,
                    "usage_entry_id": usage_entry_id,
                    "params_digest": _digest(request.params),
                    "error": error,
                    **dict(metadata or {}),
                },
            )
        )
        return event_id

    @staticmethod
    def _quota_units_for(tier: ToolRiskTier) -> int:
        return {
            "common_read": 1,
            "sensitive_read": 3,
            "external_write": 8,
            "destructive": 20,
        }[tier]


def _matches(value: str, allowed: object) -> bool:
    if isinstance(allowed, str):
        allowed = [allowed]
    if not isinstance(allowed, list):
        return False
    normalized = {str(item).strip() for item in allowed if str(item).strip()}
    return "*" in normalized or value in normalized or value.lower() in {item.lower() for item in normalized}


def _dedupe_tools(tools: list[GovernedMCPToolRead]) -> list[GovernedMCPToolRead]:
    seen: set[str] = set()
    out: list[GovernedMCPToolRead] = []
    for tool in tools:
        if tool.tool_id in seen:
            continue
        seen.add(tool.tool_id)
        out.append(tool)
    return out


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _digest(payload: object) -> str:
    raw = str(payload).encode("utf-8", "replace")
    return hashlib.sha256(raw).hexdigest()[:16]
