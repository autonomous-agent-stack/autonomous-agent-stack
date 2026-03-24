"""
自主 AI Agent 核心模块

提供任务分解、规划、执行、反思和记忆管理的核心组件。
"""

from .task_decomposer import TaskDecomposer, Task, TaskStatus
from .planning_engine import PlanningEngine, Plan
from .executor import Executor, ExecutionResult
from .reflection_module import ReflectionModule, Assessment
from .memory_system import MemorySystem, MemoryItem
from .autonomous_agent import AutonomousAgent, AgentState

__version__ = "1.0.0"
__all__ = [
    "TaskDecomposer",
    "Task",
    "TaskStatus",
    "PlanningEngine",
    "Plan",
    "Executor",
    "ExecutionResult",
    "ReflectionModule",
    "Assessment",
    "MemorySystem",
    "MemoryItem",
    "AutonomousAgent",
    "AgentState",
]
