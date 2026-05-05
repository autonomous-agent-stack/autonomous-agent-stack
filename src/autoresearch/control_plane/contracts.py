from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.shared.models import StrictModel, utc_now


class ControlPlaneTaskStatus(str, Enum):
    CREATED = "created"
    AWAITING_APPROVAL = "awaiting_approval"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ControlPlaneRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ControlPlaneApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ControlPlanePromotionStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ControlPlaneTaskCreateRequest(StrictModel):
    name: str = Field(..., min_length=1)
    intent: str | None = None
    session_id: str | None = None
    capability_id: str = "echo"
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_tags: list[str] = Field(default_factory=list)
    requested_by: str = "local-user"
    priority: int = Field(default=0, ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "capability_id", "requested_by", mode="before")
    @classmethod
    def _strip_required_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("session_id", "intent", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None

    @field_validator("risk_tags", mode="before")
    @classmethod
    def _normalize_risk_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",")]
        return sorted({str(item).strip().lower() for item in value if str(item).strip()})


class ControlPlaneApprovalDecisionRequest(StrictModel):
    decision: Literal["approved", "rejected"]
    decided_by: str = "local-approver"
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("decided_by", mode="before")
    @classmethod
    def _strip_decided_by(cls, value: Any) -> str:
        return str(value or "local-approver").strip() or "local-approver"


class ControlPlaneOperatorActionRequest(StrictModel):
    reason: str = "manual operation"
    requested_by: str = "control-plane"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reason", "requested_by", mode="before")
    @classmethod
    def _strip_action_text(cls, value: Any, info) -> str:
        fallback = "manual operation" if info.field_name == "reason" else "control-plane"
        return str(value or fallback).strip() or fallback


class ControlPlaneSessionRead(StrictModel):
    session_id: str
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    owner: str = "local-user"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlPlaneTaskRead(StrictModel):
    task_id: str
    session_id: str
    name: str
    intent: str | None = None
    status: ControlPlaneTaskStatus
    capability_id: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_tags: list[str] = Field(default_factory=list)
    requested_by: str = "local-user"
    approval_id: str | None = None
    run_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlPlaneRunRead(StrictModel):
    run_id: str
    task_id: str
    session_id: str
    capability_id: str
    status: ControlPlaneRunStatus
    worker_run_id: str | None = None
    output: dict[str, Any] | None = None
    error: str | None = None
    queued_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlPlaneApprovalRead(StrictModel):
    approval_id: str
    task_id: str
    session_id: str
    requested_by: str
    status: ControlPlaneApprovalStatus
    decided_by: str | None = None
    note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlPlaneCapabilityRead(StrictModel):
    capability_id: str
    name: str
    type: str
    enabled: bool
    dispatch_mode: Literal["worker_queue", "external_boundary", "future"]
    description: str
    risk_tags: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    external_calls_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlPlaneArtifactRead(StrictModel):
    artifact_id: str
    run_id: str
    session_id: str
    type: str
    uri: str
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlPlaneAuditEventRead(StrictModel):
    event_id: str
    session_id: str
    subject_type: str
    subject_id: str
    event_type: str
    message: str
    task_id: str | None = None
    run_id: str | None = None
    approval_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlPlanePromotionRead(StrictModel):
    promotion_id: str
    run_id: str
    session_id: str
    status: ControlPlanePromotionStatus = ControlPlanePromotionStatus.NOT_REQUESTED
    target: str | None = None
    artifact_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
