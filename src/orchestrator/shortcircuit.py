"""
短路执行机制：
根据任务复杂度在 DIRECT / LINEAR / REFLECTION 三条路径之间切换。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Callable

from .graph_engine import create_minimal_loop


class TaskComplexity(str, Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class ExecutionPath(str, Enum):
    DIRECT = "direct"
    LINEAR = "linear"
    REFLECTION = "reflection"


@dataclass
class Task:
    description: str
    complexity: TaskComplexity
    estimated_steps: int
    requires_reflection: bool
    tools_needed: list[str]


class ComplexityClassifier:
    """规则优先的轻量任务复杂度分类器。"""

    RULES: list[tuple[str, TaskComplexity]] = [
        (r"^(rename|move|copy|delete)\s+\d+\s+files?$", TaskComplexity.TRIVIAL),
        (r"^read\s+.+\.(json|yaml|toml)$", TaskComplexity.TRIVIAL),
        (r"^list\s+(directory|files|processes)$", TaskComplexity.TRIVIAL),
        (r"^batch\s+(rename|convert|process)", TaskComplexity.SIMPLE),
        (r"^install\s+\w+\s+packages?$", TaskComplexity.SIMPLE),
        (r"^(refactor|optimize|redesign)\s+.+", TaskComplexity.MODERATE),
        (r"^integrate\s+.+\s+with\s+.+", TaskComplexity.MODERATE),
        (r"^(design|architect|evolve)\s+.+", TaskComplexity.COMPLEX),
        (r"^multi-agent\s+collaboration", TaskComplexity.COMPLEX),
    ]

    def classify(self, task_description: str) -> Task:
        for pattern, complexity in self.RULES:
            if re.match(pattern, task_description, re.IGNORECASE):
                return self._create_task(task_description, complexity)
        return self._create_task(task_description, TaskComplexity.MODERATE)

    def _create_task(self, description: str, complexity: TaskComplexity) -> Task:
        tool_keywords = {
            "git": "git",
            "api": "http",
            "docker": "docker",
            "sql": "sqlite",
            "test": "pytest",
        }
        tools_needed = [tool for keyword, tool in tool_keywords.items() if keyword in description.lower()]
        steps_map = {
            TaskComplexity.TRIVIAL: 1,
            TaskComplexity.SIMPLE: 3,
            TaskComplexity.MODERATE: 6,
            TaskComplexity.COMPLEX: 10,
        }
        return Task(
            description=description,
            complexity=complexity,
            estimated_steps=steps_map[complexity],
            requires_reflection=complexity in {TaskComplexity.MODERATE, TaskComplexity.COMPLEX},
            tools_needed=tools_needed,
        )


class PathSelector:
    PATH_MAP = {
        TaskComplexity.TRIVIAL: ExecutionPath.DIRECT,
        TaskComplexity.SIMPLE: ExecutionPath.LINEAR,
        TaskComplexity.MODERATE: ExecutionPath.REFLECTION,
        TaskComplexity.COMPLEX: ExecutionPath.REFLECTION,
    }

    def select_path(self, task: Task) -> ExecutionPath:
        return self.PATH_MAP[task.complexity]


class ShortcircuitExecutor:
    """短路入口：TRIVIAL/SIMPLE 任务避免强制全链路反思。"""

    def __init__(
        self,
        classifier: ComplexityClassifier | None = None,
        path_selector: PathSelector | None = None,
    ) -> None:
        self.classifier = classifier or ComplexityClassifier()
        self.path_selector = path_selector or PathSelector()

    async def execute(
        self,
        task_description: str,
        direct_handler: Callable[[Task], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        task = self.classifier.classify(task_description)
        path = self.path_selector.select_path(task)

        if path is ExecutionPath.DIRECT:
            if direct_handler is not None:
                result = direct_handler(task)
            else:
                result = {
                    "status": "success",
                    "summary": "direct path completed without reflection",
                    "task": task.description,
                }
            return {
                "path": path.value,
                "task": task,
                "result": result,
            }

        graph = create_minimal_loop()
        graph.context.set("goal", task.description)
        graph.context.set("task_complexity", task.complexity.value)
        graph.context.set("execution_path", path.value)

        results = await graph.execute(max_steps=16)
        return {
            "path": path.value,
            "task": task,
            "result": results,
        }
