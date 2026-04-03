from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import Field

from autoresearch.agent_protocol.models import (
    ArtifactRef,
    ExecutionPolicy,
    FallbackStep,
    JobSpec,
    ValidatorSpec,
)
from autoresearch.shared.models import StrictModel

from .models import RoutingDecision, RoutingInput, RoutingMode, RoutingPolicyOverlay
from .resolver import RoutingResolver, apply_policy_overlay


class ControlPlaneJobRequest(StrictModel):
    """Scheduler-owned request envelope materialized into `JobSpec` after routing."""

    run_id: str = Field(..., min_length=1)
    parent_run_id: str | None = None

    role: Literal["planner", "executor", "reviewer", "analyst"] = "executor"
    task: str = Field(..., min_length=1)
    input_artifacts: list[ArtifactRef] = Field(default_factory=list)

    policy: ExecutionPolicy = Field(default_factory=ExecutionPolicy)
    validators: list[ValidatorSpec] = Field(default_factory=list)
    fallback: list[FallbackStep] = Field(default_factory=list)

    metadata: dict[str, Any] = Field(default_factory=dict)

    requested_agent_id: str | None = None
    capability_hint: str | None = None
    policy_profile_hint: str | None = None
    validator_profile_hint: str | None = None
    mode_hint: RoutingMode | None = None

    def routing_input(self) -> RoutingInput:
        return RoutingInput(
            task=self.task,
            metadata=self.metadata,
            requested_agent_id=self.requested_agent_id,
            capability_hint=self.capability_hint,
            policy_profile_hint=self.policy_profile_hint,
            validator_profile_hint=self.validator_profile_hint,
            mode_hint=self.mode_hint,
        )


class ControlPlaneJobBuildResult(StrictModel):
    """Routing decision plus the materialized runner contract."""

    routing_decision: RoutingDecision
    job: JobSpec


class ControlPlaneJobBuilder:
    """Bridge routing decisions into concrete `JobSpec` materialization.

    This class is intentionally not an orchestration engine. It delegates route
    selection to `RoutingResolver`, materializes the scheduler-owned request
    into `JobSpec`, and stops there.

    It must not:
    - invent a fallback route when routing is ambiguous
    - pick the first manifest by scan order
    - synthesize retry/fallback workflow steps
    - dispatch execution
    """

    def __init__(
        self,
        manifests_dir: Path,
        *,
        default_agent_id: str | None = None,
        policy_overlays: Mapping[str, RoutingPolicyOverlay] | None = None,
        validator_profiles: Mapping[str, Sequence[ValidatorSpec]] | None = None,
    ) -> None:
        self._resolver = RoutingResolver(
            manifests_dir,
            default_agent_id=default_agent_id,
            policy_overlays=policy_overlays,
            validator_profiles=(validator_profiles or {}).keys(),
        )
        self._validator_profiles = {
            profile_id: [spec.model_copy(deep=True) for spec in specs]
            for profile_id, specs in (validator_profiles or {}).items()
        }

    def build(self, request: ControlPlaneJobRequest) -> ControlPlaneJobBuildResult:
        decision = self._resolver.decide(request.routing_input())
        routed_policy = apply_policy_overlay(request.policy, decision.policy_overlay)
        validators = self._merge_validators(
            self._validator_profiles_for(decision.validator_profile_id),
            request.validators,
        )

        job = JobSpec(
            run_id=request.run_id,
            parent_run_id=request.parent_run_id,
            agent_id=decision.selected_agent_id,
            role=request.role,
            mode=decision.selected_mode,
            task=request.task,
            input_artifacts=[artifact.model_copy(deep=True) for artifact in request.input_artifacts],
            policy=routed_policy,
            validators=validators,
            fallback=[step.model_copy(deep=True) for step in request.fallback],
            metadata=dict(request.metadata),
        )
        return ControlPlaneJobBuildResult(routing_decision=decision, job=job)

    def _validator_profiles_for(self, profile_id: str | None) -> list[ValidatorSpec]:
        if profile_id is None:
            return []
        specs = self._validator_profiles.get(profile_id)
        if specs is None:
            raise ValueError(f"unknown validator profile materialization: {profile_id}")
        return [spec.model_copy(deep=True) for spec in specs]

    @staticmethod
    def _merge_validators(
        profile_validators: Sequence[ValidatorSpec],
        explicit_validators: Sequence[ValidatorSpec],
    ) -> list[ValidatorSpec]:
        merged: list[ValidatorSpec] = []
        index_by_id: dict[str, int] = {}

        for spec in profile_validators:
            copied = spec.model_copy(deep=True)
            index_by_id[copied.id] = len(merged)
            merged.append(copied)

        for spec in explicit_validators:
            copied = spec.model_copy(deep=True)
            existing_index = index_by_id.get(copied.id)
            if existing_index is None:
                index_by_id[copied.id] = len(merged)
                merged.append(copied)
                continue
            merged[existing_index] = copied

        return merged
