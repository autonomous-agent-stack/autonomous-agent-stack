from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ScoreDirection(str, Enum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class OptimizationStrategy(str, Enum):
    HILL_CLIMBING = "hill_climbing"
    SIMULATED_ANNEALING = "simulated_annealing"
    GENETIC = "genetic"


class AssistantScope(str, Enum):
    PERSONAL = "personal"
    SHARED = "shared"


class ActorRole(str, Enum):
    OWNER = "owner"
    PARTNER = "partner"
    MEMBER = "member"
    UNKNOWN = "unknown"


class ChatType(str, Enum):
    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"
    UNKNOWN = "unknown"


class MemoryScope(str, Enum):
    SESSION = "session"
    PERSONAL = "personal"
    SHARED = "shared"


class ApprovalRisk(str, Enum):
    READ = "read"
    WRITE = "write"
    EXTERNAL = "external"
    DESTRUCTIVE = "destructive"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OpenClawSessionActorRead(StrictModel):
    user_id: str | None = None
    username: str | None = None
    role: ActorRole = ActorRole.UNKNOWN


class OpenClawSessionChatContextRead(StrictModel):
    chat_id: str | None = None
    chat_type: ChatType = ChatType.UNKNOWN
    user_id: str | None = None
    message_id: str | None = None


class EvaluatorCommand(StrictModel):
    command: list[str] = Field(..., min_length=1)
    timeout_seconds: int = Field(default=300, ge=1)
    work_dir: str | None = None
    env: dict[str, str] = Field(default_factory=dict)


class EvaluationCreateRequest(StrictModel):
    task_name: str = Field(..., min_length=1)
    config_path: str = "task.json"
    description: str = "manual run"
    evaluator_command: EvaluatorCommand | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evaluator_command", mode="before")
    @classmethod
    def normalize_evaluator_command(cls, value: Any) -> Any:
        if isinstance(value, list):
            return {"command": value}
        return value


class EvaluationRead(StrictModel):
    evaluation_id: str
    task_name: str
    config_path: str
    description: str
    status: JobStatus
    result_status: str | None = None
    run_id: str | None = None
    score: float | None = None
    summary: str | None = None
    duration_seconds: float | None = None
    artifact_dir: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ExecutionCreateRequest(StrictModel):
    name: str = Field(..., min_length=1)
    command: list[str] = Field(..., min_length=1)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    work_dir: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionRead(StrictModel):
    execution_id: str
    name: str
    status: JobStatus
    command: list[str] = Field(default_factory=list)
    timeout_seconds: int
    work_dir: str | None = None
    returncode: int | None = None
    stdout_preview: str | None = None
    stderr_preview: str | None = None
    duration_seconds: float | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class OpenClawSessionCreateRequest(StrictModel):
    channel: str = "api"
    external_id: str | None = None
    title: str = "openclaw-session"
    scope: AssistantScope = AssistantScope.PERSONAL
    session_key: str | None = None
    assistant_id: str | None = None
    actor: OpenClawSessionActorRead | None = None
    chat_context: OpenClawSessionChatContextRead | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpenClawSessionEventAppendRequest(StrictModel):
    role: Literal["system", "user", "assistant", "tool", "status"] = "status"
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpenClawSessionRead(StrictModel):
    session_id: str
    channel: str
    external_id: str | None = None
    title: str
    scope: AssistantScope = AssistantScope.PERSONAL
    session_key: str | None = None
    assistant_id: str | None = None
    actor: OpenClawSessionActorRead | None = None
    chat_context: OpenClawSessionChatContextRead | None = None
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class OpenClawMemoryRecordCreateRequest(StrictModel):
    content: str = Field(..., min_length=1)
    scope: MemoryScope | None = None
    source: str = "manual"
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpenClawMemoryRecordRead(StrictModel):
    memory_id: str
    scope: MemoryScope
    content: str
    source: str
    session_id: str | None = None
    session_key: str | None = None
    assistant_id: str | None = None
    actor_user_id: str | None = None
    actor_role: ActorRole = ActorRole.UNKNOWN
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class OpenClawMemoryBundleRead(StrictModel):
    session_id: str
    session_scope: AssistantScope
    session_key: str | None = None
    assistant_id: str | None = None
    actor_user_id: str | None = None
    session_events: list[dict[str, Any]] = Field(default_factory=list)
    personal_memories: list[OpenClawMemoryRecordRead] = Field(default_factory=list)
    shared_memories: list[OpenClawMemoryRecordRead] = Field(default_factory=list)


class ApprovalRequestCreateRequest(StrictModel):
    title: str = Field(..., min_length=1)
    summary: str = ""
    risk: ApprovalRisk = ApprovalRisk.WRITE
    source: str = "manual"
    telegram_uid: str | None = None
    session_id: str | None = None
    agent_run_id: str | None = None
    assistant_scope: AssistantScope | None = None
    expires_in_seconds: int = Field(default=3600, ge=60, le=604800)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecisionRequest(StrictModel):
    decision: Literal["approved", "rejected"]
    decided_by: str = Field(..., min_length=1)
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalNoteRequest(StrictModel):
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalRequestRead(StrictModel):
    approval_id: str
    title: str
    summary: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    risk: ApprovalRisk = ApprovalRisk.WRITE
    source: str = "manual"
    telegram_uid: str | None = None
    session_id: str | None = None
    agent_run_id: str | None = None
    assistant_scope: AssistantScope | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    resolved_at: datetime | None = None
    decided_by: str | None = None
    decision_note: str | None = None


class OpenClawSessionSkillLoadRequest(StrictModel):
    skill_names: list[str] = Field(..., min_length=1)
    merge: bool = True


class OpenClawSkillRead(StrictModel):
    name: str
    skill_key: str
    description: str = ""
    source: str
    base_dir: str
    file_path: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpenClawSkillDetailRead(OpenClawSkillRead):
    content: str


class IntegrationDiscoverRequest(StrictModel):
    source_url: str = Field(..., min_length=1)
    source_kind: Literal["repository", "api_docs", "mixed"] = "repository"
    ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegrationDiscoveryRead(StrictModel):
    discovery_id: str
    source_url: str
    source_kind: str
    ref: str | None = None
    status: JobStatus
    candidate_adapter_id: str
    detected_capabilities: list[str] = Field(default_factory=list)
    summary: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class DependencyRequest(StrictModel):
    package: str = Field(..., min_length=1)
    version_spec: str = ""
    reason: str = ""
    ecosystem: Literal["pypi"] = "pypi"

    @field_validator("package")
    @classmethod
    def normalize_package(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", normalized):
            raise ValueError("package must contain lowercase letters, numbers, dot, dash or underscore")
        return normalized

    @field_validator("version_spec")
    @classmethod
    def normalize_version_spec(cls, value: str) -> str:
        return value.strip()


class SecureDependencyArtifactRead(StrictModel):
    package: str = Field(..., min_length=1)
    version_spec: str = ""
    wheel_filename: str = Field(..., min_length=1)
    sha256: str = Field(..., min_length=64, max_length=64)
    source_index: str = "https://pypi.org/simple"

    @field_validator("package")
    @classmethod
    def normalize_package(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]*", normalized):
            raise ValueError("package must contain lowercase letters, numbers, dot, dash or underscore")
        return normalized

    @field_validator("version_spec")
    @classmethod
    def normalize_version_spec(cls, value: str) -> str:
        return value.strip()

    @field_validator("sha256")
    @classmethod
    def normalize_sha256(cls, value: str) -> str:
        digest = value.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("sha256 must be a 64-char hexadecimal digest")
        return digest


class SecureFetchPlanRead(StrictModel):
    request_id: str = ""
    status: Literal["pending", "audited", "rejected", "skipped"] = "skipped"
    network_access: Literal["host_proxy_only"] = "host_proxy_only"
    audit_commands: list[str] = Field(default_factory=list)
    audit_notes: list[str] = Field(default_factory=list)
    readonly_mount_dir: str = "/opt/secure-deps"
    artifacts: list[SecureDependencyArtifactRead] = Field(default_factory=list)
    sbom: dict[str, Any] = Field(default_factory=dict)
    hash_manifest: dict[str, str] = Field(default_factory=dict)
    trace_id: str = ""
    policy_version: str = "sep-v1"
    audited_at: datetime | None = None

    @field_validator("hash_manifest")
    @classmethod
    def normalize_hash_manifest(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for package, digest_raw in value.items():
            digest = digest_raw.strip().lower()
            if not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise ValueError(f"hash_manifest[{package}] must be a 64-char hexadecimal digest")
            normalized[package] = digest
        return normalized


class OfflineSandboxPolicyRead(StrictModel):
    network: Literal["none"] = "none"
    readonly_mounts: list[str] = Field(default_factory=lambda: ["/opt/secure-deps"])
    restricted_capabilities: list[str] = Field(
        default_factory=lambda: ["NET_ADMIN", "SYS_ADMIN", "SYS_PTRACE"]
    )
    allow_secrets: bool = False


class EvaluationGateRead(StrictModel):
    required_checks: list[str] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    status: Literal["pending", "passed", "failed"] = "pending"


class IntegrationPrototypeRequest(StrictModel):
    discovery_id: str = Field(..., min_length=1)
    adapter_name: str = Field(..., min_length=1)
    sandbox_backend: Literal["docker", "colima", "mock"] = "docker"
    dry_run: bool = True
    dependency_requests: list[DependencyRequest] = Field(default_factory=list)
    policy_version: str = "sep-v1"
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegrationPrototypeRead(StrictModel):
    prototype_id: str
    discovery_id: str
    adapter_name: str
    sandbox_backend: str
    dry_run: bool
    status: JobStatus
    dependency_requests: list[DependencyRequest] = Field(default_factory=list)
    secure_fetch_plan: SecureFetchPlanRead = Field(default_factory=SecureFetchPlanRead)
    offline_sandbox_policy: OfflineSandboxPolicyRead = Field(default_factory=OfflineSandboxPolicyRead)
    evaluation_gate: EvaluationGateRead = Field(default_factory=EvaluationGateRead)
    trace_id: str = ""
    planned_files: list[str] = Field(default_factory=list)
    validation_checks: list[str] = Field(default_factory=list)
    summary: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class IntegrationSecureFetchRequest(StrictModel):
    audited_artifacts: list[SecureDependencyArtifactRead] = Field(default_factory=list)
    auditor: str = Field(default="security_auditor", min_length=1)
    policy_version: str = "sep-v1"
    sbom: dict[str, Any] = Field(default_factory=dict)
    hash_manifest: dict[str, str] = Field(default_factory=dict)
    mount_dir: str | None = None
    notes: list[str] = Field(default_factory=list)


class IntegrationPromoteRequest(StrictModel):
    prototype_id: str = Field(..., min_length=1)
    rollout_mode: Literal["shadow", "canary", "full"] = "shadow"
    evaluation_results: dict[str, bool] = Field(default_factory=dict)
    approval_mode: Literal["manual", "auto_if_green"] = "manual"
    metadata: dict[str, Any] = Field(default_factory=dict)


class IntegrationPromotionRead(StrictModel):
    promotion_id: str
    prototype_id: str
    rollout_mode: str
    status: JobStatus
    decision: Literal["pending", "approved", "rejected"] = "pending"
    gate_status: Literal["pending", "passed", "failed"] = "pending"
    required_checks: list[str] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    missing_checks: list[str] = Field(default_factory=list)
    trace_id: str = ""
    topology_patch_preview: dict[str, Any] = Field(default_factory=dict)
    rollback_plan: list[str] = Field(default_factory=list)
    summary: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class AdminAgentConfigCreateRequest(StrictModel):
    name: str = Field(..., min_length=1)
    description: str = ""
    task_name: str = Field(..., min_length=1)
    prompt_template: str = Field(..., min_length=1)
    default_timeout_seconds: int = Field(default=900, ge=1, le=7200)
    default_generation_depth: int = Field(default=1, ge=1, le=10)
    default_env: dict[str, str] = Field(default_factory=dict)
    cli_args: list[str] = Field(default_factory=list)
    command_override: list[str] | None = None
    append_prompt: bool = True
    channel_bindings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    actor: str = "admin_api"


class AdminAgentConfigUpdateRequest(StrictModel):
    name: str | None = None
    description: str | None = None
    task_name: str | None = None
    prompt_template: str | None = None
    default_timeout_seconds: int | None = Field(default=None, ge=1, le=7200)
    default_generation_depth: int | None = Field(default=None, ge=1, le=10)
    default_env: dict[str, str] | None = None
    cli_args: list[str] | None = None
    command_override: list[str] | None = None
    append_prompt: bool | None = None
    channel_bindings: list[str] | None = None
    metadata_updates: dict[str, Any] = Field(default_factory=dict)
    actor: str = "admin_api"
    reason: str | None = None


class AdminAgentConfigRead(StrictModel):
    agent_id: str
    version: int = Field(default=1, ge=1)
    status: Literal["active", "inactive"] = "active"
    name: str
    description: str = ""
    task_name: str
    prompt_template: str
    default_timeout_seconds: int
    default_generation_depth: int
    default_env: dict[str, str] = Field(default_factory=dict)
    cli_args: list[str] = Field(default_factory=list)
    command_override: list[str] | None = None
    append_prompt: bool = True
    channel_bindings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AdminChannelConfigCreateRequest(StrictModel):
    key: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    provider: Literal["telegram", "webhook", "http", "custom"] = "telegram"
    endpoint_url: str | None = None
    secret_ref: str | None = None
    secret_value: str | None = None
    allowed_chat_ids: list[str] = Field(default_factory=list)
    allowed_user_ids: list[str] = Field(default_factory=list)
    routing_policy: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True
    actor: str = "admin_api"


class AdminChannelConfigUpdateRequest(StrictModel):
    display_name: str | None = None
    provider: Literal["telegram", "webhook", "http", "custom"] | None = None
    endpoint_url: str | None = None
    secret_ref: str | None = None
    secret_value: str | None = None
    clear_secret: bool = False
    allowed_chat_ids: list[str] | None = None
    allowed_user_ids: list[str] | None = None
    routing_policy: dict[str, Any] | None = None
    metadata_updates: dict[str, Any] = Field(default_factory=dict)
    actor: str = "admin_api"
    reason: str | None = None


class AdminChannelConfigRead(StrictModel):
    channel_id: str
    version: int = Field(default=1, ge=1)
    status: Literal["active", "inactive"] = "active"
    key: str
    display_name: str
    provider: Literal["telegram", "webhook", "http", "custom"] = "telegram"
    endpoint_url: str | None = None
    secret_ref: str | None = None
    allowed_chat_ids: list[str] = Field(default_factory=list)
    allowed_user_ids: list[str] = Field(default_factory=list)
    routing_policy: dict[str, Any] = Field(default_factory=dict)
    has_secret: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class AdminSecretRecordRead(StrictModel):
    secret_id: str
    scope: Literal["channel"] = "channel"
    scope_id: str
    status: Literal["active", "deleted"] = "active"
    algorithm: Literal["fernet-v1"] = "fernet-v1"
    ciphertext: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminConfigRevisionRead(StrictModel):
    revision_id: str
    target_type: Literal["agent", "channel"]
    target_id: str
    version: int = Field(..., ge=1)
    action: Literal["create", "update", "activate", "deactivate", "rollback"]
    actor: str = "admin_api"
    reason: str | None = None
    snapshot: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AdminConfigRollbackRequest(StrictModel):
    version: int = Field(..., ge=1)
    reason: str = "manual rollback"
    actor: str = "admin_api"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminAgentLaunchRequest(StrictModel):
    session_id: str | None = None
    prompt_override: str | None = None
    timeout_seconds_override: int | None = Field(default=None, ge=1, le=7200)
    generation_depth_override: int | None = Field(default=None, ge=1, le=10)
    env_overrides: dict[str, str] = Field(default_factory=dict)
    metadata_updates: dict[str, Any] = Field(default_factory=dict)


class AdminConfigStatusChangeRequest(StrictModel):
    actor: str = "admin_api"
    reason: str | None = None


class AdminTokenIssueRequest(StrictModel):
    subject: str = Field(default="admin-local", min_length=1)
    roles: list[Literal["viewer", "editor", "admin", "owner"]] = Field(
        default_factory=lambda: ["admin"]
    )
    ttl_seconds: int | None = Field(default=None, ge=60, le=86400)


class AdminTokenRead(StrictModel):
    token: str
    token_type: Literal["Bearer"] = "Bearer"
    subject: str
    roles: list[str] = Field(default_factory=list)
    issued_at: datetime
    expires_at: datetime


class ClaudeAgentCreateRequest(StrictModel):
    task_name: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    agent_name: str | None = None
    session_id: str | None = None
    parent_agent_id: str | None = None
    generation_depth: int = Field(default=1, ge=1, le=10)
    timeout_seconds: int = Field(default=900, ge=1, le=7200)
    work_dir: str | None = None
    cli_args: list[str] = Field(default_factory=list)
    command_override: list[str] | None = None
    append_prompt: bool = True
    skill_names: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)  # 新增图片字段（URL 或路径）
    env: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaudeAgentRunRead(StrictModel):
    agent_run_id: str
    task_name: str
    prompt: str
    images: list[str] = Field(default_factory=list)  # 新增图片字段
    status: JobStatus
    agent_name: str | None = None
    session_id: str | None = None
    parent_agent_id: str | None = None
    generation_depth: int
    command: list[str] = Field(default_factory=list)
    timeout_seconds: int
    work_dir: str | None = None
    returncode: int | None = None
    stdout_preview: str | None = None
    stderr_preview: str | None = None
    duration_seconds: float | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class PanelMagicLinkRead(StrictModel):
    url: str
    telegram_uid: str
    expires_at: datetime


class PanelAuditLogRead(StrictModel):
    audit_id: str
    telegram_uid: str
    action: Literal["cancel", "retry", "approve", "reject"]
    target_type: Literal["agent_run", "approval_request"] = "agent_run"
    target_id: str
    status: Literal["accepted", "rejected", "failed"] = "accepted"
    reason: str | None = None
    request_ip: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CapabilityProviderSummaryRead(StrictModel):
    provider_id: str
    domain: str
    display_name: str
    status: str
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminCapabilityToolRead(StrictModel):
    name: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminCapabilityProviderInventoryRead(StrictModel):
    provider: CapabilityProviderSummaryRead
    skills: list[OpenClawSkillRead] = Field(default_factory=list)
    tools: list[AdminCapabilityToolRead] = Field(default_factory=list)
    supports_calendar_query: bool = False
    supports_github_search: bool = False


class AdminCapabilitySnapshotRead(StrictModel):
    providers: list[AdminCapabilityProviderInventoryRead] = Field(default_factory=list)
    issued_at: datetime


class PanelStateRead(StrictModel):
    telegram_uid: str
    sessions: list[OpenClawSessionRead] = Field(default_factory=list)
    agent_runs: list[ClaudeAgentRunRead] = Field(default_factory=list)
    audit_logs: list[PanelAuditLogRead] = Field(default_factory=list)
    capability_providers: list[CapabilityProviderSummaryRead] = Field(default_factory=list)
    pending_approvals: list[ApprovalRequestRead] = Field(default_factory=list)
    issued_at: datetime


class TelegramWebhookAck(StrictModel):
    accepted: bool
    update_id: int | None = None
    chat_id: str | None = None
    session_id: str | None = None
    agent_run_id: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaudeAgentCancelRequest(StrictModel):
    reason: str = "cancelled by user"


class ClaudeAgentRetryRequest(StrictModel):
    reason: str = "manual retry"
    prompt_override: str | None = None
    timeout_seconds_override: int | None = Field(default=None, ge=1, le=7200)
    metadata_updates: dict[str, Any] = Field(default_factory=dict)


class ClaudeAgentTreeEdgeRead(StrictModel):
    parent_agent_run_id: str
    child_agent_run_id: str


class ClaudeAgentTreeNodeRead(StrictModel):
    agent_run_id: str
    parent_agent_id: str | None = None
    session_id: str | None = None
    task_name: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    children: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaudeAgentTreeRead(StrictModel):
    session_id: str | None = None
    root_agent_run_ids: list[str] = Field(default_factory=list)
    nodes: list[ClaudeAgentTreeNodeRead] = Field(default_factory=list)
    edges: list[ClaudeAgentTreeEdgeRead] = Field(default_factory=list)
    mermaid: str = ""


class OpenVikingCompactRequest(StrictModel):
    keep_recent_events: int = Field(default=12, ge=1, le=200)
    summary_max_chars: int = Field(default=1200, ge=200, le=20000)


class OpenVikingMemoryProfileRead(StrictModel):
    session_id: str
    original_event_count: int
    retained_event_count: int
    compressed_event_count: int
    estimated_tokens_before: int
    estimated_tokens_after: int
    compression_ratio: float
    summary: str
    updated_at: datetime


class MiroFishPredictionRequest(StrictModel):
    task_name: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MiroFishPredictionRead(StrictModel):
    engine: str
    score: float = Field(..., ge=0.0, le=1.0)
    decision: Literal["allow", "review", "reject"]
    reasons: list[str] = Field(default_factory=list)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportCreateRequest(StrictModel):
    evaluation_id: str | None = None
    experiment_id: str | None = None
    format: Literal["markdown", "json", "html"] = "markdown"
    sections: list[str] = Field(
        default_factory=lambda: ["summary", "metrics", "recommendations"]
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportRead(StrictModel):
    report_id: str
    evaluation_id: str | None = None
    experiment_id: str | None = None
    status: JobStatus
    format: str
    content: str
    sections: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class VariantCreateRequest(StrictModel):
    experiment_id: str | None = None
    base_prompt: str = Field(..., min_length=1)
    strategy_hint: str = "baseline"
    max_variants: int = Field(default=3, ge=1, le=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VariantRead(StrictModel):
    variant_id: str
    experiment_id: str | None = None
    status: JobStatus
    base_prompt: str
    strategy_hint: str
    content: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizationCreateRequest(StrictModel):
    experiment_id: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    strategy: OptimizationStrategy = OptimizationStrategy.HILL_CLIMBING
    max_iterations: int = Field(default=10, ge=1, le=1000)
    early_stop_patience: int = Field(default=3, ge=0, le=100)
    rollback_on_regression: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizationRead(StrictModel):
    optimization_id: str
    experiment_id: str
    objective: str
    strategy: OptimizationStrategy
    max_iterations: int
    early_stop_patience: int
    rollback_on_regression: bool
    status: JobStatus
    best_variant_id: str | None = None
    best_score: float | None = None
    last_score: float | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentCreateRequest(StrictModel):
    name: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    mutable_paths: list[str] = Field(default_factory=list)
    evaluation_command: list[str] = Field(default_factory=list)
    score_direction: ScoreDirection = ScoreDirection.MAXIMIZE
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentRead(StrictModel):
    experiment_id: str
    name: str
    problem_statement: str
    mutable_paths: list[str] = Field(default_factory=list)
    evaluation_command: list[str] = Field(default_factory=list)
    score_direction: ScoreDirection
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptOrchestrationExecuteRequest(StrictModel):
    prompt: str = Field(..., min_length=1)
    graph_id: str | None = None
    goal: str | None = None
    max_steps: int | None = Field(default=None, ge=1, le=256)
    max_concurrency: int | None = Field(default=None, ge=1, le=32)
    context: dict[str, Any] = Field(default_factory=dict)
    include_graph: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptOrchestrationExecutionRead(StrictModel):
    graph_id: str
    status: Literal["completed", "failed"]
    goal: str
    max_steps: int
    max_concurrency: int
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    results: dict[str, Any] = Field(default_factory=dict)
    graph: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
