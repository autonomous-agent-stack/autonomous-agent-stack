"""Manifest loader for agent configuration.

Scans agents/*/manifest.yaml and provides a unified registry.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml

from .contracts import StrictModel


class ManifestLoadError(Exception):
    """Error loading a manifest file."""

    def __init__(self, path: Path, message: str) -> None:
        self.path = path
        self.message = message
        super().__init__(f"Manifest load error at {path}: {message}")


class PermissionSpec(StrictModel):
    """Permission specification for an agent."""

    filesystem: dict[str, list[str]] = {}
    network: Literal["allow", "deny"] = "deny"
    git: dict[str, bool] = {}


class GateSpec(StrictModel):
    """Gate specification for an agent."""

    validators: list[str] = []
    approvals: dict[str, list[str]] = {}


class ExecutionSpec(StrictModel):
    """Execution specification for an agent."""

    default_driver: str = "claude_code"
    fallback_drivers: list[str] = []
    workspace_mode: Literal["isolated", "shared", "in_place"] = "isolated"
    allow_code_change: bool = False
    require_patch_gate: bool = True


class InputSpec(StrictModel):
    """Input specification for an agent."""

    required: list[str] = []
    optional: list[str] = []


class OutputSpec(StrictModel):
    """Output specification for an agent."""

    output_schema: dict[str, Any] = {}
    artifacts: list[str] = []


class RuntimeSpec(StrictModel):
    """Runtime specification for an agent."""

    deterministic_execution_required: bool = False
    llm_must_not_do_final_math: bool = False
    report_formats: list[str] = []


class PromptSpec(StrictModel):
    """Prompt paths for an agent."""

    intake: str | None = None
    translate_rules: str | None = None
    repair: str | None = None


class AgentManifest(StrictModel):
    """Manifest for an agent.

    This is the unified manifest format that all agents should use.
    It's compatible with the existing manifest.yaml format in agents/*/.
    """

    version: str = "1"

    # Agent identity
    id: str
    name: str = ""
    description: str = ""
    role: Literal["specialist", "planner", "executor", "reviewer", "orchestrator"] = "specialist"

    # Routing
    task_types: list[str] = []
    keywords: list[str] = []

    # Execution
    execution: ExecutionSpec = ExecutionSpec()

    # Inputs/outputs
    inputs: InputSpec = InputSpec()
    outputs: OutputSpec = OutputSpec()

    # Permissions
    permissions: PermissionSpec = PermissionSpec()

    # Gates
    gates: GateSpec = GateSpec()

    # Runtime
    runtime: RuntimeSpec = RuntimeSpec()

    # Prompts
    prompts: PromptSpec = PromptSpec()

    # Metadata
    metadata: dict[str, Any] = {}


class AgentRegistry:
    """Registry of agent manifests."""

    def __init__(self) -> None:
        self._agents: dict[str, AgentManifest] = {}
        self._task_type_index: dict[str, str] = {}  # task_type -> agent_id

    def register(self, manifest: AgentManifest) -> None:
        """Register an agent manifest."""
        if manifest.id in self._agents:
            raise ValueError(f"Agent with id '{manifest.id}' already registered")

        if not manifest.task_types:
            raise ValueError(f"Agent '{manifest.id}' must have at least one task_type")

        self._agents[manifest.id] = manifest

        for task_type in manifest.task_types:
            if task_type in self._task_type_index:
                raise ValueError(
                    f"Task type '{task_type}' already registered by "
                    f"'{self._task_type_index[task_type]}', cannot also register '{manifest.id}'"
                )
            self._task_type_index[task_type] = manifest.id

    def get(self, agent_id: str) -> AgentManifest | None:
        """Get an agent manifest by ID."""
        return self._agents.get(agent_id)

    def get_by_task_type(self, task_type: str) -> AgentManifest | None:
        """Get an agent manifest by task type."""
        agent_id = self._task_type_index.get(task_type)
        if agent_id is None:
            return None
        return self._agents.get(agent_id)

    def list(self) -> list[AgentManifest]:
        """List all registered agents."""
        return list(self._agents.values())

    def list_task_types(self) -> list[str]:
        """List all registered task types."""
        return list(self._task_type_index.keys())


def load_manifest(path: Path) -> AgentManifest:
    """Load a manifest from a YAML file."""
    if not path.exists():
        raise ManifestLoadError(path, "File not found")

    try:
        content = path.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ManifestLoadError(path, f"YAML parse error: {e}") from e

    if not isinstance(data, dict):
        raise ManifestLoadError(path, "Manifest must be a YAML mapping")

    # Extract agent section
    agent_data = data.get("agent", {})
    if not isinstance(agent_data, dict):
        raise ManifestLoadError(path, "Manifest must have an 'agent' section")

    # Flatten the structure for our model
    flat_data: dict[str, Any] = {
        "version": data.get("version", "1"),
        "id": agent_data.get("id", ""),
        "name": agent_data.get("name", ""),
        "description": agent_data.get("description", ""),
        "role": agent_data.get("role", "specialist"),
    }

    if not flat_data["id"]:
        raise ManifestLoadError(path, "Agent must have an 'id'")

    # Routing
    routing = data.get("routing", {})
    if isinstance(routing, dict):
        flat_data["task_types"] = routing.get("task_types", [])
        flat_data["keywords"] = routing.get("keywords", [])

    # Execution
    execution = data.get("execution", {})
    if isinstance(execution, dict):
        flat_data["execution"] = ExecutionSpec(
            default_driver=execution.get("default_driver", "claude_code"),
            fallback_drivers=execution.get("fallback_drivers", []),
            workspace_mode=execution.get("workspace_mode", "isolated"),
            allow_code_change=execution.get("allow_code_change", False),
            require_patch_gate=execution.get("require_patch_gate", True),
        )

    # Inputs
    inputs = data.get("inputs", {})
    if isinstance(inputs, dict):
        flat_data["inputs"] = InputSpec(
            required=inputs.get("required", []),
            optional=inputs.get("optional", []),
        )

    # Outputs
    outputs = data.get("outputs", {})
    if isinstance(outputs, dict):
        flat_data["outputs"] = OutputSpec(
            output_schema=outputs.get("schema", {}),
            artifacts=outputs.get("artifacts", []),
        )

    # Permissions
    permissions = data.get("permissions", {})
    if isinstance(permissions, dict):
        flat_data["permissions"] = PermissionSpec(
            filesystem=permissions.get("filesystem", {}),
            network=permissions.get("network", "deny"),
            git=permissions.get("git", {}),
        )

    # Gates
    gates = data.get("gates", {})
    if isinstance(gates, dict):
        flat_data["gates"] = GateSpec(
            validators=gates.get("validators", []),
            approvals=gates.get("approvals", {}),
        )

    # Runtime
    runtime = data.get("runtime", {})
    if isinstance(runtime, dict):
        flat_data["runtime"] = RuntimeSpec(
            deterministic_execution_required=runtime.get("deterministic_execution_required", False),
            llm_must_not_do_final_math=runtime.get("llm_must_not_do_final_math", False),
            report_formats=runtime.get("report_formats", []),
        )

    # Prompts
    prompts = data.get("prompts", {})
    if isinstance(prompts, dict):
        flat_data["prompts"] = PromptSpec(
            intake=prompts.get("intake"),
            translate_rules=prompts.get("translate_rules"),
            repair=prompts.get("repair"),
        )

    # Metadata
    flat_data["metadata"] = data.get("metadata", {})

    try:
        return AgentManifest.model_validate(flat_data)
    except Exception as e:
        raise ManifestLoadError(path, f"Validation error: {e}") from e


def scan_agents_directory(agents_dir: Path) -> AgentRegistry:
    """Scan an agents directory and return a registry of manifests."""
    registry = AgentRegistry()

    if not agents_dir.exists():
        return registry

    for agent_dir in agents_dir.iterdir():
        if not agent_dir.is_dir():
            continue

        manifest_path = agent_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue

        try:
            manifest = load_manifest(manifest_path)
            registry.register(manifest)
        except ManifestLoadError as e:
            # Re-raise with more context
            raise ManifestLoadError(e.path, f"Failed to load manifest: {e.message}") from e

    return registry
