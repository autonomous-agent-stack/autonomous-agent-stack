from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class JobStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class ScoreDirection(str, Enum):
    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class OptimizationStrategy(str, Enum):
    HILL_CLIMBING = "hill_climbing"
    SIMULATED_ANNEALING = "simulated_annealing"
    GENETIC = "genetic"


class EvaluatorCommand(StrictModel):
    command: list[str] = Field(..., min_length=1)
    timeout_seconds: int = Field(default=300, ge=1)
    work_dir: str | None = None
    env: dict[str, str] = Field(default_factory=dict)


class EvaluationCreateRequest(StrictModel):
    task_name: str = Field(..., min_length=1)
    config_path: str = "task.json"
    description: str = "manual run"
    evaluator_command: EvaluatorCommand | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("evaluator_command", mode="before")
    @classmethod
    def normalize_evaluator_command(cls, value: Any) -> Any:
        if isinstance(value, list):
            return {"command": value}
        return value


class EvaluationRead(StrictModel):
    evaluation_id: str
    task_name: str
    config_path: str
    description: str
    status: JobStatus
    result_status: str | None = None
    run_id: str | None = None
    score: float | None = None
    summary: str | None = None
    duration_seconds: float | None = None
    artifact_dir: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ExecutionCreateRequest(StrictModel):
    name: str = Field(..., min_length=1)
    command: list[str] = Field(..., min_length=1)
    timeout_seconds: int = Field(default=300, ge=1, le=3600)
    work_dir: str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionRead(StrictModel):
    execution_id: str
    name: str
    status: JobStatus
    command: list[str] = Field(default_factory=list)
    timeout_seconds: int
    work_dir: str | None = None
    returncode: int | None = None
    stdout_preview: str | None = None
    stderr_preview: str | None = None
    duration_seconds: float | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class OpenClawSessionCreateRequest(StrictModel):
    channel: str = "api"
    external_id: str | None = None
    title: str = "openclaw-session"
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpenClawSessionEventAppendRequest(StrictModel):
    role: Literal["system", "user", "assistant", "tool", "status"] = "status"
    content: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OpenClawSessionRead(StrictModel):
    session_id: str
    channel: str
    external_id: str | None = None
    title: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    events: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class ClaudeAgentCreateRequest(StrictModel):
    task_name: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    agent_name: str | None = None
    session_id: str | None = None
    parent_agent_id: str | None = None
    generation_depth: int = Field(default=1, ge=1, le=10)
    timeout_seconds: int = Field(default=900, ge=1, le=7200)
    work_dir: str | None = None
    cli_args: list[str] = Field(default_factory=list)
    command_override: list[str] | None = None
    append_prompt: bool = True
    env: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaudeAgentRunRead(StrictModel):
    agent_run_id: str
    task_name: str
    prompt: str
    status: JobStatus
    agent_name: str | None = None
    session_id: str | None = None
    parent_agent_id: str | None = None
    generation_depth: int
    command: list[str] = Field(default_factory=list)
    timeout_seconds: int
    work_dir: str | None = None
    returncode: int | None = None
    stdout_preview: str | None = None
    stderr_preview: str | None = None
    duration_seconds: float | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class TelegramWebhookAck(StrictModel):
    accepted: bool
    update_id: int | None = None
    chat_id: str | None = None
    session_id: str | None = None
    agent_run_id: str | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaudeAgentCancelRequest(StrictModel):
    reason: str = "cancelled by user"


class ClaudeAgentRetryRequest(StrictModel):
    reason: str = "manual retry"
    prompt_override: str | None = None
    timeout_seconds_override: int | None = Field(default=None, ge=1, le=7200)
    metadata_updates: dict[str, Any] = Field(default_factory=dict)


class ClaudeAgentTreeEdgeRead(StrictModel):
    parent_agent_run_id: str
    child_agent_run_id: str


class ClaudeAgentTreeNodeRead(StrictModel):
    agent_run_id: str
    parent_agent_id: str | None = None
    session_id: str | None = None
    task_name: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    children: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaudeAgentTreeRead(StrictModel):
    session_id: str | None = None
    root_agent_run_ids: list[str] = Field(default_factory=list)
    nodes: list[ClaudeAgentTreeNodeRead] = Field(default_factory=list)
    edges: list[ClaudeAgentTreeEdgeRead] = Field(default_factory=list)
    mermaid: str = ""


class OpenVikingCompactRequest(StrictModel):
    keep_recent_events: int = Field(default=12, ge=1, le=200)
    summary_max_chars: int = Field(default=1200, ge=200, le=20000)


class OpenVikingMemoryProfileRead(StrictModel):
    session_id: str
    original_event_count: int
    retained_event_count: int
    compressed_event_count: int
    estimated_tokens_before: int
    estimated_tokens_after: int
    compression_ratio: float
    summary: str
    updated_at: datetime


class MiroFishPredictionRequest(StrictModel):
    task_name: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MiroFishPredictionRead(StrictModel):
    engine: str
    score: float = Field(..., ge=0.0, le=1.0)
    decision: Literal["allow", "review", "reject"]
    reasons: list[str] = Field(default_factory=list)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportCreateRequest(StrictModel):
    evaluation_id: str | None = None
    experiment_id: str | None = None
    format: Literal["markdown", "json", "html"] = "markdown"
    sections: list[str] = Field(
        default_factory=lambda: ["summary", "metrics", "recommendations"]
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReportRead(StrictModel):
    report_id: str
    evaluation_id: str | None = None
    experiment_id: str | None = None
    status: JobStatus
    format: str
    content: str
    sections: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class VariantCreateRequest(StrictModel):
    experiment_id: str | None = None
    base_prompt: str = Field(..., min_length=1)
    strategy_hint: str = "baseline"
    max_variants: int = Field(default=3, ge=1, le=20)
    metadata: dict[str, Any] = Field(default_factory=dict)


class VariantRead(StrictModel):
    variant_id: str
    experiment_id: str | None = None
    status: JobStatus
    base_prompt: str
    strategy_hint: str
    content: str
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizationCreateRequest(StrictModel):
    experiment_id: str = Field(..., min_length=1)
    objective: str = Field(..., min_length=1)
    strategy: OptimizationStrategy = OptimizationStrategy.HILL_CLIMBING
    max_iterations: int = Field(default=10, ge=1, le=1000)
    early_stop_patience: int = Field(default=3, ge=0, le=100)
    rollback_on_regression: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class OptimizationRead(StrictModel):
    optimization_id: str
    experiment_id: str
    objective: str
    strategy: OptimizationStrategy
    max_iterations: int
    early_stop_patience: int
    rollback_on_regression: bool
    status: JobStatus
    best_variant_id: str | None = None
    best_score: float | None = None
    last_score: float | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentCreateRequest(StrictModel):
    name: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    mutable_paths: list[str] = Field(default_factory=list)
    evaluation_command: list[str] = Field(default_factory=list)
    score_direction: ScoreDirection = ScoreDirection.MAXIMIZE
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExperimentRead(StrictModel):
    experiment_id: str
    name: str
    problem_statement: str
    mutable_paths: list[str] = Field(default_factory=list)
    evaluation_command: list[str] = Field(default_factory=list)
    score_direction: ScoreDirection
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
