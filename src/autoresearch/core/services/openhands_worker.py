from __future__ import annotations

import shlex
import sys

from autoresearch.agent_protocol.models import ExecutionPolicy, FallbackStep, JobSpec, ValidatorSpec
from autoresearch.shared.models import GitPromotionMode
from autoresearch.shared.openhands_controlled_contract import (
    ControlledBackend,
    ControlledExecutionRequest,
    FailureStrategy,
)
from autoresearch.shared.openhands_worker_contract import OpenHandsWorkerJobSpec


class OpenHandsWorkerService:
    """Translate a patch-only OpenHands worker contract into existing AEP/backends."""

    DEFAULT_TIMEOUT_SEC = 420

    def _execution_test_command_parts(self, raw_command: str) -> list[str]:
        parts = shlex.split(raw_command)
        if not parts:
            return []
        if parts[0] == "pytest":
            return [sys.executable, "-m", "pytest", *parts[1:]]
        return parts

    def _execution_test_command(self, raw_command: str) -> str:
        return shlex.join(self._execution_test_command_parts(raw_command))

    def build_prompt(self, spec: OpenHandsWorkerJobSpec) -> str:
        allowed_paths = "\n".join(f"- {item}" for item in spec.allowed_paths)
        forbidden_paths = "\n".join(f"- {item}" for item in spec.forbidden_paths)
        test_command = self._execution_test_command(spec.test_command)
        return (
            "You are OpenHands operating as a constrained patch-only worker.\n\n"
            "Problem statement:\n"
            f"{spec.problem_statement}\n\n"
            "Hard rules:\n"
            "- Only modify files that match allowed_paths.\n"
            "- Never modify forbidden_paths.\n"
            "- The workspace is physically permission-scoped; out-of-scope writes will fail at the filesystem layer.\n"
            "- If an allowed business surface directory does not exist yet, you may create it inside allowed_paths.\n"
            "- Do not run git add, git commit, git push, git merge, git rebase, git reset, or git checkout.\n"
            "- Do not create product-facing entrypoints or change approval/promotion policy.\n"
            "- Produce the smallest patch that can satisfy the validation command.\n"
            "- Leave branch creation and draft PR creation to the promotion gate.\n\n"
            "allowed_paths:\n"
            f"{allowed_paths}\n\n"
            "forbidden_paths:\n"
            f"{forbidden_paths}\n\n"
            "test_command:\n"
            f"- {test_command}\n"
        )

    def build_agent_job_spec(self, spec: OpenHandsWorkerJobSpec) -> JobSpec:
        test_command = self._execution_test_command(spec.test_command)
        fallback: list[FallbackStep] = []
        retry_attempts = max(spec.max_iterations - 1, 0)
        if retry_attempts > 0:
            fallback.append(FallbackStep(action="retry", max_attempts=retry_attempts))
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
                timeout_sec=self.DEFAULT_TIMEOUT_SEC,
                allowed_paths=list(spec.allowed_paths),
                forbidden_paths=list(spec.forbidden_paths),
                cleanup_on_success=True,
                retain_workspace_on_failure=True,
            ),
            validators=[
                ValidatorSpec(
                    id="worker.test_command",
                    kind="command",
                    command=test_command,
                )
            ],
            fallback=fallback,
            metadata={
                **dict(spec.metadata),
                "worker_contract": spec.protocol_version,
                "sandbox_runtime": spec.sandbox_runtime,
                "worker_output_mode": spec.worker_output_mode,
                "pipeline_target": spec.pipeline_target,
                "target_base_branch": spec.target_base_branch,
            },
        )

    def build_controlled_request(self, spec: OpenHandsWorkerJobSpec) -> ControlledExecutionRequest:
        test_command = self._execution_test_command_parts(spec.test_command)
        fallback_backend = ControlledBackend.MOCK if spec.use_mock_fallback else None
        failure_strategy = FailureStrategy.FALLBACK if fallback_backend is not None else FailureStrategy.HUMAN_IN_LOOP
        return ControlledExecutionRequest(
            task_id=spec.job_id,
            prompt=self.build_prompt(spec),
            allowed_paths=list(spec.allowed_paths),
            forbidden_paths=list(spec.forbidden_paths),
            test_command=test_command,
            backend=ControlledBackend.OPENHANDS_CLI,
            fallback_backend=fallback_backend,
            worker_output_mode=spec.worker_output_mode,
            pipeline_target=GitPromotionMode(spec.pipeline_target),
            failure_strategy=failure_strategy,
            max_iterations=spec.max_iterations,
            cleanup_workspace_on_success=True,
            keep_workspace_on_failure=True,
            metadata={
                **dict(spec.metadata),
                "worker_contract": spec.protocol_version,
                "sandbox_runtime": spec.sandbox_runtime,
                "allowed_paths": list(spec.allowed_paths),
                "forbidden_paths": list(spec.forbidden_paths),
                "base_branch": spec.target_base_branch,
            },
        )
