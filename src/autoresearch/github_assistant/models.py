from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.shared.models import StrictModel


class AssistantExecutorConfig(StrictModel):
    adapter: Literal["shell", "codex", "openhands", "custom"] = "codex"
    binary: str | None = "codex"
    command: list[str] = Field(default_factory=list)
    timeout_seconds: int = Field(default=1800, ge=1, le=7200)
    env: dict[str, str] = Field(default_factory=dict)


class AssistantScheduleConfig(StrictModel):
    issue_label: str = "assistant:auto"
    max_issues_per_repo: int = Field(default=5, ge=1, le=100)


class AssistantConfig(StrictModel):
    bot_account: str = Field(..., min_length=1)
    branch_prefix: str = Field(default="assistant/issue")
    draft_pr_only: bool = True
    manual_trigger_enabled: bool = True
    scheduled_trigger_enabled: bool = False
    issue_autoclose: bool = False
    max_changed_files: int = Field(default=10, ge=1, le=500)
    max_patch_lines: int = Field(default=400, ge=1, le=10000)
    runs_dir: str = "runs"
    workspace_root: str = "/tmp/github-assistant"
    prompts_dir: str = "prompts"
    policy_path: str = "policies/default-policy.yaml"
    executor: AssistantExecutorConfig = Field(default_factory=AssistantExecutorConfig)
    schedule: AssistantScheduleConfig = Field(default_factory=AssistantScheduleConfig)


class ManagedRepoConfig(StrictModel):
    repo: str = Field(..., min_length=3)
    default_branch: str = Field(default="main", min_length=1)
    language: str = Field(default="python", min_length=1)
    workspace_mode: Literal["temp"] = "temp"
    allowed_paths: list[str] = Field(default_factory=list)
    test_command: str = ""
    lint_command: str = ""
    reviewers: list[str] = Field(default_factory=list)
    labels_map: dict[str, list[str]] = Field(default_factory=dict)

    @field_validator("allowed_paths", "reviewers", mode="before")
    @classmethod
    def _normalize_string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        return [str(item).strip() for item in value if str(item).strip()]

    @field_validator("labels_map", mode="before")
    @classmethod
    def _normalize_labels_map(cls, value: Any) -> dict[str, list[str]]:
        if not isinstance(value, dict):
            return {}
        normalized: dict[str, list[str]] = {}
        for key, raw_items in value.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            if isinstance(raw_items, str):
                items = [raw_items.strip()] if raw_items.strip() else []
            else:
                items = [str(item).strip() for item in raw_items if str(item).strip()]
            normalized[key_text] = items
        return normalized


class RepoCatalog(StrictModel):
    repos: list[ManagedRepoConfig] = Field(default_factory=list)


class AssistantPolicy(StrictModel):
    forbidden_paths: list[str] = Field(default_factory=list)
    allow_comment: bool = True
    allow_label: bool = True
    allow_assign: bool = True
    allow_branch: bool = True
    allow_commit: bool = True
    allow_push: bool = True
    allow_draft_pr: bool = True
    allow_autoclose: bool = False

    @field_validator("forbidden_paths", mode="before")
    @classmethod
    def _normalize_forbidden_paths(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
        return [str(item).strip() for item in value if str(item).strip()]


class GitHubIssueComment(StrictModel):
    author: str
    body: str
    created_at: str | None = None


class GitHubIssue(StrictModel):
    repo: str
    number: int
    title: str
    body: str
    url: str
    state: str
    author: str
    labels: list[str] = Field(default_factory=list)
    assignees: list[str] = Field(default_factory=list)
    comments: list[GitHubIssueComment] = Field(default_factory=list)


class GitHubPullRequestFile(StrictModel):
    path: str
    additions: int = 0
    deletions: int = 0


class GitHubPullRequest(StrictModel):
    repo: str
    number: int
    title: str
    body: str
    url: str
    state: str
    author: str
    base_ref: str
    head_ref: str
    labels: list[str] = Field(default_factory=list)
    files: list[GitHubPullRequestFile] = Field(default_factory=list)


class GitHubMergedPullRequest(StrictModel):
    repo: str
    number: int
    title: str
    url: str
    author: str
    merged_at: str | None = None
    labels: list[str] = Field(default_factory=list)


class TriageIssueType(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    DUPLICATE = "duplicate"
    QUESTION = "question"
    TASK = "task"


class TriagePriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TriageResult(StrictModel):
    repo: str
    issue_number: int
    issue_url: str
    issue_type: TriageIssueType
    priority: TriagePriority
    summary: str
    suggested_labels: list[str] = Field(default_factory=list)
    suggested_assignees: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    auto_executable: bool = False
    reasons: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    validator_commands: list[str] = Field(default_factory=list)


class ExecutionPlan(StrictModel):
    repo: str
    issue_number: int
    issue_url: str
    branch_name: str
    commit_message: str
    pr_title: str
    pr_body: str
    validator_commands: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    max_changed_files: int
    max_patch_lines: int


class PullRequestReviewResult(StrictModel):
    repo: str
    pr_number: int
    pr_url: str
    summary: str
    risk_level: Literal["low", "medium", "high"]
    suggested_checks: list[str] = Field(default_factory=list)
    blocked_files: list[str] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)


class ReleasePlanResult(StrictModel):
    repo: str
    target_version: str | None = None
    summary: str
    merged_prs: list[GitHubMergedPullRequest] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class DoctorStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class DoctorCheck(StrictModel):
    name: str
    status: DoctorStatus
    detail: str
    hint: str | None = None


class RunSummary(StrictModel):
    run_id: str
    repo: str
    issue_number: int | None = None
    issue_url: str | None = None
    status: str
    started_at: datetime
    updated_at: datetime
    triage: dict[str, Any] | None = None
    plan: dict[str, Any] | None = None
    changed_files: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    pr_url: str | None = None
    comment_results: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PreparedWorkspace(StrictModel):
    source_repo_dir: Path
    execution_workspace_dir: Path


class ScheduleSummary(StrictModel):
    scheduled_trigger_enabled: bool
    issue_label: str
    repos_scanned: int = 0
    issues_selected: int = 0
    triage_runs: list[str] = Field(default_factory=list)


class GitHubAssistantDoctorRead(StrictModel):
    ok: bool
    expected_bot_account: str | None = None
    active_login: str | None = None
    checks: list[DoctorCheck] = Field(default_factory=list)


class GitHubAssistantHealthRead(StrictModel):
    status: Literal["ok", "degraded"] = "ok"
    doctor_ok: bool
    gh_auth_ok: bool
    expected_bot_account: str | None = None
    active_login: str | None = None
    checks: list[DoctorCheck] = Field(default_factory=list)


class GitHubAssistantIssueRequest(StrictModel):
    repo: str = Field(..., min_length=3)
    issue_number: int = Field(..., ge=1)


class GitHubAssistantPullRequestRequest(StrictModel):
    repo: str = Field(..., min_length=3)
    pr_number: int = Field(..., ge=1)


class GitHubAssistantReleasePlanRequest(StrictModel):
    repo: str = Field(..., min_length=3)
    version: str | None = None
    limit: int = Field(default=10, ge=1, le=100)


class GitHubAssistantRunRead(StrictModel):
    run_dir: str
    artifacts: list[str] = Field(default_factory=list)
    summary: RunSummary


class GitHubAssistantTriageRunRead(GitHubAssistantRunRead):
    triage: TriageResult


class GitHubAssistantExecutionRunRead(StrictModel):
    run_dir: str
    artifacts: list[str] = Field(default_factory=list)
    summary: RunSummary


class GitHubAssistantPullRequestReviewRunRead(StrictModel):
    run_dir: str
    artifacts: list[str] = Field(default_factory=list)
    summary: RunSummary
    review: PullRequestReviewResult


class GitHubAssistantReleasePlanRunRead(StrictModel):
    run_dir: str
    artifacts: list[str] = Field(default_factory=list)
    summary: RunSummary
    release_plan: ReleasePlanResult
