# knowledge/agents/ai-autonomous-agent-framework/core/planning_engine.py

"""
规划引擎

生成最优的任务执行计划
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import json


@dataclass
class Plan:
    """执行计划"""
    tasks: List[Dict[str, Any]]
    constraints: Dict[str, Any]
    estimated_time: float
    estimated_cost: float

    def to_list(self) -> List[str]:
        """转换为任务描述列表"""
        return [task["description"] for task in self.tasks]


class PlanningEngine:
    """
    规划引擎

    生成最优的任务执行计划
    """

    def __init__(self, llm_client=None):
        """
        初始化规划引擎

        Args:
            llm_client: LLM 客户端，用于智能规划
        """
        self.llm_client = llm_client

    def generate_plan(
        self,
        task_tree,
        constraints: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """
        生成执行计划

        Args:
            task_tree: 任务树
            constraints: 约束条件

        Returns:
            执行计划
        """
        constraints = constraints or {}
        tasks = self._flatten_tasks(task_tree)

        # 使用 LLM 进行智能规划
        if self.llm_client:
            return self._llm_plan(tasks, constraints)
        else:
            # 使用启发式规划
            return self._heuristic_plan(tasks, constraints)

    def refine_plan(
        self,
        plan: Plan,
        feedback: str,
        memory: 'MemorySystem'
    ) -> Plan:
        """
        根据反馈修正计划

        Args:
            plan: 当前计划
            feedback: 反馈信息
            memory: 记忆系统

        Returns:
            修正后的计划
        """
        # 分析反馈，调整计划
        refined_tasks = []

        for task in plan.tasks:
            # 检查任务是否失败
            task_id = task["id"]
            result = memory.retrieve(task_id)

            if result and result.get("status") == "failed":
                # 重新规划失败的任务
                new_task = {
                    **task,
                    "description": f"Retry: {task['description']}",
                    "priority": task.get("priority", 0) + 10
                }
                refined_tasks.append(new_task)
            else:
                refined_tasks.append(task)

        # 重新排序任务
        refined_tasks.sort(key=lambda x: x.get("priority", 0), reverse=True)

        return Plan(
            tasks=refined_tasks,
            constraints=plan.constraints,
            estimated_time=plan.estimated_time * 1.2,
            estimated_cost=plan.estimated_cost * 1.2
        )

    def _llm_plan(
        self,
        tasks: List[Dict[str, Any]],
        constraints: Dict[str, Any]
    ) -> Plan:
        """使用 LLM 进行智能规划"""
        prompt = self._build_planning_prompt(tasks, constraints)

        response = self.llm_client.generate(prompt)
        planned_tasks = self._parse_llm_response(response)

        return Plan(
            tasks=planned_tasks,
            constraints=constraints,
            estimated_time=self._estimate_time(planned_tasks),
            estimated_cost=self._estimate_cost(planned_tasks)
        )

    def _heuristic_plan(
        self,
        tasks: List[Dict[str, Any]],
        constraints: Dict[str, Any]
    ) -> Plan:
        """启发式规划"""
        # 构建依赖图
        dependency_graph = self._build_dependency_graph(tasks)

        # 拓扑排序
        planned_order = self._topological_sort(dependency_graph)

        # 按优先级调整顺序
        planned_tasks = [self._find_task_by_id(tasks, task_id)
                        for task_id in planned_order]

        # 考虑约束（如时间限制、成本限制）
        if constraints.get("max_time"):
            planned_tasks = self._filter_by_time(planned_tasks, constraints["max_time"])

        return Plan(
            tasks=planned_tasks,
            constraints=constraints,
            estimated_time=self._estimate_time(planned_tasks),
            estimated_cost=self._estimate_cost(planned_tasks)
        )

    def _build_planning_prompt(
        self,
        tasks: List[Dict[str, Any]],
        constraints: Dict[str, Any]
    ) -> str:
        """构建规划提示"""
        return f"""请为以下任务生成最优执行计划：

任务列表:
{self._format_tasks(tasks)}

约束条件:
{self._format_constraints(constraints)}

要求:
1. 考虑任务依赖关系
2. 优化执行顺序
3. 在约束范围内最大化效率

返回格式:
[
  {{
    "id": "task_id",
    "description": "任务描述",
    "order": 执行顺序(整数),
    "priority": 优先级(0-10)
  }}
]
"""

    def _format_tasks(self, tasks: List[Dict[str, Any]]) -> str:
        """格式化任务列表"""
        return "\n".join([
            f"- {task['id']}: {task['description']} "
            f"(优先级: {task.get('priority', 0)})"
            for task in tasks
        ])

    def _format_constraints(self, constraints: Dict[str, Any]) -> str:
        """格式化约束条件"""
        return "\n".join([
            f"- {key}: {value}"
            for key, value in constraints.items()
        ])

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 响应"""
        try:
            return json.loads(response)
        except:
            return []

    def _flatten_tasks(self, task_tree) -> List[Dict[str, Any]]:
        """展平任务树"""
        tasks = [{
            "id": task_tree.id,
            "description": task_tree.description,
            "dependencies": task_tree.dependencies,
            "priority": task_tree.priority
        }]

        subtasks = task_tree.metadata.get("subtasks", [])
        for subtask in subtasks:
            tasks.extend(self._flatten_tasks(subtask))

        return tasks

    def _build_dependency_graph(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """构建依赖图"""
        graph = {task["id"]: [] for task in tasks}

        for task in tasks:
            for dep in task.get("dependencies", []):
                if dep in graph:
                    graph[dep].append(task["id"])

        return graph

    def _topological_sort(self, graph: Dict[str, List[str]]) -> List[str]:
        """拓扑排序"""
        in_degree = {node: 0 for node in graph}
        for node in graph:
            for neighbor in graph[node]:
                in_degree[neighbor] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    def _find_task_by_id(self, tasks: List[Dict[str, Any]], task_id: str) -> Dict[str, Any]:
        """根据 ID 查找任务"""
        for task in tasks:
            if task["id"] == task_id:
                return task
        return tasks[0] if tasks else {}

    def _filter_by_time(
        self,
        tasks: List[Dict[str, Any]],
        max_time: float
    ) -> List[Dict[str, Any]]:
        """根据时间限制过滤任务"""
        filtered = []
        total_time = 0

        for task in tasks:
            task_time = task.get("estimated_time", 1.0)
            if total_time + task_time <= max_time:
                filtered.append(task)
                total_time += task_time

        return filtered

    def _estimate_time(self, tasks: List[Dict[str, Any]]) -> float:
        """估计执行时间"""
        return sum(task.get("estimated_time", 1.0) for task in tasks)

    def _estimate_cost(self, tasks: List[Dict[str, Any]]) -> float:
        """估计执行成本"""
        return sum(task.get("estimated_cost", 10.0) for task in tasks)


if __name__ == "__main__":
    from task_decomposer import TaskDecomposer, Task

    planner = PlanningEngine()
    decomposer = TaskDecomposer()

    # 创建示例任务树
    root_task = Task(
        id="root",
        description="开发一个简单的 Web 应用",
        dependencies=[]
    )

    subtasks = [
        Task(id="task_1", description="需求分析", dependencies=[]),
        Task(id="task_2", description="设计", dependencies=["task_1"]),
        Task(id="task_3", description="编码", dependencies=["task_2"]),
        Task(id="task_4", description="测试", dependencies=["task_3"]),
    ]

    root_task.metadata = {"subtasks": subtasks}

    # 生成计划
    plan = planner.generate_plan(root_task)
    print("执行计划:")
    for i, task in enumerate(plan.tasks):
        print(f"{i+1}. {task['description']}")

    print(f"\n预估时间: {plan.estimated_time} 小时")
    print(f"预估成本: ${plan.estimated_cost}")
