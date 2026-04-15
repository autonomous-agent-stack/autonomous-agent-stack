from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from autoresearch.shared.models import ApprovalStatus, JobStatus, StrictModel


class HousekeeperBackendKind(str, Enum):
    MANAGER_AGENT = "manager_agent"
    LINUX_SUPERVISOR = "linux_supervisor"
    WIN_YINGDAO = "win_yingdao"
    OPENCLAW_RUNTIME = "openclaw_runtime"


class HousekeeperTaskStatus(str, Enum):
    CREATED = "created"
    CLARIFICATION_REQUIRED = "clarification_required"
    APPROVAL_REQUIRED = "approval_required"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"

    @classmethod
    def from_job_status(cls, status: JobStatus) -> "HousekeeperTaskStatus":
        mapping = {
            JobStatus.CREATED: cls.CREATED,
            JobStatus.QUEUED: cls.QUEUED,
            JobStatus.RUNNING: cls.RUNNING,
            JobStatus.COMPLETED: cls.COMPLETED,
            JobStatus.FAILED: cls.FAILED,
            JobStatus.INTERRUPTED: cls.FAILED,
        }
        return mapping[status]


class WorkerAvailabilityStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    BUSY = "busy"


class AgentPackageRecordRead(StrictModel):
    package_id: str
    name: str
    description: str
    version: str
    manifest_path: str
    execution_backend: HousekeeperBackendKind
    supported_worker_types: list[str] = Field(default_factory=list)
    required_capabilities: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"
    requires_approval: bool = False
    raw_manifest: dict[str, Any] = Field(default_factory=dict)


class WorkerRegistrationRead(StrictModel):
    worker_id: str
    name: str
    worker_type: str
    backend_kind: HousekeeperBackendKind | None = None
    status: WorkerAvailabilityStatus = WorkerAvailabilityStatus.OFFLINE
    capabilities: list[str] = Field(default_factory=list)
    last_heartbeat: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HousekeeperDispatchRequest(StrictModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    dry_run: bool = False

    @field_validator("session_id", "message")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class HousekeeperApprovalRequest(StrictModel):
    decided_by: str = Field(..., min_length=1)
    note: str | None = None

    @field_validator("decided_by")
    @classmethod
    def _normalize_decided_by(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("decided_by must not be empty")
        return normalized


class HousekeeperTaskRead(StrictModel):
    task_id: str
    session_id: str
    draft_id: str | None = None
    control_plane_task_id: str | None = None
    source_message: str
    normalized_intent: str = ""
    routing_reason: str = ""
    status: HousekeeperTaskStatus = HousekeeperTaskStatus.CREATED
    clarification_reason_code: str | None = None
    clarification_questions: list[str] = Field(default_factory=list)
    approval_status: ApprovalStatus | None = None
    approval_id: str | None = None
    agent_package_id: str | None = None
    selected_worker_id: str | None = None
    backend_kind: HousekeeperBackendKind | None = None
    backend_ref: str | None = None
    result_summary: str | None = None
    result_payload: dict[str, Any] = Field(default_factory=dict)
    memory_snapshot: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class HousekeeperTaskDraftRead(StrictModel):
    draft_id: str
    session_id: str
    source_message: str
    normalized_intent: str = ""
    candidate_package_ids: list[str] = Field(default_factory=list)
    candidate_backend_kinds: list[HousekeeperBackendKind] = Field(default_factory=list)
    routing_reason: str = ""
    clarification_reason_code: str | None = None
    clarification_questions: list[str] = Field(default_factory=list)
    memory_scope: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ControlPlaneTaskRead(StrictModel):
    task_id: str
    source_kind: str = "housekeeper"
    source_ref: str | None = None
    session_id: str | None = None
    draft_id: str | None = None
    housekeeper_task_id: str | None = None
    agent_package_id: str
    selected_worker_id: str
    backend_kind: HousekeeperBackendKind
    status: HousekeeperTaskStatus = HousekeeperTaskStatus.CREATED
    approval_status: ApprovalStatus | None = None
    approval_id: str | None = None
    backend_ref: str | None = None
    summary: str | None = None
    result_payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    error: str | None = None
