import re
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskComplexity(Enum):
    """任务复杂度枚举"""
    SIMPLE = "simple"  # 单步任务
    MEDIUM = "medium"  # 多步任务（2-5步）
    COMPLEX = "complex"  # 复杂任务（>5步）
    HIERARCHICAL = "hierarchical"  # 层级任务（需要子任务分解）


@dataclass
class SubTask:
    """子任务数据结构"""
    task_id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    assigned_agent: Optional[str] = None
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "assigned_agent": self.assigned_agent,
            "status": self.status,
            "result": self.result,
        }


class TaskDecomposer:
    """任务分解器
    
    遵循 OpenSage Decomposer 设计：
    1. 分析任务复杂度
    2. 分解为子任务
    3. 构建任务依赖图
    4. 分配给合适的 Agent
    """
    
    def __init__(self, llm_backend: Any = None):
        self.llm = llm_backend
        self._decomposition_strategies = {
            TaskComplexity.SIMPLE: self._decompose_simple,
            TaskComplexity.MEDIUM: self._decompose_medium,
            TaskComplexity.COMPLEX: self._decompose_complex,
            TaskComplexity.HIERARCHICAL: self._decompose_hierarchical,
        }
        
    async def analyze_complexity(self, task: str) -> TaskComplexity:
        """分析任务复杂度
        
        Args:
            task: 任务描述
            
        Returns:
            任务复杂度级别
        """
        normalized = task.strip()
        word_count = len(normalized.split())
        sentence_count = len([s for s in re.split(r"[。！？!?；;\n]+", normalized) if s.strip()])
        
        # 简单启发式规则
        
        # 检查关键词
        complex_keywords = ["然后", "之后", "同时", "最后", "先", "再", "and then", "after that", "finally"]
        hierarchical_keywords = ["分解", "拆分", "子任务", "decompose", "break down", "subtask"]
        
        lowered = normalized.lower()
        has_complex = any(kw in lowered for kw in complex_keywords) or sentence_count >= 2
        has_hierarchical = any(kw in lowered for kw in hierarchical_keywords)
        
        if has_hierarchical or word_count > 200:
            return TaskComplexity.HIERARCHICAL
        elif has_complex or word_count > 100 or sentence_count > 5:
            return TaskComplexity.COMPLEX
        elif word_count > 30 or sentence_count >= 2:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.SIMPLE
            
    async def decompose(
        self,
        task: str,
        max_depth: int = 3
    ) -> list[SubTask]:
        """分解任务为子任务
        
        Args:
            task: 任务描述
            max_depth: 最大分解深度
            
        Returns:
            子任务列表
        """
        complexity = await self.analyze_complexity(task)
        strategy = self._decomposition_strategies[complexity]
        
        return await strategy(task, max_depth)
        
    async def _decompose_simple(
        self,
        task: str,
        max_depth: int
    ) -> list[SubTask]:
        """简单任务：不需要分解"""
        return [
            SubTask(
                task_id="task_0",
                description=task,
                priority=0
            )
        ]
        
    async def _decompose_medium(
        self,
        task: str,
        max_depth: int
    ) -> list[SubTask]:
        """中等任务：分解为 2-5 个子任务"""
        candidates = await self._llm_decompose(task, max_items=5)
        if not candidates:
            candidates = self._split_into_steps(task, max_items=5)
        if not candidates:
            candidates = [task.strip()]

        subtasks: list[SubTask] = []
        for i, sentence in enumerate(candidates[:5]):
            subtasks.append(SubTask(
                task_id=f"task_{i}",
                description=sentence,
                dependencies=[f"task_{i-1}"] if i > 0 else [],
                priority=i
            ))
            
        return subtasks
        
    async def _decompose_complex(
        self,
        task: str,
        max_depth: int
    ) -> list[SubTask]:
        """复杂任务：分解为 >5 个子任务"""
        candidates = await self._llm_decompose(task, max_items=12)
        if not candidates:
            candidates = self._split_into_steps(task, max_items=12)
        if not candidates:
            candidates = [task.strip()]

        subtasks: list[SubTask] = []
        for task_id, sentence in enumerate(candidates):
            subtasks.append(SubTask(
                task_id=f"task_{task_id}",
                description=sentence,
                dependencies=[f"task_{task_id-1}"] if task_id > 0 else [],
                priority=task_id
            ))
        return subtasks
        
    async def _decompose_hierarchical(
        self,
        task: str,
        max_depth: int
    ) -> list[SubTask]:
        """层级任务：递归分解"""
        if max_depth <= 0:
            return await self._decompose_complex(task, max_depth)

        primary_blocks = await self._llm_decompose(task, max_items=6)
        if not primary_blocks:
            primary_blocks = self._split_primary_blocks(task, max_items=6)
        if not primary_blocks:
            primary_blocks = [task.strip()]

        subtasks: list[SubTask] = []
        for i, block in enumerate(primary_blocks):
            primary_task_id = f"task_{i}"
            if len(block) > 120 and max_depth > 1:
                secondary_tasks = await self._decompose_complex(block, max_depth - 1)
                if not secondary_tasks:
                    subtasks.append(
                        SubTask(
                            task_id=primary_task_id,
                            description=block,
                            dependencies=[f"task_{i-1}"] if i > 0 else [],
                            priority=len(subtasks),
                        )
                    )
                    continue
                for j, secondary in enumerate(secondary_tasks):
                    secondary.task_id = f"{primary_task_id}_{j}"
                    if j == 0:
                        secondary.dependencies = [f"task_{i-1}"] if i > 0 else []
                    else:
                        secondary.dependencies = [f"{primary_task_id}_{j-1}"]
                    secondary.priority = len(subtasks)
                    subtasks.append(secondary)
            else:
                subtasks.append(
                    SubTask(
                        task_id=primary_task_id,
                        description=block,
                        dependencies=[f"task_{i-1}"] if i > 0 else [],
                        priority=len(subtasks),
                    )
                )

        return subtasks
        
    def build_dependency_graph(self, subtasks: list[SubTask]) -> dict[str, list[str]]:
        """构建任务依赖图
        
        Args:
            subtasks: 子任务列表
            
        Returns:
            依赖图 {task_id: [dependency_ids]}
        """
        graph = {}
        
        for task in subtasks:
            graph[task.task_id] = task.dependencies
            
        return graph
        
    def get_execution_order(self, subtasks: list[SubTask]) -> list[str]:
        """获取任务执行顺序（拓扑排序）
        
        Args:
            subtasks: 子任务列表
            
        Returns:
            任务执行顺序
        """
        # 拓扑排序
        in_degree = {task.task_id: 0 for task in subtasks}
        graph = {task.task_id: [] for task in subtasks}
        
        for task in subtasks:
            for dep in task.dependencies:
                if dep in graph:
                    graph[dep].append(task.task_id)
                    in_degree[task.task_id] += 1
                    
        # BFS
        queue = [tid for tid, degree in in_degree.items() if degree == 0]
        order = []
        
        while queue:
            current = queue.pop(0)
            order.append(current)
            
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        return order

    async def _llm_decompose(self, task: str, max_items: int) -> list[str]:
        if self.llm is None or not hasattr(self.llm, "generate"):
            return []
        prompt = (
            "请将下面的任务分解成可执行步骤，返回 JSON 数组（每项是字符串），"
            f"最多 {max_items} 项，不要返回解释。\n\n任务：{task}"
        )
        try:
            response = await self.llm.generate(
                prompt,
                system="你是任务拆解器，只输出 JSON 数组。",
                temperature=0.1,
                max_tokens=800,
            )
        except Exception:
            return []

        json_match = re.search(r"\[[\s\S]*\]", str(response))
        if not json_match:
            return []
        try:
            data = json.loads(json_match.group(0))
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        steps = [str(item).strip() for item in data if str(item).strip()]
        return steps[:max_items]

    def _split_into_steps(self, task: str, max_items: int) -> list[str]:
        normalized = re.sub(r"\s+", " ", task.strip())
        if not normalized:
            return []

        chunks = re.split(r"[。！？!?；;\n]+", normalized)
        steps = [chunk.strip(" .,-") for chunk in chunks if chunk.strip(" .,-")]
        if len(steps) < 2:
            steps = [part.strip(" .,-") for part in re.split(r"\s+(?:然后|之后|并且|同时|再|finally|then|after)\s+", normalized, flags=re.IGNORECASE) if part.strip(" .,-")]
        if len(steps) < 2:
            steps = [normalized]
        return steps[:max_items]

    def _split_primary_blocks(self, task: str, max_items: int) -> list[str]:
        lines = [line.strip() for line in task.splitlines() if line.strip()]
        numbered = [line for line in lines if re.match(r"^(\d+[\.\)]|[-*])\s+", line)]
        if numbered:
            blocks = [re.sub(r"^(\d+[\.\)]|[-*])\s+", "", line).strip() for line in numbered]
            return [block for block in blocks if block][:max_items]
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n{2,}", task) if paragraph.strip()]
        if paragraphs:
            return paragraphs[:max_items]
        return self._split_into_steps(task, max_items=max_items)
