"""Foundation contracts for unified task orchestration.

This module defines the core contracts (JobSpec, DriverResult, RunDecision, RunState)
that unify excel_audit, github_admin, and content_kb under a common execution framework.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    """Base model that forbids extra fields."""
    model_config = ConfigDict(extra="forbid")


def utc_now() -> datetime:
    """Return current UTC timestamp."""
    return datetime.now(datetime.timezone.utc)


# ============================================================================
# RunState - Task execution state
# ============================================================================


class RunState(str, Enum):
    """Unified task execution state.

    State transitions:
    - queued -> running
    - running -> succeeded | failed | needs_review | timed_out | cancelled
    - needs_review -> succeeded | failed | cancelled (after human decision)
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


# Valid state transitions
_VALID_TRANSITIONS: dict[RunState, set[RunState]] = {
    RunState.QUEUED: {RunState.RUNNING, RunState.CANCELLED},
    RunState.RUNNING: {
        RunState.SUCCEEDED,
        RunState.FAILED,
        RunState.NEEDS_REVIEW,
        RunState.TIMED_OUT,
        RunState.CANCELLED,
    },
    RunState.NEEDS_REVIEW: {RunState.SUCCEEDED, RunState.FAILED, RunState.CANCELLED},
    RunState.SUCCEEDED: set(),  # Terminal
    RunState.FAILED: set(),  # Terminal
    RunState.TIMED_OUT: set(),  # Terminal
    RunState.CANCELLED: set(),  # Terminal
}


def is_valid_transition(from_state: RunState, to_state: RunState) -> bool:
    """Check if a state transition is valid."""
    return to_state in _VALID_TRANSITIONS.get(from_state, set())


# ============================================================================
# RunDecision - Gate decision after task execution
# ============================================================================


class RunDecision(str, Enum):
    """Gate decision for a completed task.

    - ACCEPT: Task succeeded, accept the result
    - RETRY: Transient failure, retry the task
    - FALLBACK: Use fallback agent or strategy
    - NEEDS_REVIEW: Requires human review before accepting
    """

    ACCEPT = "accept"
    RETRY = "retry"
    FALLBACK = "fallback"
    NEEDS_REVIEW = "needs_review"


# ============================================================================
# ArtifactRef - Reference to task artifacts
# ============================================================================


class ArtifactRef(StrictModel):
    """Reference to an input or output artifact."""

    name: str = Field(..., min_length=1)
    kind: Literal["log", "report", "plan", "patch", "compliance", "custom"] = "custom"
    uri: str = Field(..., min_length=1)
    sha256: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None


# ============================================================================
# ApprovalRequirement - Human approval requirement
# ============================================================================


class ApprovalRequirement(StrictModel):
    """Approval requirement for a task."""

    required: bool = False
    scope: str = "default"  # e.g., "writeback_to_source_excel", "merge_to_main"
    reason: str = ""
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    approver_roles: list[str] = Field(default_factory=lambda: ["owner", "admin"])
    expires_in_seconds: int = Field(default=3600, ge=60, le=604800)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# JobContext - Execution context for a task
# ============================================================================


class JobContext(StrictModel):
    """Execution context for a task run."""

    dry_run: bool = True
    requires_approval: bool = False
    approval_requirement: ApprovalRequirement | None = None
    timeout_seconds: int = Field(default=900, ge=1, le=7200)
    max_retries: int = Field(default=0, ge=0, le=10)
    workspace_mode: Literal["isolated", "shared", "in_place"] = "isolated"
    allow_code_change: bool = False
    allow_network: bool = False
    allowed_paths: list[str] = Field(default_factory=list)
    forbidden_paths: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# JobSpec - Unified task specification
# ============================================================================


class JobSpec(StrictModel):
    """Unified task specification for all agents.

    This contract can express tasks for:
    - excel_audit: Commission check, reconciliation, report generation
    - github_admin: Repository inventory, transfer planning (dry-run only)
    - content_kb: Topic classification, repo selection, index building
    """

    protocol_version: Literal["foundation/v1"] = "foundation/v1"

    # Identity
    run_id: str = Field(..., min_length=1)
    parent_run_id: str | None = None

    # Agent selection
    agent_id: str = Field(..., min_length=1)
    task_type: str = Field(..., min_length=1)  # e.g., "excel_audit", "github_admin.transfer_plan"
    role: Literal["planner", "executor", "reviewer", "analyst", "specialist", "orchestrator"] = "executor"

    # Task definition
    task: str = Field(..., min_length=1)
    task_brief: str | None = None  # Extended task description

    # Input/output
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)
    attachments: list[str] = Field(default_factory=list)  # File paths or URLs

    # Execution context
    context: JobContext = Field(default_factory=JobContext)

    # Metadata
    requested_by: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# DriverRequest - Request to execute a task
# ============================================================================


class DriverRequest(StrictModel):
    """Request to execute a task via a driver."""

    run_id: str = Field(..., min_length=1)
    job_spec: JobSpec
    attempt: int = Field(default=1, ge=1, le=100)
    driver_id: str = "default"
    driver_config: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# DriverMetrics - Execution metrics
# ============================================================================


class DriverMetrics(StrictModel):
    """Metrics from driver execution."""

    duration_ms: int = 0
    steps: int = 0
    commands: int = 0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    first_progress_ms: int | None = None
    first_scoped_write_ms: int | None = None


# ============================================================================
# DriverResult - Result from driver execution
# ============================================================================


class DriverResult(StrictModel):
    """Result from driver execution.

    This captures both success and failure states with enough detail
    for the task gate to make a decision.
    """

    protocol_version: Literal["foundation/v1"] = "foundation/v1"

    # Identity
    run_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    attempt: int = Field(default=1, ge=1)

    # Status
    status: Literal[
        "succeeded",
        "partial",
        "failed",
        "timed_out",
        "stalled_no_progress",
        "policy_blocked",
        "contract_error",
    ] = "failed"

    # Result
    summary: str = ""
    changed_paths: list[str] = Field(default_factory=list)
    output_artifacts: list[ArtifactRef] = Field(default_factory=list)

    # Metrics
    metrics: DriverMetrics = Field(default_factory=DriverMetrics)

    # Decision hint
    recommended_action: Literal[
        "promote",
        "retry",
        "fallback",
        "human_review",
        "reject",
    ] = "human_review"

    # Error info
    error: str | None = None
    error_code: str | None = None
    traceback: str | None = None

    # Dry-run marker
    dry_run_executed: bool = False  # True if this was a dry-run, not real execution


# ============================================================================
# TaskGateCheck - Individual gate check
# ============================================================================


class TaskGateCheck(StrictModel):
    """Individual gate check result."""

    id: str = Field(..., min_length=1)
    passed: bool = False
    detail: str = ""
    severity: Literal["critical", "high", "medium", "low"] = "high"
    artifact: ArtifactRef | None = None


# ============================================================================
# TaskGateResult - Result from task gate evaluation
# ============================================================================


class TaskGateResult(StrictModel):
    """Result from task gate evaluation.

    The task gate evaluates a DriverResult and produces a TaskGateResult
    with the final decision and supporting checks.
    """

    run_id: str = Field(..., min_length=1)

    # Decision
    decision: RunDecision = RunDecision.NEEDS_REVIEW
    reasons: list[str] = Field(default_factory=list)

    # Checks
    checks: list[TaskGateCheck] = Field(default_factory=list)
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)

    # Flags
    requires_human_review: bool = True
    retryable: bool = False
    fallback_recommended: bool = False
    dry_run_complete: bool = False  # True if this was a dry-run that completed

    # Timing
    evaluated_at: datetime = Field(default_factory=utc_now)

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# RunRecord - Complete record of a task run
# ============================================================================


class RunRecord(StrictModel):
    """Complete record of a task run."""

    run_id: str = Field(..., min_length=1)
    job_spec: JobSpec
    state: RunState = RunState.QUEUED
    driver_result: DriverResult | None = None
    gate_result: TaskGateResult | None = None

    # Timing
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    finished_at: datetime | None = None

    # State transitions
    state_history: list[dict[str, Any]] = Field(default_factory=list)

    # Error
    error: str | None = None

    def record_transition(self, from_state: RunState, to_state: RunState, reason: str = "") -> None:
        """Record a state transition."""
        self.state_history.append(
            {
                "from": from_state.value,
                "to": to_state.value,
                "reason": reason,
                "timestamp": utc_now().isoformat(),
            }
        )
