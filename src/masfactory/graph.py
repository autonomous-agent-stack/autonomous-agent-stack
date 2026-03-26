"""Minimal graph harness for the MASFactory skeleton."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from .context import MASContext
from .nodes import EvaluatorNode, ExecutorNode, GeneratorNode, MASNode, PlannerNode


@dataclass
class MASFactoryGraph:
    nodes: list[MASNode] = field(default_factory=list)
    context: MASContext = field(default_factory=MASContext)

    def add_node(self, node: MASNode) -> None:
        self.nodes.append(node)

    async def execute(self) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for node in self.nodes:
            if hasattr(node, "pre_execute"):
                prep = node.pre_execute(self.context)  # type: ignore[attr-defined]
                if prep is not None:
                    self.context.set(f"{node.node_id}_pre", prep)
            result = await node.execute(self.context)
            results[node.node_id] = result
        return results


def build_minimal_masfactory_graph(goal: str = "explore and learn") -> MASFactoryGraph:
    graph = MASFactoryGraph(context=MASContext(goal=goal))
    graph.add_node(PlannerNode())
    graph.add_node(GeneratorNode())
    graph.add_node(ExecutorNode())
    graph.add_node(EvaluatorNode())
    return graph


async def demo() -> dict[str, Any]:
    graph = build_minimal_masfactory_graph()
    return await graph.execute()


def main() -> None:
    results = asyncio.run(demo())
    for node_id, payload in results.items():
        print(f"{node_id}: {payload}")


if __name__ == "__main__":
    main()

