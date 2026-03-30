from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.agent_protocol.models import JobSpec, RunSummary
from autoresearch.shared.models import JobStatus, StrictModel
from autoresearch.shared.openhands_controlled_contract import ControlledExecutionRequest
from autoresearch.shared.openhands_worker_contract import OpenHandsWorkerJobSpec


class ManagerDispatchRequest(StrictModel):
    prompt: str = Field(..., min_length=1)
    pipeline_target: Literal["patch", "draft_pr"] = "draft_pr"
    target_base_branch: str = Field(default="main", min_length=1)
    max_iterations: int = Field(default=2, ge=1, le=5)
    approval_granted: bool = False
    auto_dispatch: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("prompt", "target_base_branch")
    @classmethod
    def _normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized


class ManagerIntentRead(StrictModel):
    intent_id: str
    label: str
    summary: str
    matched_keywords: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    suggested_test_paths: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ManagerPlanStrategy(str, Enum):
    SINGLE_TASK = "single_task"
    TASK_DAG = "task_dag"


class ManagerTaskStage(str, Enum):
    BACKEND = "backend"
    TESTS = "tests"
    FRONTEND = "frontend"
    GENERIC = "generic"


class ManagerPlanTaskRead(StrictModel):
    task_id: str
    title: str
    summary: str
    stage: ManagerTaskStage = ManagerTaskStage.GENERIC
    depends_on: list[str] = Field(default_factory=list)
    status: JobStatus = JobStatus.CREATED
    worker_spec: OpenHandsWorkerJobSpec | None = None
    controlled_request: ControlledExecutionRequest | None = None
    agent_job: JobSpec | None = None
    run_summary: RunSummary | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ManagerExecutionPlanRead(StrictModel):
    plan_id: str
    strategy: ManagerPlanStrategy = ManagerPlanStrategy.SINGLE_TASK
    summary: str = ""
    tasks: list[ManagerPlanTaskRead] = Field(default_factory=list)


class ManagerDispatchRead(StrictModel):
    dispatch_id: str
    prompt: str
    normalized_goal: str
    status: JobStatus
    summary: str = ""
    created_at: datetime
    updated_at: datetime
    selected_intent: ManagerIntentRead | None = None
    execution_plan: ManagerExecutionPlanRead | None = None
    worker_spec: OpenHandsWorkerJobSpec | None = None
    controlled_request: ControlledExecutionRequest | None = None
    agent_job: JobSpec | None = None
    run_summary: RunSummary | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
