from __future__ import annotations

import asyncio
from pathlib import Path

from masfactory import (
    EvaluatorNode,
    ExecutorNode,
    GeneratorNode,
    PlannerNode,
    build_minimal_masfactory_graph,
)


def test_graph_builds_four_nodes():
    graph = build_minimal_masfactory_graph(goal="hello world")
    assert [node.node_id for node in graph.nodes] == ["planner", "generator", "executor", "evaluator"]


def test_node_skeletons_execute_in_order(monkeypatch):
    graph = build_minimal_masfactory_graph(goal="validate skeleton")
    graph.context.workspace = Path.cwd()

    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = '{"status":"success","result":{"ok":true},"cpu_count":8,"workspace":"/workspace"}\n'
            stderr = ""

        return Result()

    import masfactory.nodes as mas_nodes

    monkeypatch.setattr(mas_nodes.subprocess, "run", fake_run)
    results = asyncio.run(graph.execute())

    assert "planner" in results
    assert "generator" in results
    assert "executor" in results
    assert "evaluator" in results
    assert results["planner"]["goal"] == "validate skeleton"
    assert results["evaluator"]["decision"] == "continue"


def test_node_types_are_explicit():
    assert PlannerNode().node_type == "planner"
    assert GeneratorNode().node_type == "generator"
    assert ExecutorNode().node_type == "executor"
    assert EvaluatorNode().node_type == "evaluator"
