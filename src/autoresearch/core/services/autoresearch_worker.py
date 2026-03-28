from __future__ import annotations

import shlex

from autoresearch.agent_protocol.models import FallbackStep, JobSpec, ValidatorSpec
from autoresearch.shared.autoresearch_controlled_contract import (
    AutoResearchBackend,
    AutoResearchExecutionRequest,
)
from autoresearch.shared.autoresearch_worker_contract import AutoResearchWorkerJobSpec
from autoresearch.shared.models import GitPromotionMode


class AutoResearchWorkerService:
    """Translate a constrained analysis worker contract into AEP jobs and controlled requests."""

    def build_prompt(self, spec: AutoResearchWorkerJobSpec) -> str:
        allowed_paths = "\n".join(f"- {item}" for item in spec.allowed_paths)
        forbidden_paths = "\n".join(f"- {item}" for item in spec.forbidden_paths)
        deliverables = "\n".join(f"- {item}" for item in spec.deliverables)
        return (
            "You are AutoResearch operating as a constrained analysis-first worker.\n\n"
            "Task:\n"
            f"{spec.research_task}\n\n"
            "Hard rules:\n"
            "- Only produce artifacts and patch suggestions inside allowed_paths.\n"
            "- Never modify forbidden_paths.\n"
            "- Do not finalize promotion, commit, push, merge, or alter approval policy.\n"
            "- Produce concise execution_plan, test_plan, risk_summary, and patch_suggestion artifacts.\n"
            "- If you emit a patch candidate, it must stay inside allowed_paths and satisfy test_command.\n"
            "- Leave patch promotion and draft PR creation to the promotion gate.\n\n"
            "allowed_paths:\n"
            f"{allowed_paths}\n\n"
            "forbidden_paths:\n"
            f"{forbidden_paths}\n\n"
            "deliverables:\n"
            f"{deliverables}\n\n"
            "test_command:\n"
            f"- {spec.test_command}\n"
        )

    def build_agent_job_spec(self, spec: AutoResearchWorkerJobSpec) -> JobSpec:
        fallback: list[FallbackStep] = []
        retry_attempts = max(spec.max_iterations - 1, 0)
        if retry_attempts > 0:
            fallback.append(FallbackStep(action="retry", max_attempts=retry_attempts))
        fallback.append(FallbackStep(action="human_review", max_attempts=1))

        return JobSpec(
            run_id=spec.job_id,
            agent_id="autoresearch",
            role="analyst",
            mode="patch_only",
            task=self.build_prompt(spec),
            policy=spec.build_execution_policy(),
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
                "worker_output_mode": spec.worker_output_mode,
                "pipeline_target": spec.pipeline_target,
                "target_base_branch": spec.target_base_branch,
                "deliverables": list(spec.deliverables),
                "network_policy": spec.network_policy,
                "network_allowlist": list(spec.network_allowlist),
            },
        )

    def build_controlled_request(self, spec: AutoResearchWorkerJobSpec) -> AutoResearchExecutionRequest:
        return AutoResearchExecutionRequest(
            task_id=spec.job_id,
            prompt=self.build_prompt(spec),
            allowed_paths=list(spec.allowed_paths),
            forbidden_paths=list(spec.forbidden_paths),
            test_command=shlex.split(spec.test_command),
            deliverables=list(spec.deliverables),
            backend=AutoResearchBackend.MOCK,
            worker_output_mode=spec.worker_output_mode,
            pipeline_target=GitPromotionMode(spec.pipeline_target),
            max_iterations=spec.max_iterations,
            cleanup_workspace_on_success=True,
            keep_workspace_on_failure=True,
            metadata={
                **dict(spec.metadata),
                "worker_contract": spec.protocol_version,
                "allowed_paths": list(spec.allowed_paths),
                "forbidden_paths": list(spec.forbidden_paths),
                "base_branch": spec.target_base_branch,
                "deliverables": list(spec.deliverables),
                "network_policy": spec.network_policy,
                "network_allowlist": list(spec.network_allowlist),
            },
        )
