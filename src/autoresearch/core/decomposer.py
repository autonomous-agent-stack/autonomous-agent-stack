"""Task Decomposer - OpenSage 架构任务分解核心"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import re


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
    
    def __init__(self, llm_backend=None):
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
        task = task.strip()

        # 简单启发式规则
        word_count = len(task.split())
        sentence_count = len([
            part for part in re.split(r"[。！？.!?；;\n]+", task) if part.strip()
        ])
        
        # 检查关键词
        complex_keywords = ["然后", "之后", "同时", "最后", "先", "再", "and then", "after that", "finally"]
        hierarchical_keywords = ["分解", "拆分", "子任务", "decompose", "break down", "subtask"]
        
        has_complex = any(kw in task.lower() for kw in complex_keywords)
        has_hierarchical = any(kw in task.lower() for kw in hierarchical_keywords)
        
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
    ) -> List[SubTask]:
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
    ) -> List[SubTask]:
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
    ) -> List[SubTask]:
        """中等任务：分解为 2-5 个子任务"""
        # TODO: 使用 LLM 进行分解
        # 这里使用简单规则分解
        subtasks = []
        
        # 按句号分割
        sentences = [s.strip() for s in task.split("。") if s.strip()]
        
        for i, sentence in enumerate(sentences[:5]):
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
    ) -> List[SubTask]:
        """复杂任务：分解为 >5 个子任务"""
        # TODO: 使用 LLM 进行智能分解
        subtasks = []
        
        # 简单分解：按段落和句子
        paragraphs = task.split("\n\n")
        
        task_id = 0
        for para in paragraphs:
            sentences = [s.strip() for s in para.split("。") if s.strip()]
            
            for i, sentence in enumerate(sentences):
                subtasks.append(SubTask(
                    task_id=f"task_{task_id}",
                    description=sentence,
                    dependencies=[f"task_{task_id-1}"] if task_id > 0 else [],
                    priority=task_id
                ))
                task_id += 1
                
        return subtasks
        
    async def _decompose_hierarchical(
        self,
        task: str,
        max_depth: int
    ) -> List[SubTask]:
        """层级任务：递归分解"""
        if max_depth <= 0:
            return await self._decompose_complex(task, max_depth)
            
        # TODO: 使用 LLM 识别主要任务块
        # 然后递归分解每个任务块
        
        subtasks = []
        
        # 第一层分解
        primary_tasks = await self._decompose_complex(task, max_depth)
        
        for i, primary in enumerate(primary_tasks):
            # 递归分解
            if len(primary.description) > 100 and max_depth > 1:
                secondary_tasks = await self._decompose_hierarchical(
                    primary.description,
                    max_depth - 1
                )
                
                # 添加依赖关系
                for j, secondary in enumerate(secondary_tasks):
                    secondary.task_id = f"task_{i}_{j}"
                    secondary.dependencies = [f"task_{i}_{j-1}"] if j > 0 else [primary.task_id]
                    subtasks.append(secondary)
            else:
                subtasks.append(primary)
                
        return subtasks
        
    def build_dependency_graph(self, subtasks: List[SubTask]) -> Dict[str, List[str]]:
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
        
    def get_execution_order(self, subtasks: List[SubTask]) -> List[str]:
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
