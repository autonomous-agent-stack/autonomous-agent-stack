from __future__ import annotations

"""Legacy compatibility schemas for the old frontdesk-only housekeeper path.

Active runtime/API contracts live in ``autoresearch.shared.housekeeper_contract``.
Keep this module for compatibility only; do not wire new runtime behavior to it.
"""

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from autoresearch.shared.housekeeper_contract import HousekeeperBackendKind, HousekeeperTaskStatus
from autoresearch.shared.models import ApprovalRisk, ApprovalStatus, MemoryScope, StrictModel


class LegacyFrontdeskDispatchRequest(StrictModel):
    """Deprecated compatibility schema for the old frontdesk dispatch request."""

    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    dry_run: bool = False
    allowed_memory_scopes: list[MemoryScope] = Field(
        default_factory=lambda: [MemoryScope.SESSION, MemoryScope.PERSONAL, MemoryScope.SHARED]
    )

    @field_validator("session_id", "message")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("allowed_memory_scopes")
    @classmethod
    def _validate_memory_scopes(cls, value: list[MemoryScope]) -> list[MemoryScope]:
        allowed = {MemoryScope.SESSION, MemoryScope.PERSONAL, MemoryScope.SHARED}
        normalized: list[MemoryScope] = []
        for scope in value:
            if scope not in allowed:
                raise ValueError("housekeeper memory access is limited to session/personal/shared")
            if scope not in normalized:
                normalized.append(scope)
        if not normalized:
            return [MemoryScope.SESSION]
        return normalized


class LegacyFrontdeskApprovalRequest(StrictModel):
    """Deprecated compatibility schema for the old frontdesk approval payload."""

    requires_approval: bool = True
    risk: ApprovalRisk = ApprovalRisk.WRITE
    reason: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("reason", "prompt")
    @classmethod
    def _normalize_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class LegacyFrontdeskTaskRead(StrictModel):
    """Deprecated compatibility schema for the old frontdesk task read model."""

    task_id: str
    session_id: str
    source_message: str
    normalized_intent: str = ""
    routing_reason: str = ""
    status: HousekeeperTaskStatus = HousekeeperTaskStatus.CREATED
    clarification_reason_code: str | None = None
    clarification_questions: list[str] = Field(default_factory=list)
    approval_status: ApprovalStatus | None = None
    approval_request: LegacyFrontdeskApprovalRequest | None = None
    agent_package_id: str | None = None
    backend_kind: HousekeeperBackendKind | None = None
    result_summary: str | None = None
    result_payload: dict[str, Any] = Field(default_factory=dict)
    memory_snapshot: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    error: str | None = None


# Compatibility aliases for any remaining imports from the pre-cleanup module path.
HousekeeperDispatchRequest = LegacyFrontdeskDispatchRequest
HousekeeperApprovalRequest = LegacyFrontdeskApprovalRequest
HousekeeperTaskRead = LegacyFrontdeskTaskRead
