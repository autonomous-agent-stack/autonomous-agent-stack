from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from masfactory import (
    EvaluatorNode,
    ExecutorNode,
    FlightRecorder,
    MASContext,
    GeneratorNode,
    PlannerNode,
)


RESET = "\033[0m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"


def color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{code}{text}{RESET}"


def env_flag(name: str, default: str = "0") -> bool:
    value = os.getenv(name, default).strip().lower()
    return value in {"1", "true", "yes", "on"}


async def main() -> int:
    watch_enabled = env_flag("WATCH") or env_flag("MAS_FACTORY_WATCH")
    watch_log = Path(
        os.getenv(
            "MAS_FACTORY_WATCH_LOG",
            str(REPO_ROOT / ".masfactory_runtime" / "masfactory-flight.jsonl"),
        )
    )
    recorder = FlightRecorder(enabled=watch_enabled, path=watch_log, echo=watch_enabled)

    context = MASContext(
        workspace=REPO_ROOT,
        goal=os.getenv("MAS_FACTORY_GOAL", "检查 M1 原生算力与工作区可写性"),
    )
    planner = PlannerNode()
    generator = GeneratorNode()
    executor = ExecutorNode()
    evaluator = EvaluatorNode()

    if watch_enabled:
        print(color(f"[WATCH] log -> {watch_log}", YELLOW))
        recorder.emit("flight", "start", summary=f"goal={context.goal}", goal=context.goal)

    print(color("[PLANNING]", CYAN), "->", end=" ")
    recorder.emit("planner", "start", summary=f"goal={context.goal}", goal=context.goal)
    plan = await planner.execute(context)
    recorder.emit(
        "planner",
        "done",
        summary=f"next_steps={len(plan.get('next_steps', []))}",
        goal=plan["goal"],
        next_steps=plan.get("next_steps", []),
        retry_hints=plan.get("retry_hints", []),
    )
    print(color("[GENERATING]", CYAN), "->", end=" ")

    generated = await generator.execute(context)
    memory_count = len(generated.get("memory_hits", []))
    recorder.emit(
        "generator",
        "done",
        summary=f"memory_hits={memory_count}",
        memory_hits=memory_count,
        goal=generated.get("goal"),
    )
    print(color(f"memory_hits={memory_count}", YELLOW), "->", end=" ")

    print(color("[EXECUTING]", CYAN), "->", end=" ")
    recorder.emit("executor", "start", summary="sandbox=ai_lab", sandbox="ai_lab")
    execution = await executor.execute(context)
    outcome = execution.get("status", "failed")
    if outcome == "success":
        print(color("[SUCCESS]", GREEN))
    else:
        print(color("[FAILED]", RED))
    recorder.emit(
        "executor",
        "done",
        summary=f"status={execution.get('status')}",
        status=execution.get("status"),
        failure_category=execution.get("failure_category"),
        error=execution.get("error"),
    )

    evaluation = await evaluator.execute(context)
    recorder.emit(
        "evaluator",
        "done",
        summary=f"decision={evaluation['decision']}",
        decision=evaluation["decision"],
        failure_category=evaluation.get("failure_category"),
        retry_hints=evaluation.get("retry_hints", []),
    )

    if watch_enabled and evaluation.get("retry_hints"):
        recorder.emit(
            "planner",
            "retry_hints",
            summary=f"hints={len(evaluation['retry_hints'])}",
            retry_hints=evaluation["retry_hints"],
            failure_category=evaluation.get("failure_category"),
        )

    print("=== MASFactory First Flight ===")
    print(f"goal: {plan['goal']}")
    print(f"decision: {evaluation['decision']}")
    print(f"cpu_count: {evaluation['resource_hints'].get('cpu_count')}")
    print(f"memory_limit_bytes: {evaluation['resource_hints'].get('memory_limit_bytes')}")
    if evaluation.get("retry_hints"):
        print("retry_hints:")
        for hint in evaluation["retry_hints"]:
            print(f"  - {hint}")
    if generated.get("memory_hits"):
        print("memory_hits:")
        for hit in generated["memory_hits"]:
            print(f"  - {hit['path']}")
    print(f"execution: {execution}")
    print(f"evaluation: {evaluation}")
    if watch_enabled:
        print(f"watch_log: {recorder.path}")

    recorder.emit("flight", "end", summary=f"decision={evaluation['decision']}", decision=evaluation["decision"])

    return 0 if evaluation["decision"] == "continue" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
