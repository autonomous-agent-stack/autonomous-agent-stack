from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from orchestrator.graph_engine import ContextBlock, Edge, Graph, Node, NodeStatus, NodeType
from orchestrator.node_protocol import NodeOutput, NodeStatus as ProtocolNodeStatus
from orchestrator.shortcircuit import ComplexityClassifier, ExecutionPath, PathSelector, TaskComplexity


@dataclass
class _RecorderNode(Node):
    async def execute(self, context: ContextBlock) -> dict[str, object]:
        self.status = NodeStatus.RUNNING
        order = list(context.get("order", []))
        order.append(self.node_id)
        context.set("order", order)
        self.status = NodeStatus.COMPLETED
        self.outputs = {"node_id": self.node_id}
        return self.outputs


@dataclass
class _DecisionNode(Node):
    async def execute(self, context: ContextBlock) -> dict[str, object]:
        self.status = NodeStatus.RUNNING
        count = int(context.get("decision_count", 0)) + 1
        context.set("decision_count", count)
        context.set("decision", "retry" if count == 1 else "continue")
        self.status = NodeStatus.COMPLETED
        self.outputs = {"decision": context.get("decision")}
        return self.outputs


@dataclass
class _SleepNode(Node):
    delay: float = 0.2

    async def execute(self, context: ContextBlock) -> dict[str, object]:
        self.status = NodeStatus.RUNNING
        starts = dict(context.get("starts", {}))
        starts[self.node_id] = time.monotonic()
        context.set("starts", starts)
        await asyncio.sleep(self.delay)
        self.status = NodeStatus.COMPLETED
        self.outputs = {"node_id": self.node_id}
        return self.outputs


def test_edge_condition_expression_evaluation() -> None:
    context = ContextBlock()
    context.set("decision", "retry")
    assert Edge(source="a", target="b", condition="decision == 'retry'").evaluate(context) is True
    assert Edge(source="a", target="b", condition="decision != 'retry'").evaluate(context) is False


def test_graph_execute_follows_edge_conditions_and_loops() -> None:
    graph = Graph("conditional_loop")
    graph.add_node(_RecorderNode(node_id="generator", node_type=NodeType.GENERATOR))
    graph.add_node(_DecisionNode(node_id="evaluator", node_type=NodeType.EVALUATOR))
    graph.add_edge("generator", "evaluator")
    graph.add_edge("evaluator", "generator", condition="decision == 'retry'")

    asyncio.run(graph.execute(max_steps=6))
    order = graph.context.get("order", [])
    assert order == ["generator", "generator"]
    assert graph.context.get("decision_count") == 2
    assert graph.context.get("decision") == "continue"


def test_graph_execute_runs_same_layer_nodes_concurrently() -> None:
    graph = Graph("parallel_layer", max_concurrency=2)
    graph.add_node(_RecorderNode(node_id="planner", node_type=NodeType.PLANNER))
    graph.add_node(_SleepNode(node_id="generator_a", node_type=NodeType.GENERATOR, delay=0.2))
    graph.add_node(_SleepNode(node_id="generator_b", node_type=NodeType.GENERATOR, delay=0.2))
    graph.add_edge("planner", "generator_a")
    graph.add_edge("planner", "generator_b")

    started_at = time.monotonic()
    asyncio.run(graph.execute(max_steps=4, max_concurrency=2))
    elapsed = time.monotonic() - started_at

    starts = graph.context.get("starts", {})
    assert set(starts.keys()) == {"generator_a", "generator_b"}
    assert abs(starts["generator_a"] - starts["generator_b"]) < 0.1
    assert elapsed < 0.35


def test_shortcircuit_path_selection() -> None:
    classifier = ComplexityClassifier()
    selector = PathSelector()

    trivial_task = classifier.classify("rename 3 files")
    complex_task = classifier.classify("design multi-agent collaboration workflow")

    assert trivial_task.complexity is TaskComplexity.TRIVIAL
    assert selector.select_path(trivial_task) is ExecutionPath.DIRECT
    assert complex_task.complexity is TaskComplexity.COMPLEX
    assert selector.select_path(complex_task) is ExecutionPath.REFLECTION


def test_node_output_roundtrip() -> None:
    output = NodeOutput(
        status=ProtocolNodeStatus.SUCCESS,
        data={"value": 1},
        metadata={"latency_ms": 12},
    )
    restored = NodeOutput.from_dict(output.to_dict())
    assert restored.status is ProtocolNodeStatus.SUCCESS
    assert restored.data == {"value": 1}
    assert restored.metadata == {"latency_ms": 12}
