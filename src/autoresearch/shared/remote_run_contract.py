from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.agent_protocol.models import JobSpec, RunSummary
from autoresearch.shared.models import StrictModel, utc_now


def _normalize_non_empty_text(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("value must not be empty")
    return normalized


def _normalize_relative_artifact_path(value: str) -> str:
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        raise ValueError("artifact path must not be empty")
    candidate = PurePosixPath(normalized)
    if candidate.is_absolute():
        raise ValueError("artifact paths must be repo-relative or runtime-relative")
    parts = candidate.parts
    if any(part == ".." for part in parts):
        raise ValueError("artifact paths must stay inside the repo/runtime root")
    return normalized


def _normalize_artifact_paths(value: dict[str, str] | None) -> dict[str, str]:
    if not value:
        return {}
    normalized: dict[str, str] = {}
    for raw_key, raw_path in value.items():
        key = _normalize_non_empty_text(str(raw_key))
        normalized[key] = _normalize_relative_artifact_path(str(raw_path))
    return normalized


class DispatchLane(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


class RemoteRunStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    STALLED = "stalled"
    TIMED_OUT = "timed_out"


class FailureClass(str, Enum):
    PLANNER_STALLED = "planner_stalled"
    EXECUTOR_STALLED = "executor_stalled"
    TOOL_TIMEOUT = "tool_timeout"
    MODEL_FALLBACK = "model_fallback"
    ASSERTION_FAILED_AFTER_FALLBACK = "assertion_failed_after_fallback"
    ENV_MISSING = "env_missing"
    WORKSPACE_DIRTY = "workspace_dirty"
    TRANSIENT_NETWORK = "transient_network"
    UNKNOWN = "unknown"


class RecoveryAction(str, Enum):
    RETRY = "retry"
    ABORT = "abort"
    REQUIRE_HUMAN_REVIEW = "require_human_review"
    DOWNGRADE_TO_DRAFT = "downgrade_to_draft"
    QUARANTINE = "quarantine"


class RemoteTaskSpec(StrictModel):
    protocol_version: Literal["remote-run/v1"] = "remote-run/v1"
    run_id: str = Field(..., min_length=1)
    requested_lane: DispatchLane = DispatchLane.LOCAL
    lane: DispatchLane = DispatchLane.LOCAL
    runtime_mode: str = Field(default="day", min_length=1)
    planner_plan_id: str | None = None
    planner_candidate_id: str | None = None
    job: JobSpec
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("run_id", "runtime_mode")
    @classmethod
    def _normalize_required_text(cls, value: str) -> str:
        return _normalize_non_empty_text(value)

    @field_validator("planner_plan_id", "planner_candidate_id")
    @classmethod
    def _normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class RemoteRunRecord(StrictModel):
    protocol_version: Literal["remote-run/v1"] = "remote-run/v1"
    run_id: str = Field(..., min_length=1)
    requested_lane: DispatchLane = DispatchLane.LOCAL
    lane: DispatchLane = DispatchLane.LOCAL
    status: RemoteRunStatus = RemoteRunStatus.QUEUED
    failure_class: FailureClass | None = None
    recovery_action: RecoveryAction | None = None
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    started_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    fallback_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("run_id")
    @classmethod
    def _normalize_run_id(cls, value: str) -> str:
        return _normalize_non_empty_text(value)

    @field_validator("summary")
    @classmethod
    def _normalize_summary(cls, value: str) -> str:
        return value.strip()

    @field_validator("fallback_reason")
    @classmethod
    def _normalize_fallback_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("artifact_paths", mode="before")
    @classmethod
    def _validate_artifact_paths(cls, value: dict[str, str] | None) -> dict[str, str]:
        return _normalize_artifact_paths(value)


class RemoteHeartbeat(StrictModel):
    protocol_version: Literal["remote-run/v1"] = "remote-run/v1"
    run_id: str = Field(..., min_length=1)
    lane: DispatchLane = DispatchLane.LOCAL
    status: RemoteRunStatus = RemoteRunStatus.RUNNING
    sequence: int = Field(default=1, ge=1)
    summary: str = ""
    recorded_at: datetime = Field(default_factory=utc_now)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("run_id")
    @classmethod
    def _normalize_heartbeat_run_id(cls, value: str) -> str:
        return _normalize_non_empty_text(value)

    @field_validator("summary")
    @classmethod
    def _normalize_heartbeat_summary(cls, value: str) -> str:
        return value.strip()

    @field_validator("artifact_paths", mode="before")
    @classmethod
    def _validate_heartbeat_artifact_paths(cls, value: dict[str, str] | None) -> dict[str, str]:
        return _normalize_artifact_paths(value)


class RemoteRunSummary(RemoteRunRecord):
    run_summary: RunSummary | None = None


class RemoteWorkerHealthRead(StrictModel):
    protocol_version: Literal["remote-run/v1"] = "remote-run/v1"
    healthy: bool = False
    host: str | None = None
    detail: str = ""
    checked_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("host")
    @classmethod
    def _normalize_host(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("detail")
    @classmethod
    def _normalize_detail(cls, value: str) -> str:
        return value.strip()
