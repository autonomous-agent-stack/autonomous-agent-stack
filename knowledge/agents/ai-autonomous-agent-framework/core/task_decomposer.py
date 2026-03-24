# knowledge/agents/ai-autonomous-agent-framework/core/task_decomposer.py

"""
任务分解器

将复杂目标分解为可执行的子任务序列
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """任务数据结构"""
    id: str
    description: str
    dependencies: List[str]
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "description": self.description,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "priority": self.priority,
            "metadata": self.metadata
        }


class TaskDecomposer:
    """
    任务分解器

    将复杂任务分解为可执行的子任务序列
    """

    def __init__(self, llm_client=None):
        """
        初始化任务分解器

        Args:
            llm_client: LLM 客户端，用于智能任务分解
        """
        self.llm_client = llm_client

    def decompose(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        max_depth: int = 3
    ) -> Task:
        """
        分解目标为任务树

        Args:
            goal: 用户目标
            context: 上下文信息
            max_depth: 最大分解深度

        Returns:
            根任务（包含子任务树）
        """
        context = context or {}

        # 使用 LLM 进行智能分解
        if self.llm_client:
            return self._llm_decompose(goal, context, max_depth)
        else:
            # 使用规则基分解
            return self._rule_based_decompose(goal, context)

    def _llm_decompose(
        self,
        goal: str,
        context: Dict[str, Any],
        max_depth: int
    ) -> Task:
        """使用 LLM 进行智能分解"""
        prompt = self._build_decomposition_prompt(goal, context)

        response = self.llm_client.generate(prompt)
        subtasks = self._parse_llm_response(response)

        root_task = Task(
            id="root",
            description=goal,
            dependencies=[],
            priority=0
        )

        # 递归分解子任务
        for subtask in subtasks:
            if max_depth > 0:
                child_task = self._llm_decompose(
                    subtask["description"],
                    {**context, "parent": goal},
                    max_depth - 1
                )
            else:
                child_task = Task(
                    id=subtask["id"],
                    description=subtask["description"],
                    dependencies=subtask.get("dependencies", []),
                    priority=subtask.get("priority", 0)
                )

            root_task.metadata.setdefault("subtasks", []).append(child_task)

        return root_task

    def _rule_based_decompose(
        self,
        goal: str,
        context: Dict[str, Any]
    ) -> Task:
        """规则基分解"""
        # 简单的关键词匹配规则
        subtasks = self._apply_decomposition_rules(goal)

        root_task = Task(
            id="root",
            description=goal,
            dependencies=[],
            priority=0
        )

        for i, subtask in enumerate(subtasks):
            child_task = Task(
                id=f"task_{i}",
                description=subtask,
                dependencies=[f"task_{i-1}"] if i > 0 else [],
                priority=i
            )
            root_task.metadata.setdefault("subtasks", []).append(child_task)

        return root_task

    def refine(
        self,
        task_tree: Task,
        feedback: str,
        memory: 'MemorySystem'
    ) -> Task:
        """
        根据反馈修正任务树

        Args:
            task_tree: 当前任务树
            feedback: 反馈信息
            memory: 记忆系统

        Returns:
            修正后的任务树
        """
        # 分析反馈
        failed_tasks = self._identify_failed_tasks(task_tree, memory)

        # 重新分解失败的任务
        for task_id in failed_tasks:
            task = self._find_task(task_tree, task_id)
            if task:
                # 添加新的子任务
                new_subtasks = self.decompose(
                    f"Fix: {task.description}",
                    context={"original_task": task.description}
                )

                # 更新任务树
                task.metadata["subtasks"] = new_subtasks.metadata.get("subtasks", [])

        return task_tree

    def _build_decomposition_prompt(
        self,
        goal: str,
        context: Dict[str, Any]
    ) -> str:
        """构建任务分解提示"""
        return f"""请将以下目标分解为可执行的子任务序列：

目标: {goal}

上下文: {context}

要求:
1. 将复杂任务分解为 3-5 个子任务
2. 识别任务之间的依赖关系
3. 每个任务应该可独立验证
4. 返回格式为 JSON 列表

返回格式:
[
  {{
    "id": "task_id",
    "description": "任务描述",
    "dependencies": ["依赖任务ID"],
    "priority": 优先级(0-10)
  }}
]
"""

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """解析 LLM 响应"""
        # 简化的解析逻辑
        try:
            return json.loads(response)
        except:
            return [{"id": "task_0", "description": response, "dependencies": [], "priority": 0}]

    def _apply_decomposition_rules(self, goal: str) -> List[str]:
        """应用分解规则"""
        rules = {
            "分析": ["收集数据", "预处理数据", "分析数据", "生成报告"],
            "开发": ["需求分析", "设计", "编码", "测试", "部署"],
            "研究": ["文献调研", "实验设计", "执行实验", "结果分析"],
            "自动化": ["识别流程", "编写脚本", "测试", "优化"],
            "生成": ["分析需求", "设计结构", "生成代码", "验证"],
        }

        for keyword, subtasks in rules.items():
            if keyword in goal:
                return subtasks

        # 默认分解
        return ["步骤 1", "步骤 2", "步骤 3"]

    def _identify_failed_tasks(
        self,
        task_tree: Task,
        memory: 'MemorySystem'
    ) -> List[str]:
        """识别失败的任务"""
        failed = []
        tasks = self._flatten_tasks(task_tree)

        for task in tasks:
            result = memory.retrieve(task.id)
            if result and result.get("status") == "failed":
                failed.append(task.id)

        return failed

    def _find_task(self, task_tree: Task, task_id: str) -> Optional[Task]:
        """在任务树中查找任务"""
        if task_tree.id == task_id:
            return task_tree

        subtasks = task_tree.metadata.get("subtasks", [])
        for subtask in subtasks:
            found = self._find_task(subtask, task_id)
            if found:
                return found

        return None

    def _flatten_tasks(self, task_tree: Task) -> List[Task]:
        """展平任务树为列表"""
        tasks = [task_tree]
        subtasks = task_tree.metadata.get("subtasks", [])
        for subtask in subtasks:
            tasks.extend(self._flatten_tasks(subtask))
        return tasks


if __name__ == "__main__":
    # 使用示例
    decomposer = TaskDecomposer()

    # 示例 1: 分析任务
    goal = "分析某公司的财务报告并生成投资建议"
    task_tree = decomposer.decompose(goal)
    print(f"分解任务: {task_tree.description}")
    for subtask in task_tree.metadata.get("subtasks", []):
        print(f"  - {subtask.description}")

    # 示例 2: 开发任务
    goal = "开发一个简单的 Web 应用"
    task_tree = decomposer.decompose(goal)
    print(f"\n分解任务: {task_tree.description}")
    for subtask in task_tree.metadata.get("subtasks", []):
        print(f"  - {subtask.description}")
