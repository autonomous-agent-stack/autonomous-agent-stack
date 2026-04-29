from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    CANCELLED = "cancelled"


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


class ManagedSkillInstallStatus(str, Enum):
    PENDING = "pending"
    QUARANTINED = "quarantined"
    COLD_VALIDATED = "cold_validated"
    PROMOTED = "promoted"
    REJECTED = "rejected"


class GitPromotionMode(str, Enum):
    PATCH = "patch"
    DRAFT_PR = "draft_pr"


class PromotionActorRole(str, Enum):
    AGGREGATOR = "aggregator"
    WORKER = "worker"


class PromotionGateCheck(StrictModel):
    id: str
    passed: bool
    detail: str = ""


class PromotionDiffStats(StrictModel):
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    patch_lines: int = 0


class GitRemoteProbe(StrictModel):
    remote_name: str | None = None
    remote_url: str | None = None
    healthy: bool = False
    credentials_available: bool = False
    base_branch_exists: bool = False
    reason: str | None = None


class PromotionIntent(StrictModel):
    run_id: str = Field(..., min_length=1)
    actor_role: PromotionActorRole = PromotionActorRole.AGGREGATOR
    actor_id: str = "aggregator"
    writer_id: str | None = None
    writer_lease_key: str | None = None
    patch_uri: str = Field(..., min_length=1)
    changed_files: list[str] = Field(default_factory=list)
    base_ref: str | None = None
    preferred_mode: GitPromotionMode = GitPromotionMode.PATCH
    target_base_branch: str = "main"
    approval_granted: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromotionPreflight(StrictModel):
    run_id: str
    requested_mode: GitPromotionMode
    effective_mode: GitPromotionMode | None = None
    allowed: bool = False
    remote_probe: GitRemoteProbe = Field(default_factory=GitRemoteProbe)
    checks: list[PromotionGateCheck] = Field(default_factory=list)
    reason: str | None = None


class PromotionResult(StrictModel):
    run_id: str
    success: bool = False
    mode: GitPromotionMode | None = None
    patch_uri: str | None = None
    branch_name: str | None = None
    commit_sha: str | None = None
    pr_url: str | None = None
    base_ref: str | None = None
    target_base_branch: str | None = None
    changed_files: list[str] = Field(default_factory=list)
    diff_stats: PromotionDiffStats = Field(default_factory=PromotionDiffStats)
    finalized_by: str = "aggregator"
    checks: list[PromotionGateCheck] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpenClawSessionActorRead(StrictModel):
    user_id: str | None = None
    username: str | None = None
    role: ActorRole = ActorRole.UNKNOWN


class OpenClawSessionChatContextRead(StrictModel):
    chat_id: str | None = None
    chat_type: ChatType = ChatType.UNKNOWN
    user_id: str | None = None
    message_id: str | None = None
    message_thread_id: str | None = None
    is_topic_message: bool = False
    reply_to_message_id: str | None = None


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


class ManagedSkillCheck(StrictModel):
    id: str
    passed: bool
    detail: str = ""


class ManagedSkillManifestFileRead(StrictModel):
    path: str = Field(..., min_length=1)
    sha256: str = Field(..., min_length=64, max_length=64)

    @field_validator("path")
    @classmethod
    def _validate_relative_path(cls, value: str) -> str:
        normalized = value.strip().replace("\\", "/")
        if not normalized or normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
            raise ValueError("managed skill file paths must be relative to the bundle root")
        return normalized

    @field_validator("sha256")
    @classmethod
    def _validate_sha256(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", normalized):
            raise ValueError("managed skill file sha256 must be 64 lowercase hex characters")
        return normalized


class ManagedSkillManifestRead(StrictModel):
    schema_version: Literal["managed-skill/v1"] = "managed-skill/v1"
    skill_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    description: str = ""
    entrypoint: str = "SKILL.md"
    signer_id: str = Field(..., min_length=1)
    signature: str = Field(..., min_length=1)
    capabilities: list[str] = Field(default_factory=list)
    files: list[ManagedSkillManifestFileRead] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("skill_id")
    @classmethod
    def _validate_skill_id(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", normalized):
            raise ValueError("managed skill_id must use lowercase letters, digits, dot, underscore, or hyphen")
        return normalized

    @field_validator("version")
    @classmethod
    def _validate_version(cls, value: str) -> str:
        normalized = value.strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][A-Za-z0-9._-]+)?", normalized):
            raise ValueError("managed skill version must be semver-like, for example 1.2.3")
        return normalized

    @field_validator("entrypoint")
    @classmethod
    def _validate_entrypoint(cls, value: str) -> str:
        normalized = value.strip().replace("\\", "/")
        if normalized != "SKILL.md":
            raise ValueError("managed skill entrypoint must be SKILL.md")
        return normalized

    @field_validator("capabilities")
    @classmethod
    def _dedupe_capabilities(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            candidate = item.strip()
            if not candidate:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
        return normalized


class ManagedSkillInstallRequest(StrictModel):
    bundle_dir: str = Field(..., min_length=1)
    requested_by: str = Field(default="manual", min_length=1)
    allow_update: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ManagedSkillAuditEventRead(StrictModel):
    stage: str
    status: Literal["ok", "failed", "skipped"] = "ok"
    message: str = ""
    created_at: datetime


class ManagedSkillRuntimeStateRead(StrictModel):
    install_id: str = Field(..., min_length=1)
    skill_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    status: ManagedSkillInstallStatus
    updated_at: datetime


class ManagedSkillInstallRead(StrictModel):
    install_id: str
    status: ManagedSkillInstallStatus = ManagedSkillInstallStatus.PENDING
    skill_id: str
    version: str
    requested_by: str = "manual"
    manifest: ManagedSkillManifestRead
    quarantine_dir: str | None = None
    active_dir: str | None = None
    checks: list[ManagedSkillCheck] = Field(default_factory=list)
    audit_events: list[ManagedSkillAuditEventRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


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
    action: Literal["cancel", "retry", "approve", "reject", "dispatch"]
    target_type: Literal["agent_run", "approval_request", "autoresearch_plan"] = "agent_run"
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


class AdminManagedSkillStatusGroupRead(StrictModel):
    status: ManagedSkillInstallStatus
    installs: list[ManagedSkillInstallRead] = Field(default_factory=list)


class AdminManagedSkillStatusSnapshotRead(StrictModel):
    groups: list[AdminManagedSkillStatusGroupRead] = Field(default_factory=list)
    issued_at: datetime


class AdminManagedSkillPromotionRequest(StrictModel):
    telegram_uid: str | None = None
    note: str | None = None
    expires_in_seconds: int = Field(default=3600, ge=60, le=604800)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminManagedSkillPromotionRequestRead(StrictModel):
    install: ManagedSkillInstallRead
    approval: ApprovalRequestRead
    mini_app_url: str | None = None
    notification_sent: bool = False


class AdminManagedSkillPromotionExecuteRequest(StrictModel):
    approval_id: str = Field(..., min_length=1)
    action_nonce: str = Field(..., min_length=1)
    action_hash: str = Field(..., min_length=64, max_length=64)
    action_issued_at: str = Field(..., min_length=1)
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminAgentAuditRole(str, Enum):
    MANAGER = "manager"
    PLANNER = "planner"
    WORKER = "worker"


class AdminAgentAuditTrailEntryRead(StrictModel):
    entry_id: str
    source: Literal["manager_task", "autoresearch_plan", "claude_agent", "runtime_artifact"]
    agent_role: AdminAgentAuditRole = AdminAgentAuditRole.WORKER
    run_id: str
    agent_id: str | None = None
    title: str
    status: str
    final_status: str | None = None
    recorded_at: datetime
    duration_ms: int | None = None
    first_progress_ms: int | None = None
    first_scoped_write_ms: int | None = None
    first_state_heartbeat_ms: int | None = None
    files_changed: int = 0
    changed_paths: list[str] = Field(default_factory=list)
    scope_paths: list[str] = Field(default_factory=list)
    patch_uri: str | None = None
    isolated_workspace: str | None = None
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdminAgentAuditTrailStatsRead(StrictModel):
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    running: int = 0
    queued: int = 0
    review_required: int = 0


class AdminAgentAuditTrailSnapshotRead(StrictModel):
    items: list[AdminAgentAuditTrailEntryRead] = Field(default_factory=list)
    stats: AdminAgentAuditTrailStatsRead = Field(default_factory=AdminAgentAuditTrailStatsRead)
    issued_at: datetime


class AdminAgentAuditTrailDetailRead(StrictModel):
    entry: AdminAgentAuditTrailEntryRead
    input_prompt: str | None = None
    job_spec: dict[str, Any] = Field(default_factory=dict)
    worker_spec: dict[str, Any] = Field(default_factory=dict)
    controlled_request: dict[str, Any] = Field(default_factory=dict)
    patch_text: str = ""
    patch_truncated: bool = False
    error_reason: str | None = None
    traceback: str | None = None
    raw_record: dict[str, Any] = Field(default_factory=dict)


class PanelStateRead(StrictModel):
    telegram_uid: str
    sessions: list[OpenClawSessionRead] = Field(default_factory=list)
    agent_runs: list[ClaudeAgentRunRead] = Field(default_factory=list)
    audit_logs: list[PanelAuditLogRead] = Field(default_factory=list)
    capability_providers: list[CapabilityProviderSummaryRead] = Field(default_factory=list)
    pending_approvals: list[ApprovalRequestRead] = Field(default_factory=list)
    pending_autoresearch_plans: list[dict[str, Any]] = Field(default_factory=list)
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


class YouTubeTargetKind(str, Enum):
    CHANNEL = "channel"
    VIDEO = "video"
    PLAYLIST = "playlist"
    UNKNOWN = "unknown"


class YouTubeSubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DELETED = "deleted"


class YouTubeTranscriptSource(str, Enum):
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    MISSING = "missing"


class YouTubeResultKind(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    NOOP = "noop"
    FAILED = "failed"


class YouTubeFailureKind(str, Enum):
    UNSUPPORTED_SOURCE_OR_PARSE_FAILED = "unsupported_source_or_parse_failed"
    NO_NEW_VIDEOS_FOUND = "no_new_videos_found"
    VIDEO_UNAVAILABLE = "video_unavailable"
    TRANSCRIPT_UNAVAILABLE = "transcript_unavailable"
    RATE_LIMITED = "rate_limited"
    AUTO_CAPTIONS_ONLY = "auto_captions_only"
    SUBTITLE_LANGUAGE_MISMATCH = "subtitle_language_mismatch"
    YT_DLP_EXTRACTOR_FAILURE = "yt_dlp_extractor_failure"
    NETWORK_FAILURE = "network_failure"
    TIMEOUT_FAILURE = "timeout_failure"
    DUPLICATE_IDEMPOTENT_NOOP = "duplicate_idempotent_noop"
    ASK_CONTEXT_MISSING = "ask_context_missing"


class YouTubeFailedStage(str, Enum):
    DISCOVERY = "discovery"
    METADATA_FETCH = "metadata_fetch"
    TRANSCRIPT_FETCH = "transcript_fetch"
    DIGEST_BUILD = "digest_build"
    ASK = "ask"


class YouTubeRunKind(str, Enum):
    SUBSCRIPTION_CHECK = "subscription_check"
    VIDEO_METADATA_REFRESH = "video_metadata_refresh"
    TRANSCRIPT_FETCH = "transcript_fetch"
    DIGEST_GENERATE = "digest_generate"
    QUESTION_ANSWER = "question_answer"


class YouTubeSubscriptionCreateRequest(StrictModel):
    source_url: str = Field(..., min_length=1)
    title: str | None = None
    auto_fetch_transcript: bool = True
    auto_digest: bool = True
    poll_interval_minutes: int = Field(default=60, ge=5, le=10080)
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeSubscriptionUpdateRequest(StrictModel):
    title: str | None = None
    status: YouTubeSubscriptionStatus | None = None
    auto_fetch_transcript: bool | None = None
    auto_digest: bool | None = None
    poll_interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeSubscriptionCheckRequest(StrictModel):
    force: bool = False
    limit: int = Field(default=5, ge=1, le=50)
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeTranscriptCreateRequest(StrictModel):
    preferred_languages: list[str] = Field(
        default_factory=lambda: ["zh-Hans", "zh-CN", "en"]
    )
    include_auto_generated: bool = True
    overwrite_existing: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeDigestCreateRequest(StrictModel):
    format: Literal["markdown", "json"] = "markdown"
    overwrite_existing: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeQuestionRequest(StrictModel):
    question: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeSubscriptionImportItem(StrictModel):
    source_url: str = Field(..., min_length=1)
    title: str | None = None
    status: YouTubeSubscriptionStatus = YouTubeSubscriptionStatus.ACTIVE
    auto_fetch_transcript: bool = True
    auto_digest: bool = True
    poll_interval_minutes: int = Field(default=60, ge=5, le=10080)
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeSubscriptionImportRequest(StrictModel):
    subscriptions: list[YouTubeSubscriptionImportItem] = Field(default_factory=list)


class YouTubeSubscriptionRead(StrictModel):
    subscription_id: str
    source_url: str
    normalized_url: str
    target_kind: YouTubeTargetKind
    external_id: str | None = None
    title: str | None = None
    status: YouTubeSubscriptionStatus = YouTubeSubscriptionStatus.ACTIVE
    auto_fetch_transcript: bool = True
    auto_digest: bool = True
    poll_interval_minutes: int = 60
    latest_video_id: str | None = None
    last_checked_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeVideoRead(StrictModel):
    video_id: str
    source_url: str
    subscription_id: str | None = None
    channel_id: str | None = None
    channel_title: str | None = None
    title: str | None = None
    description: str | None = None
    published_at: datetime | None = None
    duration_seconds: int | None = None
    status: JobStatus = JobStatus.CREATED
    transcript_id: str | None = None
    digest_id: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeTranscriptRead(StrictModel):
    transcript_id: str
    video_id: str
    language: str
    source: YouTubeTranscriptSource = YouTubeTranscriptSource.MISSING
    status: JobStatus = JobStatus.CREATED
    result_kind: YouTubeResultKind = YouTubeResultKind.SUCCESS
    failure_kind: YouTubeFailureKind | None = None
    failed_stage: YouTubeFailedStage | None = None
    reason: str | None = None
    content: str = ""
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeDigestRead(StrictModel):
    digest_id: str
    video_id: str
    status: JobStatus = JobStatus.CREATED
    result_kind: YouTubeResultKind = YouTubeResultKind.SUCCESS
    failure_kind: YouTubeFailureKind | None = None
    failed_stage: YouTubeFailedStage | None = None
    reason: str | None = None
    format: Literal["markdown", "json"] = "markdown"
    content: str = ""
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class YouTubeRunRead(StrictModel):
    run_id: str
    kind: YouTubeRunKind
    status: JobStatus = JobStatus.CREATED
    result_kind: YouTubeResultKind = YouTubeResultKind.SUCCESS
    failure_kind: YouTubeFailureKind | None = None
    failed_stage: YouTubeFailedStage | None = None
    reason: str | None = None
    subscription_id: str | None = None
    video_id: str | None = None
    summary: str | None = None
    duration_seconds: float | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class YouTubeCheckResultRead(StrictModel):
    run: YouTubeRunRead
    subscription: YouTubeSubscriptionRead
    discovered_count: int = 0
    discovered_video_ids: list[str] = Field(default_factory=list)
    new_video_ids: list[str] = Field(default_factory=list)


class YouTubeSubscriptionExportRead(StrictModel):
    version: Literal["youtube_subscriptions.v1"] = "youtube_subscriptions.v1"
    exported_at: datetime
    subscriptions: list[YouTubeSubscriptionImportItem] = Field(default_factory=list)


class YouTubeSubscriptionImportItemResultRead(StrictModel):
    source_url: str
    normalized_url: str | None = None
    action: Literal["created", "updated", "restored", "skipped", "failed"]
    subscription: YouTubeSubscriptionRead | None = None
    error_kind: YouTubeFailureKind | None = None
    reason: str | None = None


class YouTubeSubscriptionImportResultRead(StrictModel):
    imported_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    restored_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    items: list[YouTubeSubscriptionImportItemResultRead] = Field(default_factory=list)


class YouTubeQuestionAnswerRead(StrictModel):
    video_id: str
    question: str
    answer: str
    citations: list[str] = Field(default_factory=list)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerType(str, Enum):
    LINUX = "linux"
    MAC = "mac"
    WIN_YINGDAO = "win_yingdao"
    OPENCLAW = "openclaw"


class WorkerMode(str, Enum):
    ACTIVE = "active"
    STANDBY = "standby"
    DRAINING = "draining"
    OFFLINE = "offline"


class WorkerHealth(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"


class WorkerRegisterRequest(StrictModel):
    worker_id: str = Field(..., min_length=1)
    worker_type: WorkerType
    name: str | None = None
    host: str | None = None
    mode: WorkerMode = WorkerMode.ACTIVE
    role: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerHeartbeatRequest(StrictModel):
    health: WorkerHealth = WorkerHealth.OK
    load: float | None = Field(default=None, ge=0.0)
    queue_depth: int = Field(default=0, ge=0)
    disk_free_gb: float | None = Field(default=None, ge=0.0)
    accepting_work: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerRegistrationRead(StrictModel):
    worker_id: str
    worker_type: WorkerType
    name: str | None = None
    host: str | None = None
    mode: WorkerMode = WorkerMode.ACTIVE
    role: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    health: WorkerHealth = WorkerHealth.OK
    load: float | None = None
    queue_depth: int = 0
    disk_free_gb: float | None = None
    accepting_work: bool = True
    is_stale: bool = False
    registered_at: datetime
    last_heartbeat_at: datetime
    updated_at: datetime


class WorkerLatestTaskSummaryRead(StrictModel):
    run_id: str
    task_name: str
    task_type: WorkerTaskType | str
    status: JobStatus
    message: str | None = None
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerLocationRead(StrictModel):
    host: str | None = None
    runtime: str | None = None
    work_dir: str | None = None


class WorkerDispatchRulesRead(StrictModel):
    accepting_work: bool = True
    mode: WorkerMode = WorkerMode.ACTIVE
    queue_names: list[str] = Field(default_factory=list)
    task_types: list[str] = Field(default_factory=list)
    preferred_run_ids: list[str] = Field(default_factory=list)
    capability_tags: list[str] = Field(default_factory=list)


class WorkerInventoryRead(StrictModel):
    worker_id: str
    worker_type: WorkerType
    name: str | None = None
    host: str | None = None
    mode: WorkerMode = WorkerMode.ACTIVE
    role: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    health: WorkerHealth = WorkerHealth.OK
    load: float | None = None
    queue_depth: int = 0
    disk_free_gb: float | None = None
    accepting_work: bool = True
    is_stale: bool = False
    registered_at: datetime
    last_heartbeat_at: datetime
    updated_at: datetime
    active_tasks: int = 0
    latest_task_summary: WorkerLatestTaskSummaryRead | None = None
    location: WorkerLocationRead = Field(default_factory=WorkerLocationRead)
    dispatch_rules: WorkerDispatchRulesRead = Field(default_factory=WorkerDispatchRulesRead)
    display_status: str = "online"


class HermesInteractiveSessionRead(StrictModel):
    aas_session_id: str = Field(..., min_length=1)
    hermes_gateway_session_id: str = Field(..., min_length=1)
    run_id: str | None = None
    gateway_stream_cursor: str | None = None
    worker_id: str | None = None
    last_event: dict[str, Any] | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerInventorySummaryRead(StrictModel):
    total_workers: int = 0
    online_workers: int = 0
    busy_workers: int = 0
    degraded_workers: int = 0
    offline_workers: int = 0
    issued_at: datetime


class WorkerInventoryListRead(StrictModel):
    summary: WorkerInventorySummaryRead
    workers: list[WorkerInventoryRead] = Field(default_factory=list)


class WorkerQueueName(str, Enum):
    HOUSEKEEPING = "housekeeping"


class WorkerTaskType(str, Enum):
    NOOP = "noop"
    CLEANUP_APPLEDOUBLE = "cleanup_appledouble"
    CLEANUP_TMP = "cleanup_tmp"
    YOUTUBE_ACTION = "youtube_action"
    YOUTUBE_AUTOFLOW = "youtube_autoflow"
    CLAUDE_RUNTIME = "claude_runtime"
    EXCEL_AUDIT = "excel_audit"
    CONTENT_KB_CLASSIFY = "content_kb_classify"
    CONTENT_KB_INGEST = "content_kb_ingest"


class WorkerRunProgressRead(StrictModel):
    current: int = Field(default=0, ge=0)
    total: int | None = Field(default=None, ge=0)


class WorkerQueueItemCreateRequest(StrictModel):
    queue_name: WorkerQueueName = WorkerQueueName.HOUSEKEEPING
    task_name: str | None = None
    task_type: WorkerTaskType = WorkerTaskType.NOOP
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: str | None = None
    priority: int = Field(default=0, ge=0, le=100)
    max_retries: int = Field(default=2, ge=0, le=20)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _derive_task_name(self) -> WorkerQueueItemCreateRequest:
        if self.task_name is None or not self.task_name.strip():
            self.task_name = self.task_type.value
        else:
            self.task_name = self.task_name.strip()
        return self


class WorkerQueueItemRead(StrictModel):
    run_id: str
    queue_name: WorkerQueueName
    task_name: str
    task_type: WorkerTaskType = WorkerTaskType.NOOP
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: str | None = None
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 2
    next_attempt_at: datetime | None = None
    recovery_reason: str | None = None
    status: JobStatus = JobStatus.QUEUED
    assigned_worker_id: str | None = None
    message: str | None = None
    progress: WorkerRunProgressRead | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerLeaseRead(StrictModel):
    lease_id: str
    run_id: str
    worker_id: str
    queue_name: WorkerQueueName
    lease_expires_at: datetime
    active: bool = True
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkerClaimRequest(StrictModel):
    queue_name: WorkerQueueName = WorkerQueueName.HOUSEKEEPING


class WorkerClaimRead(StrictModel):
    claimed: bool = False
    queue_name: WorkerQueueName
    worker_id: str
    run: WorkerQueueItemRead | None = None
    lease: WorkerLeaseRead | None = None
    reason: str | None = None
    created_at: datetime


class WorkerRunReportRequest(StrictModel):
    status: JobStatus
    message: str | None = None
    progress: WorkerRunProgressRead | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip().lower() == "succeeded":
            return JobStatus.COMPLETED
        return value

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: JobStatus) -> JobStatus:
        if value not in {JobStatus.RUNNING, JobStatus.COMPLETED, JobStatus.FAILED}:
            raise ValueError("status must be running, completed, failed, or succeeded")
        return value


class WorkerScheduleMode(str, Enum):
    ONCE = "once"
    INTERVAL = "interval"


class WorkerRunScheduleCreateRequest(StrictModel):
    schedule_name: str | None = None
    queue_name: WorkerQueueName = WorkerQueueName.HOUSEKEEPING
    task_name: str | None = None
    task_type: WorkerTaskType = WorkerTaskType.NOOP
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: str | None = None
    priority: int = Field(default=0, ge=0, le=100)
    max_retries: int = Field(default=2, ge=0, le=20)
    metadata: dict[str, Any] = Field(default_factory=dict)
    schedule_mode: WorkerScheduleMode = WorkerScheduleMode.INTERVAL
    first_run_at: datetime | None = None
    interval_seconds: int | None = Field(default=None, ge=1)
    enabled: bool = True

    @model_validator(mode="after")
    def _normalize_schedule(self) -> WorkerRunScheduleCreateRequest:
        if self.task_name is None or not self.task_name.strip():
            self.task_name = self.task_type.value
        else:
            self.task_name = self.task_name.strip()

        if self.schedule_name is None or not self.schedule_name.strip():
            self.schedule_name = self.task_name
        else:
            self.schedule_name = self.schedule_name.strip()

        if self.schedule_mode == WorkerScheduleMode.ONCE:
            if self.first_run_at is None:
                raise ValueError("first_run_at is required for once schedules")
            self.interval_seconds = None
        elif self.interval_seconds is None:
            raise ValueError("interval_seconds is required for interval schedules")
        return self


class WorkerRunScheduleRead(StrictModel):
    schedule_id: str
    schedule_name: str
    queue_name: WorkerQueueName = WorkerQueueName.HOUSEKEEPING
    task_name: str
    task_type: WorkerTaskType = WorkerTaskType.NOOP
    payload: dict[str, Any] = Field(default_factory=dict)
    requested_by: str | None = None
    priority: int = 0
    max_retries: int = 2
    metadata: dict[str, Any] = Field(default_factory=dict)
    schedule_mode: WorkerScheduleMode = WorkerScheduleMode.INTERVAL
    interval_seconds: int | None = None
    enabled: bool = True
    next_run_at: datetime | None = None
    last_triggered_at: datetime | None = None
    last_enqueued_run_id: str | None = None
    run_count: int = 0
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class WorkerRunScheduleResumeRequest(StrictModel):
    next_run_at: datetime | None = None


class WorkerScheduleDispatchRead(StrictModel):
    schedule_id: str
    run_id: str
    task_type: WorkerTaskType
    queued_at: datetime


class WorkerScheduleTickRead(StrictModel):
    scanned: int = 0
    dispatches: list[WorkerScheduleDispatchRead] = Field(default_factory=list)
    failures: dict[str, str] = Field(default_factory=dict)
    created_at: datetime


class StandbyYouTubeAction(str, Enum):
    SUBSCRIBE = "subscribe"
    CHECK = "check"
    FETCH_TRANSCRIPT = "fetch_transcript"
    BUILD_DIGEST = "build_digest"
    ASK = "ask"


class StandbyYouTubeActionRequest(StrictModel):
    action: StandbyYouTubeAction
    target_url: str | None = None
    subscription_id: str | None = None
    video_id: str | None = None
    question: str | None = None
    preferred_languages: list[str] = Field(default_factory=lambda: ["zh-Hans", "zh-CN", "en"])
    include_auto_generated: bool = True
    overwrite_existing: bool = False
    check_limit: int = Field(default=5, ge=1, le=50)
    digest_format: Literal["markdown", "json"] = "markdown"
    requested_by: str | None = None
    source: str = "standby_housekeeper"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_action_fields(self) -> StandbyYouTubeActionRequest:
        if self.action == StandbyYouTubeAction.SUBSCRIBE and not self.target_url:
            raise ValueError("target_url is required for subscribe")
        if self.action == StandbyYouTubeAction.CHECK and not self.subscription_id:
            raise ValueError("subscription_id is required for check")
        if self.action in {
            StandbyYouTubeAction.FETCH_TRANSCRIPT,
            StandbyYouTubeAction.BUILD_DIGEST,
            StandbyYouTubeAction.ASK,
        } and not self.video_id:
            raise ValueError("video_id is required for this action")
        if self.action == StandbyYouTubeAction.ASK and not (self.question and self.question.strip()):
            raise ValueError("question is required for ask")
        return self


class StandbyYouTubeActionResult(StrictModel):
    success: bool
    action: str
    status: JobStatus
    result_kind: YouTubeResultKind | None = None
    error_kind: str | None = None
    failed_stage: str | None = None
    reason: str | None = None
    subscription_id: str | None = None
    video_id: str | None = None
    transcript_id: str | None = None
    digest_id: str | None = None
    run_id: str | None = None
    answer: str | None = None
    citations: list[str] = Field(default_factory=list)
    discovered_video_ids: list[str] = Field(default_factory=list)
    new_video_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StandbyYouTubeAutoflowRequest(StrictModel):
    source_url: str | None = None
    input_text: str | None = None
    repo_hint: str | None = None
    preferred_languages: list[str] = Field(default_factory=lambda: ["zh-Hans", "zh-CN", "en"])
    include_auto_generated: bool = True
    overwrite_existing: bool = False
    requested_by: str | None = None
    source: str = "standby_housekeeper"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_source_fields(self) -> StandbyYouTubeAutoflowRequest:
        has_source_url = bool(self.source_url and self.source_url.strip())
        has_input_text = bool(self.input_text and self.input_text.strip())
        if not has_source_url and not has_input_text:
            raise ValueError("source_url or input_text is required")
        return self


class StandbyYouTubeAutoflowResult(StrictModel):
    success: bool
    status: JobStatus
    source_url: str | None = None
    normalized_url: str | None = None
    subscription_id: str | None = None
    video_id: str | None = None
    transcript_id: str | None = None
    digest_id: str | None = None
    repo: str | None = None
    output_path: str | None = None
    route_reason: str | None = None
    github_run_dir: str | None = None
    github_run_status: str | None = None
    pr_url: str | None = None
    error_kind: str | None = None
    failed_stage: str | None = None
    reason: str | None = None
    artifacts: list[str] = Field(default_factory=list)
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


# ---------------------------------------------------------------------------
# Claude Runtime Session Stickiness
# ---------------------------------------------------------------------------


class ClaudeRuntimeSessionRecordRead(StrictModel):
    session_key: str
    worker_id: str | None = None
    project_dir: str | None = None
    claude_home: str | None = None
    latest_session_ref: str | None = None
    last_summary: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
