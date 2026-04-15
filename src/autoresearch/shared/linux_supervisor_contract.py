from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field

from autoresearch.shared.models import StrictModel


class LinuxSupervisorTaskKind(str, Enum):
    AEP_AGENT_RUN = "aep_agent_run"


class LinuxSupervisorTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class LinuxSupervisorConclusion(str, Enum):
    SUCCEEDED = "succeeded"
    STALLED_NO_PROGRESS = "stalled_no_progress"
    TIMED_OUT = "timed_out"
    MOCK_FALLBACK = "mock_fallback"
    ASSERTION_FAILED = "assertion_failed"
    INFRA_ERROR = "infra_error"
    UNKNOWN = "unknown"


class LinuxSupervisorTaskCreateRequest(StrictModel):
    prompt: str = Field(..., min_length=1)
    agent_id: str = Field(default="openhands", min_length=1)
    retry: int = Field(default=1, ge=0, le=5)
    fallback_agent: str | None = "mock"
    validator_commands: list[str] = Field(default_factory=list)
    total_timeout_sec: int = Field(default=1800, ge=1, le=86400)
    stall_timeout_sec: int = Field(default=600, ge=1, le=86400)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LinuxSupervisorTaskRead(LinuxSupervisorTaskCreateRequest):
    task_id: str
    run_id: str
    kind: LinuxSupervisorTaskKind = LinuxSupervisorTaskKind.AEP_AGENT_RUN
    created_at: datetime


class LinuxSupervisorTaskStatusRead(StrictModel):
    task_id: str
    run_id: str
    status: LinuxSupervisorTaskStatus
    updated_at: datetime
    claimed_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    pid: int | None = None
    current_phase: str = "queued"
    last_error: str | None = None
    conclusion: LinuxSupervisorConclusion | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LinuxSupervisorTaskHeartbeatRead(StrictModel):
    task_id: str
    run_id: str
    status: LinuxSupervisorTaskStatus
    observed_at: datetime
    pid: int | None = None
    current_phase: str = "queued"
    elapsed_seconds: float = 0.0
    last_progress_at: datetime | None = None
    last_progress_signature: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LinuxSupervisorTaskSummaryRead(StrictModel):
    task_id: str
    run_id: str
    status: LinuxSupervisorTaskStatus
    conclusion: LinuxSupervisorConclusion
    success: bool = False
    agent_id: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float = 0.0
    process_returncode: int | None = None
    aep_final_status: str | None = None
    aep_driver_status: str | None = None
    used_mock_fallback: bool = False
    message: str = ""
    task_dir: str
    run_dir: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LinuxSupervisorProcessStatusRead(StrictModel):
    status: Literal["idle", "running", "stopped"] = "stopped"
    pid: int | None = None
    current_task_id: str | None = None
    last_task_id: str | None = None
    queue_depth: int = 0
    started_at: datetime | None = None
    updated_at: datetime
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LinuxSupervisorProcessHeartbeatRead(StrictModel):
    observed_at: datetime
    pid: int | None = None
    current_task_id: str | None = None
    queue_depth: int = 0
    status: Literal["idle", "running", "stopped"] = "stopped"
    metadata: dict[str, Any] = Field(default_factory=dict)
