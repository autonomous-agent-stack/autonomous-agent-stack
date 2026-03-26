from __future__ import annotations

import asyncio
from pathlib import Path

from masfactory import MASContext, build_minimal_masfactory_graph
from masfactory.nodes import ExecutorNode


def test_memory_search_finds_matching_notes(tmp_path: Path):
    (tmp_path / "memory").mkdir()
    note = tmp_path / "memory" / "note.md"
    note.write_text("This note mentions APFS quota and sandbox execution.", encoding="utf-8")

    context = MASContext(workspace=tmp_path, goal="APFS sandbox")
    hits = context.search_memory(["apfs", "sandbox"], max_results=3)

    assert hits
    assert hits[0]["path"] == str(note)


def test_executor_returns_sandbox_payload_when_docker_is_mocked(tmp_path: Path, monkeypatch):
    graph = build_minimal_masfactory_graph(goal="check cpu")
    graph.context.workspace = tmp_path
    graph.context.set("generated_code", "def solve_task():\n    return {'ok': True}\n")

    def fake_run(*args, **kwargs):
        class Result:
            returncode = 0
            stdout = '{"status":"success","result":{"ok":true},"cpu_count":8,"workspace":"/workspace"}\n'
            stderr = ""

        return Result()

    monkeypatch.setattr("masfactory.nodes.subprocess.run", fake_run)
    result = asyncio.run(ExecutorNode().execute(graph.context))

    assert result["status"] == "success"
    assert result["cpu_count"] == 8
    assert result["workspace"] == "/workspace"


def test_first_flight_graph_remains_four_nodes():
    graph = build_minimal_masfactory_graph(goal="inspect workspace")
    assert [node.node_id for node in graph.nodes] == ["planner", "generator", "executor", "evaluator"]

