"""Unified task contract for the control plane.

This is the canonical Python runtime equivalent of the TypeScript spec in
agent-control-plane/packages/core/src/types/task.ts.

All control-plane components (housekeeper, dispatch, worker registry) should
use these types. Worker-specific contracts (OpenHandsWorkerJobSpec,
LinuxSupervisorTaskCreateRequest, etc.) are legitimate *backend* translation
layers that convert from this unified model.

Status lifecycle::

    pending -> queued -> running -> succeeded
                                  -> failed
                                  -> needs_review
                     -> approval_required -> approved  -> queued
                                            -> rejected
              -> cancelled

Legacy JobStatus values map as follows::

    JobStatus.CREATED     -> TaskStatus.PENDING
    JobStatus.QUEUED      -> TaskStatus.QUEUED
    JobStatus.RUNNING     -> TaskStatus.RUNNING
    JobStatus.COMPLETED   -> TaskStatus.SUCCEEDED
    JobStatus.FAILED      -> TaskStatus.FAILED
    JobStatus.INTERRUPTED -> TaskStatus.FAILED
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import StrictModel, utc_now

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TaskStatus(str, Enum):
    """Unified task status across the control plane.

    Superset of TS TaskStatus + HousekeeperTaskStatus + ControlledRunStatus.
    """

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    APPROVAL_REQUIRED = "approval_required"
    NEEDS_REVIEW = "needs_review"
    REJECTED = "rejected"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ArtifactType(str, Enum):
    SCREENSHOT = "screenshot"
    LOG = "log"
    FILE = "file"
    RECEIPT = "receipt"
    METADATA = "metadata"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


class TaskArtifact(StrictModel):
    """A file or data artifact produced by a task run."""

    type: ArtifactType
    path: str
    size_bytes: int = 0
    mime_type: str = "application/octet-stream"
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskError(StrictModel):
    """Structured error information for a failed task."""

    code: str
    message: str
    details: Any = None
    retryable: bool = False
    suggested_action: Literal["retry", "manual", "skip", "escalate"] = "manual"
    occurred_at: datetime = Field(default_factory=utc_now)


class TaskResult(StrictModel):
    """Outcome of a completed task."""

    success: bool
    data: dict[str, Any] | None = None
    artifacts: list[TaskArtifact] = Field(default_factory=list)
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Core task model
# ---------------------------------------------------------------------------


class Task(StrictModel):
    """Canonical task representation in the control plane.

    Mirrors agent-control-plane Task interface.  Every component that creates,
    dispatches, or inspects tasks should use this model.
    """

    # Identity
    id: str
    type: str
    agent_package_id: str

    # Input / output
    input: dict[str, Any] = Field(default_factory=dict)
    result: TaskResult | None = None

    # Lifecycle
    status: TaskStatus = TaskStatus.PENDING

    # Approval gate
    requires_approval: bool = False
    approval_status: ApprovalStatus | None = None
    approvers: list[str] = Field(default_factory=list)

    # Execution binding
    worker_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    timeout_at: datetime | None = None

    # Error handling
    error: TaskError | None = None
    retry_count: int = 0
    max_retries: int = 3

    # Metadata
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    created_by: str | None = None
    tags: list[str] = Field(default_factory=list)
    priority: TaskPriority = TaskPriority.MEDIUM
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class CreateTaskRequest(StrictModel):
    """Parameters for creating a new task."""

    type: str
    agent_package_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    created_by: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    max_retries: int = 3
    timeout_seconds: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateTaskRequest(BaseModel):
    """Mutable fields when updating a task.

    Uses extra='ignore' so callers can send partial updates.
    """

    model_config = ConfigDict(extra="ignore")

    status: TaskStatus | None = None
    worker_id: str | None = None
    result: TaskResult | None = None
    error: TaskError | None = None
    approval_status: ApprovalStatus | None = None
    retry_count: int | None = None


class TaskQuery(BaseModel):
    """Filter parameters for listing tasks."""

    model_config = ConfigDict(extra="ignore")

    status: TaskStatus | None = None
    agent_package_id: str | None = None
    worker_id: str | None = None
    created_by: str | None = None
    priority: TaskPriority | None = None
    tags: list[str] = Field(default_factory=list)
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int = 50
    offset: int = 0


# ---------------------------------------------------------------------------
# Status transition helpers
# ---------------------------------------------------------------------------

# Legal forward transitions for each status.
_VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.APPROVAL_REQUIRED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.APPROVAL_REQUIRED, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.NEEDS_REVIEW,
        TaskStatus.CANCELLED,
    },
    TaskStatus.APPROVAL_REQUIRED: {TaskStatus.QUEUED, TaskStatus.REJECTED, TaskStatus.CANCELLED},
    TaskStatus.NEEDS_REVIEW: {
        TaskStatus.QUEUED,
        TaskStatus.SUCCEEDED,
        TaskStatus.FAILED,
        TaskStatus.REJECTED,
    },
    TaskStatus.REJECTED: set(),
    TaskStatus.SUCCEEDED: set(),
    TaskStatus.FAILED: {TaskStatus.QUEUED},  # retry
    TaskStatus.CANCELLED: set(),
}


def is_valid_transition(current: TaskStatus, target: TaskStatus) -> bool:
    """Return True if transitioning from *current* to *target* is legal."""
    return target in _VALID_TRANSITIONS.get(current, set())


# ---------------------------------------------------------------------------
# Legacy JobStatus mapping
# ---------------------------------------------------------------------------

from .models import JobStatus as _LegacyJobStatus  # noqa: E402

_JOB_STATUS_TO_TASK_STATUS: dict[_LegacyJobStatus, TaskStatus] = {
    _LegacyJobStatus.CREATED: TaskStatus.PENDING,
    _LegacyJobStatus.QUEUED: TaskStatus.QUEUED,
    _LegacyJobStatus.RUNNING: TaskStatus.RUNNING,
    _LegacyJobStatus.COMPLETED: TaskStatus.SUCCEEDED,
    _LegacyJobStatus.FAILED: TaskStatus.FAILED,
    _LegacyJobStatus.INTERRUPTED: TaskStatus.FAILED,
}

_TASK_STATUS_TO_JOB_STATUS: dict[TaskStatus, _LegacyJobStatus] = {
    TaskStatus.PENDING: _LegacyJobStatus.CREATED,
    TaskStatus.QUEUED: _LegacyJobStatus.QUEUED,
    TaskStatus.RUNNING: _LegacyJobStatus.RUNNING,
    TaskStatus.SUCCEEDED: _LegacyJobStatus.COMPLETED,
    TaskStatus.FAILED: _LegacyJobStatus.FAILED,
    TaskStatus.CANCELLED: _LegacyJobStatus.INTERRUPTED,
    TaskStatus.NEEDS_REVIEW: _LegacyJobStatus.RUNNING,
    TaskStatus.APPROVAL_REQUIRED: _LegacyJobStatus.CREATED,
    TaskStatus.REJECTED: _LegacyJobStatus.FAILED,
}


def job_status_to_task_status(js: _LegacyJobStatus) -> TaskStatus:
    return _JOB_STATUS_TO_TASK_STATUS[js]


def task_status_to_job_status(ts: TaskStatus) -> _LegacyJobStatus:
    return _TASK_STATUS_TO_JOB_STATUS[ts]


# ---------------------------------------------------------------------------
# HousekeeperTaskStatus bridge
# ---------------------------------------------------------------------------

from .housekeeper_contract import HousekeeperTaskStatus as _HousekeeperTaskStatus  # noqa: E402

_HOUSEKEEPER_TO_UNIFIED: dict[_HousekeeperTaskStatus, TaskStatus] = {
    _HousekeeperTaskStatus.CREATED: TaskStatus.PENDING,
    _HousekeeperTaskStatus.CLARIFICATION_REQUIRED: TaskStatus.NEEDS_REVIEW,
    _HousekeeperTaskStatus.APPROVAL_REQUIRED: TaskStatus.APPROVAL_REQUIRED,
    _HousekeeperTaskStatus.QUEUED: TaskStatus.QUEUED,
    _HousekeeperTaskStatus.RUNNING: TaskStatus.RUNNING,
    _HousekeeperTaskStatus.COMPLETED: TaskStatus.SUCCEEDED,
    _HousekeeperTaskStatus.FAILED: TaskStatus.FAILED,
    _HousekeeperTaskStatus.REJECTED: TaskStatus.REJECTED,
}

_UNIFIED_TO_HOUSEKEEPER: dict[TaskStatus, _HousekeeperTaskStatus] = {
    TaskStatus.PENDING: _HousekeeperTaskStatus.CREATED,
    TaskStatus.QUEUED: _HousekeeperTaskStatus.QUEUED,
    TaskStatus.RUNNING: _HousekeeperTaskStatus.RUNNING,
    TaskStatus.SUCCEEDED: _HousekeeperTaskStatus.COMPLETED,
    TaskStatus.FAILED: _HousekeeperTaskStatus.FAILED,
    TaskStatus.CANCELLED: _HousekeeperTaskStatus.FAILED,
    TaskStatus.APPROVAL_REQUIRED: _HousekeeperTaskStatus.APPROVAL_REQUIRED,
    TaskStatus.NEEDS_REVIEW: _HousekeeperTaskStatus.CLARIFICATION_REQUIRED,
    TaskStatus.REJECTED: _HousekeeperTaskStatus.REJECTED,
}


def housekeeper_status_to_task_status(hs: _HousekeeperTaskStatus) -> TaskStatus:
    return _HOUSEKEEPER_TO_UNIFIED[hs]


def task_status_to_housekeeper_status(ts: TaskStatus) -> _HousekeeperTaskStatus:
    return _UNIFIED_TO_HOUSEKEEPER[ts]
