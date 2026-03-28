from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.shared.models import GitPromotionMode, PromotionPreflight, PromotionResult, StrictModel


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
    FAILED = "failed"
    REJECTED = "rejected"
    NEEDS_HUMAN_REVIEW = "needs_human_review"
    POLICY_BLOCKED = "policy_blocked"


class ControlledExecutionArtifact(StrictModel):
    kind: Literal["log", "patch", "compliance", "summary", "validation"]
    path: str


class PatchResult(StrictModel):
    output_mode: Literal["patch"] = "patch"
    patch_path: str
    patch_text: str = ""
    changed_files: list[str] = Field(default_factory=list)
    stdout: str = ""
    stderr: str = ""


class ControlledExecutionRequest(StrictModel):
    task_id: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    allowed_paths: list[str] = Field(..., min_length=1)
    forbidden_paths: list[str] = Field(default_factory=list)
    test_command: list[str] = Field(..., min_length=1)
    backend: ControlledBackend = ControlledBackend.MOCK
    fallback_backend: ControlledBackend | None = None
    worker_output_mode: Literal["patch"] = "patch"
    pipeline_target: GitPromotionMode = GitPromotionMode.PATCH
    max_iterations: int = Field(default=1, ge=1, le=5)
    failure_strategy: FailureStrategy = FailureStrategy.HUMAN_IN_LOOP
    cleanup_workspace_on_success: bool = True
    keep_workspace_on_failure: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("allowed_paths", mode="before")
    @classmethod
    def _normalize_allowed_paths(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            candidate = item.strip().replace("\\", "/")
            if not candidate:
                continue
            if candidate.startswith("/") or candidate.startswith("../") or "/../" in candidate:
                raise ValueError("path patterns must stay inside the repo")
            if candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
        if not normalized:
            raise ValueError("allowed_paths must not be empty")
        return normalized

    @field_validator("forbidden_paths", mode="before")
    @classmethod
    def _normalize_forbidden_paths(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            candidate = item.strip().replace("\\", "/")
            if not candidate:
                continue
            if candidate.startswith("/") or candidate.startswith("../") or "/../" in candidate:
                raise ValueError("path patterns must stay inside the repo")
            if candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
        return normalized

    @field_validator("test_command")
    @classmethod
    def _normalize_test_command(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if not normalized:
            raise ValueError("test_command is required")
        return normalized


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
    iterations_used: int = 0
    backend_used: ControlledBackend
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    patch_result: PatchResult | None = None
    promotion_preflight: PromotionPreflight | None = None
    promotion: PromotionResult | None = None
