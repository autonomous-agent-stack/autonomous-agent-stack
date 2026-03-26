from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class WorkflowNode(BaseModel):
    id: str
    type: str = "default"
    position: dict[str, float] = Field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    data: dict[str, Any] = Field(default_factory=dict)


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str | None = None


class WorkflowDefinition(BaseModel):
    workflow_id: str
    title: str = "Untitled Workflow"
    goal: str = "Execute agent workflow"
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowCompileResult(BaseModel):
    workflow_id: str
    prompt: str
    node_sequence: list[str] = Field(default_factory=list)
    retry_edges: list[dict[str, str]] = Field(default_factory=list)
    max_steps: int = 32
    max_concurrency: int = 3


class WorkflowStore:
    def __init__(self, base_dir: str | None = None) -> None:
        resolved = base_dir or os.getenv("BLITZ_WORKFLOW_DIR", "data/blitz_workflows")
        self.base_dir = Path(resolved)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, workflow_id: str) -> Path:
        safe = "".join(ch for ch in workflow_id if ch.isalnum() or ch in {"_", "-"})
        if not safe:
            safe = "default"
        return self.base_dir / f"{safe}.json"

    def get(self, workflow_id: str) -> WorkflowDefinition | None:
        path = self._path(workflow_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return WorkflowDefinition.model_validate(payload)

    def save(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        path = self._path(workflow.workflow_id)
        path.write_text(
            workflow.model_dump_json(indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return workflow

    def get_or_create_default(self, workflow_id: str) -> WorkflowDefinition:
        existing = self.get(workflow_id)
        if existing is not None:
            return existing

        default = WorkflowDefinition(
            workflow_id=workflow_id,
            title="Default Agent Flow",
            goal="Execute planner -> generator -> executor -> evaluator",
            nodes=[
                WorkflowNode(id="planner", type="planner", position={"x": 80, "y": 120}, data={"label": "planner"}),
                WorkflowNode(id="generator", type="generator", position={"x": 280, "y": 120}, data={"label": "generator"}),
                WorkflowNode(id="executor", type="executor", position={"x": 480, "y": 120}, data={"label": "executor"}),
                WorkflowNode(id="evaluator", type="evaluator", position={"x": 680, "y": 120}, data={"label": "evaluator"}),
            ],
            edges=[
                WorkflowEdge(id="planner-generator", source="planner", target="generator"),
                WorkflowEdge(id="generator-executor", source="generator", target="executor"),
                WorkflowEdge(id="executor-evaluator", source="executor", target="evaluator"),
                WorkflowEdge(id="retry-evaluator-generator", source="evaluator", target="generator", label="retry"),
            ],
            metadata={"max_steps": 24, "max_concurrency": 3},
        )
        return self.save(default)

    def compile(self, workflow: WorkflowDefinition) -> WorkflowCompileResult:
        if not workflow.nodes:
            raise ValueError("workflow must contain at least one node")

        # Stable sequence by canvas x/y so drag layout controls execution order.
        sorted_nodes = sorted(
            workflow.nodes,
            key=lambda n: (float(n.position.get("x", 0.0)), float(n.position.get("y", 0.0)), n.id),
        )
        node_sequence = [self._normalize_node_label(node) for node in sorted_nodes]

        retry_edges: list[dict[str, str]] = []
        for edge in workflow.edges:
            label = (edge.label or "").strip().lower()
            if "retry" in label or label == "r":
                retry_edges.append(
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "condition": "decision == 'retry'",
                    }
                )

        max_steps = int(workflow.metadata.get("max_steps", 32))
        max_concurrency = int(workflow.metadata.get("max_concurrency", 3))

        lines = [
            f"goal: {workflow.goal}",
            f"nodes: {' -> '.join(node_sequence)}",
            f"max_steps: {max(1, min(max_steps, 256))}",
            f"max_concurrency: {max(1, min(max_concurrency, 32))}",
        ]
        if retry_edges:
            retry = retry_edges[0]
            lines.append(
                f"retry: {retry['source']} -> {retry['target']} when {retry['condition']}"
            )

        return WorkflowCompileResult(
            workflow_id=workflow.workflow_id,
            prompt="\n".join(lines),
            node_sequence=node_sequence,
            retry_edges=retry_edges,
            max_steps=max(1, min(max_steps, 256)),
            max_concurrency=max(1, min(max_concurrency, 32)),
        )

    @staticmethod
    def _normalize_node_label(node: WorkflowNode) -> str:
        label = str(node.data.get("label") or node.type or node.id).strip().lower()
        aliases = {
            "plan": "planner",
            "planning": "planner",
            "generate": "generator",
            "execution": "executor",
            "evaluate": "evaluator",
        }
        return aliases.get(label, label)
