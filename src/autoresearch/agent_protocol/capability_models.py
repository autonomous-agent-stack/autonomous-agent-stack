from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.agent_protocol.runtime_models import RuntimeRunRead, RuntimeRunRequest
from autoresearch.shared.models import StrictModel


CapabilityKind = Literal["runtime", "tool", "knowledge", "workflow", "federated"]
CapabilityRiskTier = Literal["common_read", "sensitive_read", "external_write", "destructive"]


class CapabilityManifest(StrictModel):
    capability_id: str = Field(..., min_length=1)
    kind: CapabilityKind = "runtime"
    provided_by: str = Field(..., min_length=1)
    display_name: str | None = None
    description: str = ""
    enabled: bool = True
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk_tier: CapabilityRiskTier = "common_read"
    policy_refs: list[str] = Field(default_factory=list)
    artifact_types: list[str] = Field(default_factory=list)
    lease_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("capability_id", "provided_by", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("value is required")
        return normalized


class CapabilityRunRequest(StrictModel):
    task_name: str = Field(..., min_length=1)
    prompt: str | None = None
    session_id: str | None = None
    actor_id: str = "local-user"
    actor_role: str = "member"
    requested_by: str = "local-user"
    timeout_seconds: int = Field(default=900, ge=1, le=7200)
    parameters: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("prompt", "session_id", mode="before")
    @classmethod
    def _strip_optional(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class CapabilityRunRead(StrictModel):
    capability_id: str
    runtime_id: str
    manifest: CapabilityManifest
    runtime_request: RuntimeRunRequest
    runtime_run: RuntimeRunRead
