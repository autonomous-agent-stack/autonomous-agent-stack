from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field, field_validator, model_validator

from autoresearch.shared.models import JobStatus, StrictModel


class GitHubAdminVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    ALL = "all"


class GitHubAdminRunType(str, Enum):
    INVENTORY = "inventory"
    TRANSFER_PLAN = "transfer_plan"


class GitHubAdminReadiness(str, Enum):
    READY = "ready"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class GitHubAdminPostActions(StrictModel):
    add_cross_collaborators: bool = True
    request_invitation_acceptance: bool = True


class GitHubAdminInventoryRequest(StrictModel):
    owners: list[str] = Field(..., min_length=1)
    visibility: GitHubAdminVisibility = GitHubAdminVisibility.PUBLIC
    target_owner: str | None = None
    include_archived: bool = False

    @field_validator("owners", mode="before")
    @classmethod
    def _normalize_owners(cls, value: object) -> list[str]:
        if not isinstance(value, list):
            raise ValueError("owners must be a list of strings")
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("owners must be a list of strings")
            candidate = item.strip()
            if not candidate:
                continue
            lowered = candidate.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(candidate)
        if not normalized:
            raise ValueError("owners must include at least one owner")
        return normalized

    @field_validator("target_owner")
    @classmethod
    def _normalize_target_owner(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class GitHubAdminTransferPlanRequest(StrictModel):
    source_owners: list[str] = Field(..., min_length=1)
    target_owner: str = Field(..., min_length=1)
    visibility: GitHubAdminVisibility = GitHubAdminVisibility.PUBLIC
    include_archived: bool = False
    post_actions: GitHubAdminPostActions = Field(default_factory=GitHubAdminPostActions)
    dry_run: bool = True

    @field_validator("source_owners", mode="before")
    @classmethod
    def _normalize_source_owners(cls, value: object) -> list[str]:
        return GitHubAdminInventoryRequest._normalize_owners(value)

    @field_validator("target_owner")
    @classmethod
    def _normalize_target_owner(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("target_owner is required")
        return normalized

    @model_validator(mode="after")
    def _enforce_dry_run(self) -> "GitHubAdminTransferPlanRequest":
        if not self.dry_run:
            raise ValueError("execute-transfer is not implemented in this slice; transfer-plan must stay dry_run=true")
        return self


class GitHubAdminFailureRead(StrictModel):
    scope: str
    owner: str | None = None
    repo: str | None = None
    action: str
    detail: str


class GitHubAdminProfileRead(StrictModel):
    profile_id: str
    owner: str
    github_host: str = "github.com"
    can_transfer: bool = False
    has_token: bool = False
    source_path: str
    is_example: bool = False
    token: str | None = Field(default=None, exclude=True, repr=False)


class GitHubAdminRepositoryRead(StrictModel):
    source_owner: str
    name: str
    full_name: str
    visibility: str = "public"
    archived: bool = False
    fork: bool = False
    description: str | None = None
    html_url: str | None = None
    default_branch: str | None = None
    language: str | None = None
    stargazers_count: int = 0
    forks_count: int = 0
    pushed_at: str | None = None
    other_collaborators: list[str] = Field(default_factory=list)
    collaborator_check: str = "not_checked"
    suggested_exclude: bool = False
    suggested_exclude_reasons: list[str] = Field(default_factory=list)
    source_profile_id: str | None = None


class GitHubAdminPreflightCheckRead(StrictModel):
    status: GitHubAdminReadiness = GitHubAdminReadiness.UNKNOWN
    reason: str = ""


class GitHubAdminProfileIsolationRead(StrictModel):
    owner: str
    role: str
    profile_id: str | None = None
    readiness: GitHubAdminReadiness = GitHubAdminReadiness.UNKNOWN
    reason: str = ""
    github_host: str | None = None
    has_token: bool = False
    can_transfer: bool = False


class GitHubAdminTargetOwnerProbeRead(StrictModel):
    target_owner: str
    confirmation_profile_id: str | None = None
    readiness: GitHubAdminReadiness = GitHubAdminReadiness.UNKNOWN
    reason: str = ""
    probe_method: str = "repository_listing"


class GitHubAdminRepoPreflightRead(StrictModel):
    full_name: str
    readiness: GitHubAdminReadiness = GitHubAdminReadiness.UNKNOWN
    reason: str = ""
    source_profile_id: str | None = None
    confirmation_profile_id: str | None = None
    profile_isolation: GitHubAdminPreflightCheckRead = Field(default_factory=GitHubAdminPreflightCheckRead)
    target_owner_probe: GitHubAdminPreflightCheckRead = Field(default_factory=GitHubAdminPreflightCheckRead)
    collaborator_sync: GitHubAdminPreflightCheckRead = Field(default_factory=GitHubAdminPreflightCheckRead)
    invitation_acceptance: GitHubAdminPreflightCheckRead = Field(default_factory=GitHubAdminPreflightCheckRead)
    reasons: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GitHubAdminPreflightRead(StrictModel):
    profile_isolation: list[GitHubAdminProfileIsolationRead] = Field(default_factory=list)
    target_owner_probe: GitHubAdminTargetOwnerProbeRead | None = None
    repositories: list[GitHubAdminRepoPreflightRead] = Field(default_factory=list)


class GitHubAdminPlanDecisionRead(StrictModel):
    full_name: str
    action: str
    reason: str
    readiness: GitHubAdminReadiness = GitHubAdminReadiness.UNKNOWN
    source_profile_id: str | None = None
    confirmation_profile_id: str | None = None
    planned_collaborators: list[str] = Field(default_factory=list)
    invitation_acceptance_profiles: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GitHubAdminRunSummary(StrictModel):
    owners_requested: list[str] = Field(default_factory=list)
    owners_scanned: list[str] = Field(default_factory=list)
    repo_count: int = 0
    candidate_repo_count: int = 0
    excluded_repo_count: int = 0
    planned_transfer_count: int = 0
    manual_review_count: int = 0
    ready_to_execute_count: int = 0
    blocked_count: int = 0
    unknown_count: int = 0
    failure_count: int = 0


class GitHubAdminRunRead(StrictModel):
    run_id: str
    run_type: GitHubAdminRunType
    status: JobStatus = JobStatus.CREATED
    dry_run: bool = True
    source_owners: list[str] = Field(default_factory=list)
    target_owner: str | None = None
    visibility: GitHubAdminVisibility = GitHubAdminVisibility.PUBLIC
    include_archived: bool = False
    profiles: list[GitHubAdminProfileRead] = Field(default_factory=list)
    repositories: list[GitHubAdminRepositoryRead] = Field(default_factory=list)
    preflight: GitHubAdminPreflightRead = Field(default_factory=GitHubAdminPreflightRead)
    decisions: list[GitHubAdminPlanDecisionRead] = Field(default_factory=list)
    failures: list[GitHubAdminFailureRead] = Field(default_factory=list)
    summary: GitHubAdminRunSummary = Field(default_factory=GitHubAdminRunSummary)
    run_dir: str = ""
    artifacts: list[str] = Field(default_factory=list)
    plan_markdown: str | None = None
    created_at: datetime
    updated_at: datetime
    error: str | None = None

