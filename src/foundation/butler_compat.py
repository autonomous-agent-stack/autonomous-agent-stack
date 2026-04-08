"""Butler compatibility adapter for existing butler to foundation router.

This allows existing butler to leverage foundation routing
while preserving backward compatibility.
"""

from __future__ import annotations

from datetime import datetime

from .contracts import JobSpec, JobContext
from .manifest_loader import AgentManifest
from .router import Router, RoutingResult


class ButlerCompatAdapter:
    """Compatibility adapter for existing butler to use foundation router.

    This allows existing butler to leverage foundation routing
    while preserving backward compatibility.
    """

    def __init__(self, router: Router) -> None:
        self.router = router

    def route(
        self,
        task: str,
        task_type: str | None = None,
        attachments: list[str] | None = None,
        dry_run: bool = True,
    ) -> JobSpec | None:
        """Route a task using foundation router.

        This method can be called by existing butler to leverage
        foundation routing while maintaining backward compatibility.
        """
        result = self.router.route(task, task_type)
        if result is None:
            return None

        # Convert to JobSpec for compatibility with existing code
        job_spec = self._create_job_spec(
            result=result,
            task=task,
            task_type=task_type or result.task_type,
            attachments=attachments,
            dry_run=dry_run,
        )

        return job_spec

    def _create_job_spec(
        self,
        result: RoutingResult,
        task: str,
        task_type: str,
        attachments: list[str] | None = None,
        dry_run: bool = True,
    ) -> JobSpec:
        """Create a JobSpec from routing result."""
        manifest = result.manifest

        return JobSpec(
            run_id=f"run-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            agent_id=result.agent_id,
            task_type=task_type,
            role=manifest.role,
            task=task,
            attachments=attachments or [],
            context=JobContext(
                dry_run=dry_run,
                requires_approval=self._needs_approval(manifest),
            ),
        )

    def _needs_approval(self, manifest: AgentManifest) -> bool:
        """Check if approval is needed based on manifest."""
        gates = manifest.gates
        if not gates:
            return False
        approvals = gates.approvals or {}
        human_required = approvals.get("human_required_for", [])
        return len(human_required) > 0
