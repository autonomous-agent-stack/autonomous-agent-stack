from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field

from autoresearch.shared.models import StrictModel


class HousekeeperMode(str, Enum):
    DAY_SAFE = "day_safe"
    NIGHT_READONLY_EXPLORE = "night_readonly_explore"
    NIGHT_EXPLORE = "night_explore"


class HousekeeperChangeReason(str, Enum):
    SCHEDULE = "schedule"
    MANUAL_PANEL = "manual_panel"
    MANUAL_API = "manual_api"
    CIRCUIT_BREAKER = "circuit_breaker"
    RECOVERED_FROM_CIRCUIT_BREAKER = "recovered_from_circuit_breaker"


class CircuitBreakerStatus(str, Enum):
    CLOSED = "closed"
    OPEN = "open"


class AdmissionRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DeferredReason(str, Enum):
    DEFERRED_TO_NIGHT = "deferred_to_night"
    APPROVAL_REQUIRED = "approval_required"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    BUDGET_EXHAUSTED = "budget_exhausted"
    DEDUP_BLOCKED = "dedup_blocked"


class ExplorationBlockerReason(str, Enum):
    ENV_MISSING = "env_missing"
    PERMISSION_DENIED = "permission_denied"
    EMPTY_SCOPE = "empty_scope"
    STALLED_NO_PROGRESS = "stalled_no_progress"
    VALIDATION_FAILED = "validation_failed"
    APPROVAL_PENDING = "approval_pending"
    DIRTY_REPO = "dirty_repo"
    BUDGET_EXHAUSTED = "budget_exhausted"
    UNKNOWN = "unknown"


class CircuitBreakerStateRead(StrictModel):
    status: CircuitBreakerStatus = CircuitBreakerStatus.CLOSED
    triggered_at: datetime | None = None
    reason: str | None = None
    consecutive_failures: int = 0
    recent_failure_rate: float = 0.0
    acknowledged_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionProfileRead(StrictModel):
    profile_name: HousekeeperMode
    pipeline_target: Literal["patch", "draft_pr"]
    max_iterations: int = Field(default=1, ge=1, le=5)
    auto_dispatch_allowed: bool = False
    parallelism: int = Field(default=1, ge=1, le=32)
    allow_draft_pr: bool = False
    allow_repo_write: bool = True
    allow_network: bool = False
    allow_long_task_minutes: int = Field(default=15, ge=1, le=1440)


class TaskAdmissionAssessmentRead(StrictModel):
    plan_shape: Literal["single_task", "task_dag", "planner_candidate", "media_job", "unknown"] = "unknown"
    estimated_runtime_minutes: int = Field(default=15, ge=0, le=1440)
    requires_repo_write: bool = True
    requires_network: bool = False
    fanout_count: int = Field(default=1, ge=0, le=100)
    risk_level: AdmissionRiskLevel = AdmissionRiskLevel.MEDIUM


class HousekeeperStateRead(StrictModel):
    state_id: str = "housekeeper"
    scheduled_mode: HousekeeperMode = HousekeeperMode.DAY_SAFE
    manual_override_mode: HousekeeperMode | None = None
    effective_mode: HousekeeperMode = HousekeeperMode.DAY_SAFE
    effective_until: datetime | None = None
    reason: HousekeeperChangeReason = HousekeeperChangeReason.SCHEDULE
    changed_by: str = "system"
    last_changed_at: datetime
    circuit_breaker_state: CircuitBreakerStateRead = Field(default_factory=CircuitBreakerStateRead)
    last_summary_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HousekeeperModeUpdateRequest(StrictModel):
    action: Literal["set_manual_override", "clear_manual_override", "ack_circuit_breaker", "apply_schedule"]
    target_mode: HousekeeperMode | None = None
    changed_by: str = Field(..., min_length=1)
    reason: HousekeeperChangeReason
    effective_until: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NightBudgetStateRead(StrictModel):
    budget_id: str = "night_budget"
    window_start: datetime
    window_end: datetime
    dispatches_used: int = 0
    draft_prs_used: int = 0
    worker_minutes_used: int = 0
    max_dispatches_per_night: int = 4
    max_draft_pr_per_night: int = 2
    max_worker_minutes_per_night: int = 180
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class HousekeeperTickRead(StrictModel):
    executed: bool = False
    skipped_reason: str | None = None
    target_kind: Literal["manager_dispatch", "planner_dispatch", "none"] = "none"
    target_id: str | None = None
    blocker_reason: ExplorationBlockerReason | None = None
    summary: str = ""
    state: HousekeeperStateRead
    budget: NightBudgetStateRead | None = None


class HousekeeperMorningSummaryRead(StrictModel):
    sent: bool = False
    summary_text: str
    completed_items: list[str] = Field(default_factory=list)
    blocked_items: list[str] = Field(default_factory=list)
    decision_items: list[str] = Field(default_factory=list)
    queue_items: list[str] = Field(default_factory=list)
    state: HousekeeperStateRead


class ExplorationDedupKeyRead(StrictModel):
    repo_id: str
    target_scope_hash: str
    intent_id: str
    normalized_goal_hash: str


class ExplorationRecordRead(StrictModel):
    record_id: str
    dedup_key: ExplorationDedupKeyRead
    target_kind: Literal["manager_dispatch", "planner_dispatch", "media_job"]
    target_id: str
    blocker_reason: ExplorationBlockerReason | None = None
    final_status: str | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
