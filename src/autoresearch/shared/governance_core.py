from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.shared.models import StrictModel, utc_now


class GovernanceTaskStatus(str, Enum):
    CREATED = "created"
    AWAITING_APPROVAL = "awaiting_approval"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


class GovernanceRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GovernanceApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class GovernanceTaskCreateRequest(StrictModel):
    name: str = Field(..., min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_tags: list[str] = Field(default_factory=list)
    adapter_id: str = "echo"
    owner: str = "local-user"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "adapter_id", "owner", mode="before")
    @classmethod
    def _strip_required_text(cls, value: Any) -> str:
        return str(value or "").strip()

    @field_validator("risk_tags", mode="before")
    @classmethod
    def _normalize_risk_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",")]
        return sorted({str(item).strip().lower() for item in value if str(item).strip()})


class GovernanceApprovalDecisionRequest(StrictModel):
    decision: Literal["approved", "rejected"]
    approver: str = "local-approver"
    note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("approver", mode="before")
    @classmethod
    def _strip_approver(cls, value: Any) -> str:
        return str(value or "local-approver").strip() or "local-approver"


class GovernanceTaskRead(StrictModel):
    task_id: str
    name: str
    status: GovernanceTaskStatus
    parameters: dict[str, Any] = Field(default_factory=dict)
    risk_tags: list[str] = Field(default_factory=list)
    adapter_id: str = "echo"
    owner: str = "local-user"
    approval_id: str | None = None
    run_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceRunRead(StrictModel):
    run_id: str
    task_id: str
    adapter_id: str
    status: GovernanceRunStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    queued_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceSessionRead(StrictModel):
    session_id: str
    user_id: str
    context: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceApprovalRead(StrictModel):
    approval_id: str
    task_id: str
    requested_by: str
    status: GovernanceApprovalStatus
    approver: str | None = None
    note: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceAdapterRead(StrictModel):
    adapter_id: str
    name: str
    type: str
    enabled: bool
    description: str
    capabilities: list[str] = Field(default_factory=list)
    external_calls_enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceArtifactRead(StrictModel):
    artifact_id: str
    run_id: str
    type: str
    uri: str
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GovernanceAuditEventRead(StrictModel):
    event_id: str
    subject_type: str
    subject_id: str
    event_type: str
    message: str
    run_id: str | None = None
    task_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
