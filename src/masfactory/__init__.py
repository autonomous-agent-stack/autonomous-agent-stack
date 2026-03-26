"""MASFactory node skeletons for the autonomous-agent-stack workspace.

This package keeps the four core roles explicit:
Planner -> Generator -> Executor -> Evaluator
"""

from .context import MASContext
from .flight import FlightRecorder
from .graph import MASFactoryGraph, build_minimal_masfactory_graph
from .nodes import EvaluatorNode, ExecutorNode, GeneratorNode, PlannerNode

__all__ = [
    "MASContext",
    "FlightRecorder",
    "MASFactoryGraph",
    "build_minimal_masfactory_graph",
    "PlannerNode",
    "GeneratorNode",
    "ExecutorNode",
    "EvaluatorNode",
]
