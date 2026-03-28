from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from autoresearch.agent_protocol.models import ExecutionPolicy
from autoresearch.shared.models import StrictModel


class AutoResearchWorkerJobSpec(StrictModel):
    protocol_version: Literal["autoresearch-worker/v1"] = "autoresearch-worker/v1"
    job_id: str = Field(..., min_length=1)
    research_task: str = Field(..., min_length=1)
    allowed_paths: list[str] = Field(..., min_length=1)
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
    test_command: str = Field(..., min_length=1)
    deliverables: list[Literal["execution_plan", "test_plan", "risk_summary", "patch_suggestion"]] = (
        Field(
            default_factory=lambda: [
                "execution_plan",
                "test_plan",
                "risk_summary",
                "patch_suggestion",
            ]
        )
    )
    network_policy: Literal["disabled", "allowlist", "full"] = "disabled"
    network_allowlist: list[str] = Field(default_factory=list)
    worker_output_mode: Literal["patch"] = "patch"
    pipeline_target: Literal["patch", "draft_pr"] = "patch"
    target_base_branch: str = "main"
    max_iterations: int = Field(default=1, ge=1, le=5)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("allowed_paths", "forbidden_paths")
    @classmethod
    def _normalize_globs(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            candidate = item.strip().replace("\\", "/")
            if not candidate:
                continue
            if candidate.startswith("/"):
                raise ValueError("path patterns must be repo-relative")
            if candidate.startswith("../") or "/../" in candidate:
                raise ValueError("path patterns must stay inside the repo")
            if candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
        if not normalized:
            raise ValueError("at least one path pattern is required")
        return normalized

    @field_validator("deliverables", mode="before")
    @classmethod
    def _normalize_deliverables(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        allowed = {"execution_plan", "test_plan", "risk_summary", "patch_suggestion"}
        for item in value:
            candidate = item.strip().lower()
            if not candidate:
                continue
            if candidate not in allowed:
                raise ValueError(f"unsupported deliverable: {candidate}")
            if candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
        if not normalized:
            raise ValueError("at least one deliverable is required")
        return normalized

    @field_validator("target_base_branch")
    @classmethod
    def _normalize_base_branch(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("target_base_branch is required")
        return normalized

    @field_validator("pipeline_target")
    @classmethod
    def _normalize_pipeline_target(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"patch", "draft_pr"}:
            raise ValueError("pipeline_target must be patch or draft_pr")
        return normalized

    @field_validator("test_command")
    @classmethod
    def _normalize_test_command(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("test_command is required")
        return normalized

    def build_execution_policy(self) -> ExecutionPolicy:
        return ExecutionPolicy(
            network=self.network_policy,
            network_allowlist=list(self.network_allowlist),
            allowed_paths=list(self.allowed_paths),
            forbidden_paths=list(self.forbidden_paths),
            cleanup_on_success=True,
            retain_workspace_on_failure=True,
        )
