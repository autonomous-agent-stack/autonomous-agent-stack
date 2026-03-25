"""
MASFactory 集成模块

这个模块提供 MASFactory 图编排引擎的集成支持。
"""

from .graph_engine import (
    Node,
    Edge,
    Graph,
    ContextBlock,
    NodeType,
    NodeStatus,
    PlannerNode,
    GeneratorNode,
    ExecutorNode,
    EvaluatorNode,
    create_minimal_loop
)
from .mcp_context import MCPContextBlock, MCPToolRegistry, create_default_mcp_registry
from .node_protocol import NodeAdapter, NodeOutput, NodeRegistry
from .shortcircuit import (
    ComplexityClassifier,
    ExecutionPath,
    PathSelector,
    ShortcircuitExecutor,
    Task,
    TaskComplexity,
)
from .tool_synthesis import (
    SynthesizedTool,
    ToolSynthesisError,
    ToolSynthesisPolicy,
    ToolSynthesizer,
)

__all__ = [
    "Node",
    "Edge",
    "Graph",
    "ContextBlock",
    "NodeType",
    "NodeStatus",
    "PlannerNode",
    "GeneratorNode",
    "ExecutorNode",
    "EvaluatorNode",
    "create_minimal_loop",
    "NodeOutput",
    "NodeAdapter",
    "NodeRegistry",
    "MCPContextBlock",
    "MCPToolRegistry",
    "create_default_mcp_registry",
    "TaskComplexity",
    "ExecutionPath",
    "Task",
    "ComplexityClassifier",
    "PathSelector",
    "ShortcircuitExecutor",
    "ToolSynthesisError",
    "ToolSynthesisPolicy",
    "SynthesizedTool",
    "ToolSynthesizer",
]
