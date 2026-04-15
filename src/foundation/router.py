"""Router for unified task routing.

This module provides a unified router that can route tasks to the appropriate
agent based on manifest registry and task type.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .contracts import JobSpec, JobContext
from .manifest_loader import AgentManifest, scan_agents_directory


@dataclass
class RoutingResult:
    """Result of routing a task to an agent."""

    agent_id: str
    task_type: str
    manifest: AgentManifest
    confidence: float = 1.0
    reason: str = ""


class Router:
    """Unified router for task routing.

    Routes tasks to appropriate agents based on manifest registry
    and task type.
    """

    def __init__(self, agents_dir: str = "agents") -> None:
        self.agents_dir = agents_dir
        self._manifests: dict[str, AgentManifest] = {}
        self._by_task_type: dict[str, AgentManifest] = {}
        self._by_id: dict[str, AgentManifest] = {}
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the router by loading manifests."""
        self._manifests = {}
        self._by_task_type = {}
        self._by_id = {}
        self._initialized = False

        registry = scan_agents_directory(Path(self.agents_dir))
        for manifest in registry.list():
            manifest_id = manifest.id
            if manifest_id in self._manifests:
                raise ValueError(f"Duplicate agent id: {manifest_id}")
            self._manifests[manifest_id] = manifest
            self._by_id[manifest_id] = manifest

            for task_type in manifest.task_types:
                if task_type in self._by_task_type:
                    raise ValueError(f"Duplicate task_type: {task_type}")
                self._by_task_type[task_type] = manifest

        self._initialized = True

    def is_initialized(self) -> bool:
        """Check if the router is initialized."""
        return self._initialized

    def get_agent(self, agent_id: str) -> AgentManifest | None:
        """Get an agent by ID."""
        return self._by_id.get(agent_id)

    def get_agent_for_task_type(self, task_type: str) -> AgentManifest | None:
        """Get the agent that handles a task type."""
        return self._by_task_type.get(task_type)

    def list_agents(self) -> list[AgentManifest]:
        """List all registered agents."""
        return list(self._manifests.values())

    def list_task_types(self) -> list[str]:
        """List all registered task types."""
        return list(self._by_task_type.keys())

    def route(self, task_brief: str, task_type: str | None = None) -> RoutingResult | None:
        """Route a task to an agent.

        Args:
            task_brief: The task brief/description
            task_type: Optional task type hint (e.g., "excel_audit", "github_admin")

        Returns:
            RoutingResult with the selected agent or None if no match.
        """
        if not self._initialized:
            self.initialize()

        # Try to match by task_type first
        if task_type:
            manifest = self._by_task_type.get(task_type)
            if manifest:
                return RoutingResult(
                    agent_id=manifest.id,
                    task_type=task_type,
                    manifest=manifest,
                    confidence=1.0,
                    reason="matched by task_type",
                )

        # Try to match by keywords in task_brief
        task_brief_lower = task_brief.lower()
        for manifest in self._manifests.values():
            for keyword in manifest.keywords:
                if keyword in task_brief_lower:
                    return RoutingResult(
                        agent_id=manifest.id,
                        task_type=manifest.task_types[0] if manifest.task_types else task_type or "",
                        manifest=manifest,
                        confidence=0.8,
                        reason=f"matched by keyword: {keyword}",
                    )

        return None

    def route_to_job_spec(
        self,
        task: str,
        task_type: str | None = None,
        attachments: list[str] | None = None,
        dry_run: bool = True,
        requires_approval: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> JobSpec:
        """Route a task to a JobSpec.

        This method converts a high-level task request into a properly
        structured JobSpec that can be executed by the framework.

        Args:
            task: The task description
            task_type: Optional task type (e.g., "excel_audit", "github_admin.transfer_plan")
            attachments: Optional list of attachment paths/URLs
            dry_run: Whether this is a dry-run (default: True)
            requires_approval: Whether human approval is required (default: False)
            metadata: Optional metadata

        Returns:
            JobSpec ready for execution
        """
        # Route the task
        routing_result = self.route(task, task_type)
        if routing_result is None:
            raise ValueError(f"No agent found for task: {task_type or task}")

        manifest = routing_result.manifest

        # Build JobContext from manifest
        context = JobContext(
            dry_run=dry_run,
            requires_approval=requires_approval,
            timeout_seconds=900 if manifest.execution.workspace_mode == "isolated" else 300,
            allow_code_change=manifest.execution.allow_code_change,
            metadata={
                "agent_name": manifest.name,
                "agent_description": manifest.description,
                **(metadata or {}),
            },
        )

        # Build JobSpec
        job_spec = JobSpec(
            run_id=f"run-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            agent_id=manifest.id,
            task_type=task_type or routing_result.task_type,
            role=manifest.role,
            task=task,
            attachments=attachments or [],
            context=context,
            metadata=metadata or {},
        )

        return job_spec
