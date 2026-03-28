from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field

from autoresearch.shared.models import PromotionPreflight, PromotionResult, StrictModel


class ControlledBackend(str, Enum):
    MOCK = "mock"
    OPENHANDS_CLI = "openhands_cli"


class FailureStrategy(str, Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    HUMAN_IN_LOOP = "human_in_loop"


class ValidationStatus(str, Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ControlledRunStatus(str, Enum):
    READY_FOR_PROMOTION = "ready_for_promotion"
    REJECTED = "rejected"
    NEEDS_HUMAN_REVIEW = "needs_human_review"


class ControlledExecutionArtifact(StrictModel):
    kind: Literal["log", "patch", "compliance", "summary", "validation"]
    path: str


class ControlledExecutionRequest(StrictModel):
    task_id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    backend: ControlledBackend = ControlledBackend.MOCK
    fallback_backend: ControlledBackend | None = None
    validation_command: list[str] = Field(default_factory=lambda: ["python3", "-m", "compileall", "-q", "src"])
    failure_strategy: FailureStrategy = FailureStrategy.HUMAN_IN_LOOP
    max_retries: int = Field(default=1, ge=0, le=3)
    cleanup_workspace_on_success: bool = True
    keep_workspace_on_failure: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class ControlledExecutionRead(StrictModel):
    run_id: str
    task_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    workspace: str
    workspace_retained: bool = True
    execution_log: str
    artifacts: list[ControlledExecutionArtifact] = Field(default_factory=list)
    changed_files: list[str] = Field(default_factory=list)
    exit_code: int
    validation_status: ValidationStatus
    validation_exit_code: int | None = None
    status: ControlledRunStatus
    retries_used: int = 0
    backend_used: ControlledBackend
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    promotion_preflight: PromotionPreflight | None = None
    promotion: PromotionResult | None = None
