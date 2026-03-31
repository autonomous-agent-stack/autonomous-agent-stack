from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.agent_protocol.models import JobSpec, RunSummary
from autoresearch.shared.models import JobStatus, StrictModel
from autoresearch.shared.openhands_controlled_contract import ControlledExecutionRequest
from autoresearch.shared.openhands_worker_contract import OpenHandsWorkerJobSpec
from autoresearch.shared.remote_run_contract import RemoteRunRecord


class AutoResearchPlannerRequest(StrictModel):
    goal: str = Field(
        default="Scan the repo for the next safe patch-only improvement.",
        min_length=1,
    )
    max_candidates: int = Field(default=5, ge=1, le=20)
    pipeline_target: Literal["patch", "draft_pr"] = "draft_pr"
    target_base_branch: str = Field(default="main", min_length=1)
    max_iterations: int = Field(default=2, ge=1, le=5)
    approval_granted: bool = False
    include_upstream_watch: bool = False
    telegram_uid: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("goal", "target_base_branch")
    @classmethod
    def _normalize_non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("pipeline_target")
    @classmethod
    def _normalize_pipeline_target(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"patch", "draft_pr"}:
            raise ValueError("pipeline_target must be patch or draft_pr")
        return normalized

    @field_validator("telegram_uid")
    @classmethod
    def _normalize_telegram_uid(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class AutoResearchPlanDispatchStatus(str, Enum):
    PENDING = "pending"
    DISPATCHING = "dispatching"
    DISPATCHED = "dispatched"
    FAILED = "failed"


class UpstreamWatchDecision(str, Enum):
    SKIP = "skip"
    REVIEW = "review"
    FAILED = "failed"


class UpstreamWatchCommitRead(StrictModel):
    sha: str
    title: str
    committed_at: datetime | None = None
    touched_paths: list[str] = Field(default_factory=list)


class UpstreamWatchRead(StrictModel):
    upstream_url: str
    default_branch: str = "main"
    latest_commit_sha: str | None = None
    latest_commit_title: str | None = None
    latest_commit_at: datetime | None = None
    recent_commits: list[UpstreamWatchCommitRead] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    relevant_paths: list[str] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list)
    decision: UpstreamWatchDecision = UpstreamWatchDecision.SKIP
    summary: str = ""
    cleaned_up: bool = False
    cleanup_paths: list[str] = Field(default_factory=list)
    error: str | None = None


class AutoResearchPlannerEvidenceRead(StrictModel):
    kind: Literal["marker", "test_gap", "hotspot"]
    path: str = Field(..., min_length=1)
    line: int | None = None
    detail: str = ""
    weight: float = 0.0


class AutoResearchPlannerCandidateRead(StrictModel):
    candidate_id: str
    title: str
    summary: str
    category: Literal["marker_backlog", "test_gap"]
    priority_score: float = 0.0
    source_path: str
    allowed_paths: list[str] = Field(default_factory=list)
    suggested_test_paths: list[str] = Field(default_factory=list)
    test_command: str
    evidence: list[AutoResearchPlannerEvidenceRead] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AutoResearchPlanRead(StrictModel):
    plan_id: str
    goal: str
    status: JobStatus
    summary: str = ""
    created_at: datetime
    updated_at: datetime
    selected_candidate: AutoResearchPlannerCandidateRead | None = None
    candidates: list[AutoResearchPlannerCandidateRead] = Field(default_factory=list)
    worker_spec: OpenHandsWorkerJobSpec | None = None
    controlled_request: ControlledExecutionRequest | None = None
    agent_job: JobSpec | None = None
    upstream_watch: UpstreamWatchRead | None = None
    telegram_uid: str | None = None
    panel_action_url: str | None = None
    notification_sent: bool = False
    dispatch_status: AutoResearchPlanDispatchStatus = AutoResearchPlanDispatchStatus.PENDING
    dispatch_requested_at: datetime | None = None
    dispatch_completed_at: datetime | None = None
    dispatch_requested_by: str | None = None
    dispatch_run: RemoteRunRecord | None = None
    run_summary: RunSummary | None = None
    dispatch_error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
