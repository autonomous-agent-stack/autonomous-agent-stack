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
