from __future__ import annotations

import asyncio

from src.orchestrator import PromptBuilder, create_graph_from_prompt


def test_prompt_builder_parses_structured_orchestration_plan() -> None:
    prompt = """
goal: 优化代码性能 50%
nodes: planner -> generator -> executor -> evaluator
retry: evaluator -> generator when decision == 'retry'
max_steps: 12
max_concurrency: 4
"""

    plan = PromptBuilder.build_orchestration_plan(prompt)

    assert plan.goal == "优化代码性能 50%"
    assert [step.node_id for step in plan.steps] == ["planner", "generator", "executor", "evaluator"]
    assert plan.max_steps == 12
    assert plan.max_concurrency == 4
    assert any(
        edge.source == "evaluator"
        and edge.target == "generator"
        and edge.condition == "decision == 'retry'"
        for edge in plan.edges
    )


def test_prompt_builder_parses_natural_language_retry() -> None:
    prompt = "请按 规划 -> 生成 -> 执行 -> 评估 流程编排，失败时重试。"
    plan = PromptBuilder.build_orchestration_plan(prompt, fallback_goal="自然语言编排")

    assert [step.node_id for step in plan.steps] == ["planner", "generator", "executor", "evaluator"]
    assert any(edge.source == "evaluator" and edge.target == "generator" for edge in plan.edges)


def test_graph_can_execute_from_prompt_plan() -> None:
    prompt = """
goal: 编写一个最小可运行示例
nodes: planner -> generator -> executor -> evaluator
retry: evaluator -> generator when decision == 'retry'
max_steps: 8
max_concurrency: 2
"""
    graph = create_graph_from_prompt(prompt, graph_id="test_prompt_graph")
    results = asyncio.run(graph.execute())

    assert set(results.keys()) == {"planner", "generator", "executor", "evaluator"}
    assert graph.context.get("goal") == "编写一个最小可运行示例"
    assert graph.context.get("orchestration_max_steps") == 8
    assert graph.context.get("orchestration_max_concurrency") == 2
