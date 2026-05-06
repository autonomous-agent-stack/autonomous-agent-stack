from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.shared.models import StrictModel, utc_now


class Stability(str, Enum):
    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"


class CertificationStatus(str, Enum):
    MISSING = "missing"
    PARTIAL = "partial"
    CERTIFIED = "certified"


class StorageProfileKind(str, Enum):
    LOCAL = "local"
    DEV = "dev"
    PRODUCTION = "production"


class PolicyDecisionValue(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class PrincipalType(str, Enum):
    USER = "user"
    SERVICE_ACCOUNT = "service_account"
    RUNTIME = "runtime"
    PEER = "peer"
    SYSTEM = "system"


class ConnectorType(str, Enum):
    RUNTIME_ADAPTER = "runtime_adapter"
    TOOL_CONNECTOR = "tool"
    MODEL_PROVIDER = "model"
    DATA_CONNECTOR = "data"
    MESSAGING_CONNECTOR = "messaging"
    WORKFLOW_CONNECTOR = "workflow"


class GACertificationItemRead(StrictModel):
    item_id: str
    passed: bool = False
    evidence: str | None = None
    notes: str | None = None


class GAStatusRead(StrictModel):
    object_id: str
    object_type: str
    contract_version: str = "ga/v1"
    stability: Stability = Stability.EXPERIMENTAL
    certification_status: CertificationStatus = CertificationStatus.MISSING
    certification_profile: str | None = None
    live_test_command: str | None = None
    production_profile_required: bool = True
    missing_checks: list[str] = Field(default_factory=list)


class PrincipalRead(StrictModel):
    principal_id: str
    principal_type: PrincipalType = PrincipalType.USER
    tenant_id: str = "local"
    organization_id: str | None = None
    workspace_id: str | None = None
    roles: list[str] = Field(default_factory=list)
    resource_scope: str = "*"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecretLeaseRead(StrictModel):
    lease_id: str
    secret_ref: str
    principal_id: str
    scope: str
    purpose: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ModelInvocationRequest(StrictModel):
    provider_id: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    principal: PrincipalRead = Field(default_factory=lambda: PrincipalRead(principal_id="local-user"))
    session_id: str | None = None
    policy_decision_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("provider_id", "model_id", "prompt", mode="before")
    @classmethod
    def _strip_required(cls, value: Any) -> str:
        return str(value or "").strip()


class ModelInvocationRead(StrictModel):
    invocation_id: str
    provider_id: str
    model_id: str
    status: Literal["allowed", "denied", "failed"]
    output: str | None = None
    error: str | None = None
    policy_decision_id: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConnectorDescriptorRead(StrictModel):
    connector_id: str
    connector_type: ConnectorType
    stability: Stability = Stability.EXPERIMENTAL
    secret_scope: str
    requires_policy: bool = True
    requires_audit: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeIsolationPolicyRead(StrictModel):
    profile_id: str = "default_runtime_sandbox"
    filesystem_sandbox: bool = True
    network_egress_policy: Literal["deny_by_default", "policy_required"] = "deny_by_default"
    env_allowlist: list[str] = Field(default_factory=list)
    process_isolation: bool = True
    secret_injection: Literal["lease_only"] = "lease_only"
    artifact_output_directory_only: bool = True
    workspace_mount_policy: Literal["workspace_only", "none"] = "workspace_only"
    deny_dotenv: bool = True
    deny_host_home: bool = True
    docker_sandbox_optional: bool = True


class RuntimeIsolationReportRead(StrictModel):
    runtime_id: str
    stability: Stability = Stability.EXPERIMENTAL
    policy: RuntimeIsolationPolicyRead
    passed: bool
    violations: list[str] = Field(default_factory=list)
    checked_at: datetime = Field(default_factory=utc_now)


class PolicyDecisionRead(StrictModel):
    decision_id: str
    decision: PolicyDecisionValue
    subject: PrincipalRead
    action: str
    resource: str
    reason: str
    risk_tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReleaseGateCheckRead(StrictModel):
    check_id: str
    status: Literal["passed", "failed", "skipped"] = "passed"
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class ReleaseGateReportRead(StrictModel):
    gate_id: str = "evergreen-os-ga-v1"
    status: Literal["passed", "failed"] = "failed"
    checks: list[ReleaseGateCheckRead] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @property
    def failed_checks(self) -> list[ReleaseGateCheckRead]:
        return [check for check in self.checks if check.status == "failed"]

