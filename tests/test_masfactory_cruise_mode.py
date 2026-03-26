from __future__ import annotations

import asyncio
import json
from pathlib import Path

from masfactory import MASContext, EvaluatorNode, PlannerNode
from masfactory.flight import FlightRecorder


def test_flight_recorder_writes_jsonl(tmp_path: Path):
    log_path = tmp_path / "flight.jsonl"
    recorder = FlightRecorder(enabled=True, path=log_path, echo=False)

    recorder.emit("planner", "start", summary="goal=test", goal="test")
    recorder.emit("planner", "done", summary="next_steps=4", next_steps=["a", "b"])

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["stage"] == "planner"
    assert first["event"] == "start"
    assert first["goal"] == "test"


def test_evaluator_provides_retry_hints_for_sandbox_errors():
    context = MASContext()
    context.set(
        "execution_result",
        {"status": "failed", "error": "[error] Docker daemon is not ready. Start Docker Desktop first."},
    )

    evaluation = asyncio.run(EvaluatorNode().execute(context))

    assert evaluation["failure_category"] == "sandbox_error"
    assert evaluation["retry_hints"]
    assert any("Docker" in hint for hint in evaluation["retry_hints"])


def test_planner_reuses_retry_hints_from_previous_evaluation():
    context = MASContext(goal="retry loop")
    context.save_memory(
        "last_evaluation",
        {
            "decision": "retry",
            "retry_hints": ["check Docker", "re-run ai-lab-check"],
        },
    )

    plan = asyncio.run(PlannerNode().execute(context))

    assert plan["retry_hints"] == ["check Docker", "re-run ai-lab-check"]

