from __future__ import annotations

import shlex

from autoresearch.agent_protocol.models import ExecutionPolicy, FallbackStep, JobSpec, ValidatorSpec
from autoresearch.shared.openhands_controlled_contract import (
    ControlledBackend,
    ControlledExecutionRequest,
    FailureStrategy,
)
from autoresearch.shared.openhands_worker_contract import OpenHandsWorkerJobSpec


class OpenHandsWorkerService:
    """Translate a patch-only OpenHands worker contract into existing AEP/backends."""

    def build_prompt(self, spec: OpenHandsWorkerJobSpec) -> str:
        allowed_paths = "\n".join(f"- {item}" for item in spec.allowed_paths)
        forbidden_paths = "\n".join(f"- {item}" for item in spec.forbidden_paths)
        return (
            "You are OpenHands operating as a constrained patch-only worker.\n\n"
            "Problem statement:\n"
            f"{spec.problem_statement}\n\n"
            "Hard rules:\n"
            "- Only modify files that match allowed_paths.\n"
            "- Never modify forbidden_paths.\n"
            "- Do not run git add, git commit, git push, git merge, git rebase, git reset, or git checkout.\n"
            "- Do not create product-facing entrypoints or change approval/promotion policy.\n"
            "- Produce the smallest patch that can satisfy the validation command.\n"
            "- Leave branch creation and draft PR creation to the promotion gate.\n\n"
            "allowed_paths:\n"
            f"{allowed_paths}\n\n"
            "forbidden_paths:\n"
            f"{forbidden_paths}\n\n"
            "validation_command:\n"
            f"- {spec.test_command}\n"
        )

    def build_agent_job_spec(self, spec: OpenHandsWorkerJobSpec) -> JobSpec:
        fallback: list[FallbackStep] = []
        if spec.max_retries > 0:
            fallback.append(FallbackStep(action="retry", max_attempts=spec.max_retries))
        if spec.use_mock_fallback:
            fallback.append(FallbackStep(action="fallback_agent", agent_id="mock", max_attempts=1))
        fallback.append(FallbackStep(action="human_review", max_attempts=1))

        return JobSpec(
            run_id=spec.job_id,
            agent_id="openhands",
            role="executor",
            mode="patch_only",
            task=self.build_prompt(spec),
            policy=ExecutionPolicy(
                allowed_paths=list(spec.allowed_paths),
                forbidden_paths=list(spec.forbidden_paths),
                cleanup_on_success=True,
                retain_workspace_on_failure=True,
            ),
            validators=[
                ValidatorSpec(
                    id="worker.test_command",
                    kind="command",
                    command=spec.test_command,
                )
            ],
            fallback=fallback,
            metadata={
                **dict(spec.metadata),
                "worker_contract": spec.protocol_version,
                "sandbox_runtime": spec.sandbox_runtime,
                "output_mode": spec.output_mode,
                "target_base_branch": spec.target_base_branch,
                "promotion_mode": "patch",
            },
        )

    def build_controlled_request(self, spec: OpenHandsWorkerJobSpec) -> ControlledExecutionRequest:
        validation_command = shlex.split(spec.test_command)
        fallback_backend = ControlledBackend.MOCK if spec.use_mock_fallback else None
        failure_strategy = FailureStrategy.FALLBACK if fallback_backend is not None else FailureStrategy.HUMAN_IN_LOOP
        return ControlledExecutionRequest(
            task_id=spec.job_id,
            prompt=self.build_prompt(spec),
            backend=ControlledBackend.OPENHANDS_CLI,
            fallback_backend=fallback_backend,
            validation_command=validation_command,
            failure_strategy=failure_strategy,
            max_retries=spec.max_retries,
            cleanup_workspace_on_success=True,
            keep_workspace_on_failure=True,
            metadata={
                **dict(spec.metadata),
                "worker_contract": spec.protocol_version,
                "sandbox_runtime": spec.sandbox_runtime,
                "output_mode": spec.output_mode,
                "allowed_paths": list(spec.allowed_paths),
                "forbidden_paths": list(spec.forbidden_paths),
                "base_branch": spec.target_base_branch,
                "promotion_mode": "patch",
            },
        )
