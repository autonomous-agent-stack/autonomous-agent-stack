from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.agent_protocol.registry import _load_yaml_like
from autoresearch.core.adapters.contracts import CapabilityDomain, MCPProvider
from autoresearch.github_assistant.config import load_yaml_object
from autoresearch.shared.models import StrictModel


class ButlerToolTier(StrEnum):
    COMMON_READ = "common_read"
    SENSITIVE_READ = "sensitive_read"
    EXTERNAL_WRITE = "external_write"
    DESTRUCTIVE = "destructive"


class ButlerToolDescriptorRead(StrictModel):
    tool_id: str = Field(..., min_length=1)
    capability: str = Field(..., min_length=1)
    aliases: list[str] = Field(default_factory=list)
    provider: str = "mcp"
    tier: ButlerToolTier = ButlerToolTier.COMMON_READ
    description: str = ""
    allowed_agents: list[str] = Field(default_factory=lambda: ["*"])
    allowed_roles: list[str] = Field(default_factory=lambda: ["owner", "supervisor"])
    risk_tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tool_id", "capability", "provider", mode="before")
    @classmethod
    def _strip_required_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("aliases", "allowed_agents", "allowed_roles", "risk_tags", mode="before")
    @classmethod
    def _normalize_text_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",")]
        return [str(item).strip() for item in value if str(item).strip()]


class ButlerToolRequirementRead(StrictModel):
    capability: str = Field(..., min_length=1)
    input_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capability", mode="before")
    @classmethod
    def _strip_capability(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("input_text", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ButlerToolGrantRead(StrictModel):
    grant_id: str
    tool_id: str
    capability: str
    provider: str
    tier: ButlerToolTier
    target_agent: str
    risk_tags: list[str] = Field(default_factory=list)
    audit_summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ButlerToolDeniedRead(StrictModel):
    capability: str
    reason: str
    tier: ButlerToolTier | None = None
    risk_tags: list[str] = Field(default_factory=list)
    audit_summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ButlerToolResolveRequest(StrictModel):
    requested_by: str = "local-user"
    actor_role: str = "operator"
    target_agent: str = "butler_orchestrator"
    tool_requirements: list[Any] = Field(default_factory=list)
    task_risk_tags: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("requested_by", "actor_role", "target_agent", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("task_risk_tags", mode="before")
    @classmethod
    def _normalize_risk_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",")]
        return sorted({str(item).strip().lower() for item in value if str(item).strip()})


class ButlerToolResolutionRead(StrictModel):
    status: Literal["granted", "partial", "denied"]
    requested_by: str
    actor_role: str
    target_agent: str
    grants: list[ButlerToolGrantRead] = Field(default_factory=list)
    denied: list[ButlerToolDeniedRead] = Field(default_factory=list)
    risk_tags: list[str] = Field(default_factory=list)
    audit_summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ButlerRegistryRead(StrictModel):
    tools: list[ButlerToolDescriptorRead] = Field(default_factory=list)
    mcp_tools: list[dict[str, Any]] = Field(default_factory=list)
    agents: list[dict[str, Any]] = Field(default_factory=list)
    runtime_agents: list[dict[str, Any]] = Field(default_factory=list)
    tool_profiles: list[dict[str, Any]] = Field(default_factory=list)
    github_accounts: list[dict[str, Any]] = Field(default_factory=list)
    rules: dict[str, Any] = Field(default_factory=dict)
    rule_candidates: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ButlerToolBroker:
    """Resolve shared tool grants for one Butler-routed task."""

    _PRIVATE_ADDRESS_RE = re.compile(
        r"(\d{2,}.*(?:号|室|栋|幢|单元|楼|小区|公寓|路|街|巷|弄|lane|road|street|apt|unit))|"
        r"((?:home|address|住址|家庭地址|公司地址).*\d)",
        flags=re.IGNORECASE,
    )
    _DIGIT_RE = re.compile(r"\d")

    def __init__(self, *, repo_root: Path | None = None, mcp_registry: Any | None = None) -> None:
        self._repo_root = (repo_root or Path(__file__).resolve().parents[4]).resolve()
        self._mcp_registry = mcp_registry
        self._tools_path = self._repo_root / "configs" / "butler" / "tools.yaml"
        self._rules_path = self._repo_root / "configs" / "butler" / "rules.yaml"
        self._rule_candidates_path = self._repo_root / "configs" / "butler" / "rule_candidates.yaml"
        self._tools = self._load_tools()

    def list_tools(self) -> list[ButlerToolDescriptorRead]:
        return sorted(self._tools, key=lambda item: item.tool_id)

    def registry(self) -> ButlerRegistryRead:
        return ButlerRegistryRead(
            tools=self.list_tools(),
            mcp_tools=self._load_mcp_tools(),
            agents=self._load_manifest_dir("configs/agents"),
            runtime_agents=self._load_manifest_dir("configs/runtime_agents"),
            tool_profiles=self._load_manifest_dir("configs/tool_profiles"),
            github_accounts=self._load_manifest_dir("configs/github_accounts"),
            rules=self._load_optional_yaml(self._rules_path),
            rule_candidates=self._load_optional_yaml(self._rule_candidates_path),
            metadata={
                "tools_path": str(self._tools_path),
                "rules_path": str(self._rules_path),
                "rule_candidates_path": str(self._rule_candidates_path),
            },
        )

    def assert_package_tool_registration_allowed(
        self,
        *,
        package_id: str,
        package_stable: bool,
        policy_decision: str | None,
        approval_status: str | None,
    ) -> None:
        normalized_package = str(package_id or "").strip()
        if not normalized_package:
            raise PermissionError("package_id is required for tool registration")
        if not package_stable:
            raise PermissionError("package tool registration requires a certified stable package")
        if policy_decision != "allow":
            raise PermissionError("package tool registration requires PolicyDecision allow")
        if approval_status != "approved":
            raise PermissionError("package tool registration requires approved human approval")

    def resolve(self, request: ButlerToolResolveRequest) -> ButlerToolResolutionRead:
        request = ButlerToolResolveRequest.model_validate(request.model_dump(mode="json"))
        requirements = self._normalize_requirements(request.tool_requirements, request.parameters)
        grants: list[ButlerToolGrantRead] = []
        denied: list[ButlerToolDeniedRead] = []
        risk_tags = set(request.task_risk_tags)
        sanitized_inputs: list[str] = []

        for index, requirement in enumerate(requirements, start=1):
            tool = self._find_tool(requirement.capability)
            if tool is None:
                denied.append(
                    ButlerToolDeniedRead(
                        capability=requirement.capability,
                        reason="tool capability is not registered",
                        audit_summary=requirement.capability,
                    )
                )
                continue

            input_text = self._input_text_for_requirement(requirement, request.parameters)
            sanitized = self._sanitize_input(input_text)
            if sanitized:
                sanitized_inputs.append(sanitized)

            extra_risk = set(tool.risk_tags)
            if self._looks_like_private_location(input_text):
                extra_risk.add("pii_location")

            role_allowed = self._role_allowed(request.actor_role, tool.allowed_roles)
            agent_allowed = self._agent_allowed(request.target_agent, tool.allowed_agents)
            if tool.tier is ButlerToolTier.DESTRUCTIVE:
                denied.append(
                    ButlerToolDeniedRead(
                        capability=requirement.capability,
                        reason="destructive tools are blocked by default",
                        tier=tool.tier,
                        risk_tags=sorted(extra_risk | {"destructive"}),
                        audit_summary=sanitized or requirement.capability,
                    )
                )
                risk_tags.update(extra_risk | {"destructive", "external_api"})
                continue
            if not role_allowed:
                denied.append(
                    ButlerToolDeniedRead(
                        capability=requirement.capability,
                        reason=f"role {request.actor_role or 'unknown'} is not allowed for {tool.tool_id}",
                        tier=tool.tier,
                        risk_tags=sorted(extra_risk | self._tier_risk_tags(tool.tier)),
                        audit_summary=sanitized or requirement.capability,
                    )
                )
                risk_tags.update(extra_risk | self._tier_risk_tags(tool.tier))
                continue
            if not agent_allowed:
                denied.append(
                    ButlerToolDeniedRead(
                        capability=requirement.capability,
                        reason=f"agent {request.target_agent or 'unknown'} is not allowed for {tool.tool_id}",
                        tier=tool.tier,
                        risk_tags=sorted(extra_risk | self._tier_risk_tags(tool.tier)),
                        audit_summary=sanitized or requirement.capability,
                    )
                )
                risk_tags.update(extra_risk | self._tier_risk_tags(tool.tier))
                continue

            grant_risk = extra_risk | self._tier_risk_tags(tool.tier)
            grants.append(
                ButlerToolGrantRead(
                    grant_id=f"grant-{index}-{tool.tool_id.replace('.', '-')}",
                    tool_id=tool.tool_id,
                    capability=tool.capability,
                    provider=tool.provider,
                    tier=tool.tier,
                    target_agent=request.target_agent or "butler_orchestrator",
                    risk_tags=sorted(grant_risk),
                    audit_summary=sanitized or tool.capability,
                    metadata={
                        **tool.metadata,
                        "requested_capability": requirement.capability,
                        "requires_approval": tool.tier is ButlerToolTier.EXTERNAL_WRITE,
                    },
                )
            )
            risk_tags.update(grant_risk)

        if grants and not denied:
            status: Literal["granted", "partial", "denied"] = "granted"
        elif grants:
            status = "partial"
        elif requirements:
            status = "denied"
        else:
            status = "granted"

        return ButlerToolResolutionRead(
            status=status,
            requested_by=request.requested_by or "local-user",
            actor_role=(request.actor_role or "operator").lower(),
            target_agent=request.target_agent or "butler_orchestrator",
            grants=grants,
            denied=denied,
            risk_tags=sorted(risk_tags),
            audit_summary={
                "requirements": [item.capability for item in requirements],
                "sanitized_inputs": sanitized_inputs[:20],
                "grant_count": len(grants),
                "denied_count": len(denied),
            },
            metadata={"strategy": "central_registry_scoped_grants"},
        )

    def _load_tools(self) -> list[ButlerToolDescriptorRead]:
        payload = self._load_optional_yaml(self._tools_path)
        raw_tools = payload.get("tools") if isinstance(payload, dict) else None
        if not isinstance(raw_tools, list):
            return []
        return [ButlerToolDescriptorRead.model_validate(item) for item in raw_tools if isinstance(item, dict)]

    def _load_manifest_dir(self, relative_dir: str) -> list[dict[str, Any]]:
        manifest_dir = self._repo_root / relative_dir
        if not manifest_dir.exists():
            return []
        items: list[dict[str, Any]] = []
        for path in sorted(manifest_dir.glob("*.yaml")):
            try:
                payload = _load_yaml_like(path)
            except Exception as exc:
                items.append({"id": path.stem, "path": str(path), "status": "invalid", "error": str(exc)})
                continue
            items.append(self._safe_manifest_summary(path=path, payload=payload))
        return items

    def _load_mcp_tools(self) -> list[dict[str, Any]]:
        registry = self._mcp_registry
        if registry is None:
            return []
        try:
            descriptors = registry.list_descriptors(domain=CapabilityDomain.MCP)
        except Exception as exc:
            return [{"status": "invalid", "error": str(exc)}]
        tools: list[dict[str, Any]] = []
        for descriptor in descriptors:
            provider = registry.get(descriptor.provider_id)
            if not isinstance(provider, MCPProvider):
                continue
            try:
                provider_tools = provider.list_tools()
            except Exception as exc:
                tools.append(
                    {
                        "provider_id": descriptor.provider_id,
                        "status": "invalid",
                        "error": str(exc),
                    }
                )
                continue
            for tool in provider_tools:
                tools.append(
                    {
                        "provider_id": descriptor.provider_id,
                        "name": tool.name,
                        "description": tool.description,
                        "metadata": tool.metadata,
                    }
                )
        return sorted(tools, key=lambda item: (str(item.get("provider_id") or ""), str(item.get("name") or "")))

    @staticmethod
    def _safe_manifest_summary(*, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
        auth = payload.get("auth") if isinstance(payload.get("auth"), dict) else {}
        return {
            "id": payload.get("id") or payload.get("profile_id") or path.stem,
            "path": str(path),
            "kind": payload.get("kind"),
            "description": payload.get("description"),
            "capabilities": payload.get("capabilities") or [],
            "profile_id": payload.get("profile_id"),
            "provider": payload.get("provider"),
            "auth_envs": {
                key: value
                for key, value in auth.items()
                if str(key).endswith("_env") or str(key) in {"token_env", "fallback_token_env"}
            },
            "metadata": payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
        }

    @staticmethod
    def _load_optional_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return load_yaml_object(path)
        except Exception as exc:
            return {"status": "invalid", "error": str(exc), "path": str(path)}

    def _normalize_requirements(
        self,
        raw_requirements: list[Any],
        parameters: dict[str, Any],
    ) -> list[ButlerToolRequirementRead]:
        source = raw_requirements or parameters.get("tool_requirements") or []
        if isinstance(source, str):
            source = [source]
        out: list[ButlerToolRequirementRead] = []
        for raw in source:
            if isinstance(raw, ButlerToolRequirementRead):
                out.append(raw)
                continue
            if isinstance(raw, str):
                out.append(ButlerToolRequirementRead(capability=raw))
                continue
            if isinstance(raw, dict):
                out.append(ButlerToolRequirementRead.model_validate(raw))
        return out

    def _find_tool(self, capability: str) -> ButlerToolDescriptorRead | None:
        normalized = capability.strip().lower()
        for tool in self._tools:
            candidates = {tool.capability.lower(), tool.tool_id.lower(), *(alias.lower() for alias in tool.aliases)}
            if normalized in candidates:
                return tool
        return None

    def _input_text_for_requirement(
        self,
        requirement: ButlerToolRequirementRead,
        parameters: dict[str, Any],
    ) -> str:
        chunks: list[str] = []
        if requirement.input_text:
            chunks.append(requirement.input_text)
        for key in ("address", "location", "city", "query", "message", "request_text"):
            value = requirement.metadata.get(key) if key in requirement.metadata else parameters.get(key)
            if isinstance(value, str) and value.strip():
                chunks.append(value.strip())
        return " ".join(chunks)

    def _looks_like_private_location(self, text: str) -> bool:
        normalized = text.strip()
        if not normalized:
            return False
        return bool(self._PRIVATE_ADDRESS_RE.search(normalized))

    def _sanitize_input(self, text: str) -> str:
        normalized = " ".join(text.split())
        if not normalized:
            return ""
        redacted = self._DIGIT_RE.sub("#", normalized)
        if len(redacted) > 120:
            return f"{redacted[:117].rstrip()}..."
        return redacted

    def _role_allowed(self, actor_role: str, allowed_roles: list[str]) -> bool:
        role = (actor_role or "unknown").strip().lower() or "unknown"
        allowed = {item.strip().lower() for item in allowed_roles if item.strip()}
        if "*" in allowed:
            return True
        return role in allowed

    @staticmethod
    def _agent_allowed(target_agent: str, allowed_agents: list[str]) -> bool:
        allowed = {item.strip() for item in allowed_agents if item.strip()}
        if "*" in allowed:
            return True
        return (target_agent or "").strip() in allowed

    @staticmethod
    def _tier_risk_tags(tier: ButlerToolTier) -> set[str]:
        if tier is ButlerToolTier.COMMON_READ:
            return set()
        if tier is ButlerToolTier.SENSITIVE_READ:
            return {"sensitive_read"}
        if tier is ButlerToolTier.EXTERNAL_WRITE:
            return {"external_api", "external_write"}
        return {"external_api", "destructive"}
