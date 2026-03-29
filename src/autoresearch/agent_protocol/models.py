from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from autoresearch.shared.models import PromotionPreflight, PromotionResult, StrictModel


class ArtifactRef(StrictModel):
    name: str
    kind: Literal["log", "report", "plan", "patch", "compliance", "custom"]
    uri: str
    sha256: str | None = None


class ExecutionPolicy(StrictModel):
    timeout_sec: int = Field(default=900, ge=1, le=7200)
    max_steps: int = Field(default=1, ge=1, le=20)
    network: Literal["disabled", "allowlist", "full"] = "disabled"
    network_allowlist: list[str] = Field(default_factory=list)

    tool_allowlist: list[str] = Field(default_factory=lambda: ["read", "write", "bash"])

    allowed_paths: list[str] = Field(default_factory=lambda: ["src/**", "tests/**", "docs/**", "apps/**"])
    forbidden_paths: list[str] = Field(
        default_factory=lambda: [
            ".git/**",
            "logs/**",
            ".masfactory_runtime/**",
            "memory/**",
            "**/*.key",
            "**/*.pem",
        ]
    )

    max_changed_files: int = Field(default=20, ge=0, le=1000)
    max_patch_lines: int = Field(default=500, ge=0, le=100000)
    allow_binary_changes: bool = False

    cleanup_on_success: bool = True
    retain_workspace_on_failure: bool = True


class ValidatorSpec(StrictModel):
    id: str
    kind: Literal["builtin", "command", "human"]
    command: str | None = None


class FallbackStep(StrictModel):
    action: Literal["retry", "fallback_agent", "human_review", "reject"]
    agent_id: str | None = None
    max_attempts: int = Field(default=1, ge=1, le=20)


class JobSpec(StrictModel):
    protocol_version: Literal["aep/v0"] = "aep/v0"

    run_id: str
    parent_run_id: str | None = None

    agent_id: str
    role: Literal["planner", "executor", "reviewer", "analyst"] = "executor"
    mode: Literal["plan_only", "patch_only", "apply_in_workspace", "review_only"] = "patch_only"

    task: str
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)

    policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    validators: list[ValidatorSpec] = Field(default_factory=list)
    fallback: list[FallbackStep] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)


class DriverMetrics(StrictModel):
    duration_ms: int = 0
    steps: int = 0
    commands: int = 0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    first_progress_ms: int | None = None
    first_scoped_write_ms: int | None = None
    first_state_heartbeat_ms: int | None = None


class DriverResult(StrictModel):
    protocol_version: Literal["aep/v0"] = "aep/v0"

    run_id: str
    agent_id: str
    attempt: int = 1

    status: Literal[
        "succeeded",
        "partial",
        "failed",
        "timed_out",
        "stalled_no_progress",
        "policy_blocked",
        "contract_error",
    ]

    summary: str
    changed_paths: list[str] = Field(default_factory=list)
    output_artifacts: list[ArtifactRef] = Field(default_factory=list)

    metrics: DriverMetrics = Field(default_factory=DriverMetrics)

    recommended_action: Literal[
        "promote",
        "retry",
        "fallback",
        "human_review",
        "reject",
    ] = "human_review"

    error: str | None = None


class ValidationCheck(StrictModel):
    id: str
    passed: bool
    detail: str = ""
    artifact: ArtifactRef | None = None


class ValidationReport(StrictModel):
    run_id: str
    passed: bool
    checks: list[ValidationCheck] = Field(default_factory=list)


class RunSummary(StrictModel):
    run_id: str
    final_status: Literal[
        "ready_for_promotion",
        "blocked",
        "failed",
        "promoted",
        "human_review",
    ]
    driver_result: DriverResult
    validation: ValidationReport
    promotion_patch_uri: str | None = None
    promotion_preflight: PromotionPreflight | None = None
    promotion: PromotionResult | None = None


class AgentManifest(StrictModel):
    id: str
    kind: Literal["process"] = "process"
    entrypoint: str
    version: str = "0.1"
    capabilities: list[str] = Field(default_factory=list)
    default_mode: Literal["plan_only", "patch_only", "apply_in_workspace", "review_only"] = (
        "apply_in_workspace"
    )
    policy_defaults: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
