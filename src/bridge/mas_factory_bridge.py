"""MAS Factory Bridge - MAS Factory 桥接器

将底座的任务分发协议映射到 MAS Factory 的 AgentOrchestrator 接口
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


@dataclass
class AgentSpec:
    """Agent 规格"""
    agent_id: str
    name: str
    capabilities: List[str]
    max_concurrency: int = 3
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskSpec:
    """任务规格"""
    task_id: str
    description: str
    required_capabilities: List[str]
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    timeout: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchestrationResult:
    """编排结果"""
    task_id: str
    status: str  # success, failed, timeout
    agent_id: Optional[str] = None
    output: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class MASFactoryBridge:
    """MAS Factory 桥接器"""
    
    def __init__(self):
        self.agents: Dict[str, AgentSpec] = {}
        self.tasks: Dict[str, TaskSpec] = {}
        self.results: Dict[str, OrchestrationResult] = {}
        self._agent_executors: Dict[str, Callable] = {}
        
    async def register_agent(
        self,
        agent_spec: AgentSpec,
        executor: Optional[Callable] = None
    ):
        """注册 Agent
        
        Args:
            agent_spec: Agent 规格
            executor: 执行函数（可选）
        """
        logger.info(f"[MAS Bridge] 注册 Agent: {agent_spec.agent_id}")
        
        self.agents[agent_spec.agent_id] = agent_spec
        
        if executor:
            self._agent_executors[agent_spec.agent_id] = executor
            
    async def submit_task(self, task_spec: TaskSpec):
        """提交任务
        
        Args:
            task_spec: 任务规格
        """
        logger.info(f"[MAS Bridge] 提交任务: {task_spec.task_id}")
        
        self.tasks[task_spec.task_id] = task_spec
        
    async def orchestrate(
        self,
        task_id: str,
        strategy: str = "capability_match"
    ) -> OrchestrationResult:
        """编排任务
        
        Args:
            task_id: 任务 ID
            strategy: 编排策略（capability_match, round_robin, priority）
            
        Returns:
            编排结果
        """
        logger.info(f"[MAS Bridge] 编排任务: {task_id} (策略: {strategy})")
        
        task = self.tasks.get(task_id)
        if not task:
            return OrchestrationResult(
                task_id=task_id,
                status="failed",
                error="任务不存在"
            )
            
        # 检查依赖
        for dep_id in task.dependencies:
            if dep_id not in self.results or self.results[dep_id].status != "success":
                return OrchestrationResult(
                    task_id=task_id,
                    status="failed",
                    error=f"依赖未完成: {dep_id}"
                )
                
        # 选择 Agent
        agent = await self._select_agent(task, strategy)
        
        if not agent:
            return OrchestrationResult(
                task_id=task_id,
                status="failed",
                error="无可用 Agent"
            )
            
        # 执行任务
        start_time = datetime.now()
        
        try:
            executor = self._agent_executors.get(agent.agent_id)
            
            if executor:
                output = await asyncio.wait_for(
                    executor(task.description, task.metadata),
                    timeout=task.timeout
                )
                
                execution_time = (datetime.now() - start_time).total_seconds()
                
                result = OrchestrationResult(
                    task_id=task_id,
                    status="success",
                    agent_id=agent.agent_id,
                    output=output,
                    execution_time=execution_time
                )
                
                logger.info(f"[MAS Bridge] 任务执行成功: {task_id}")
                
            else:
                result = OrchestrationResult(
                    task_id=task_id,
                    status="failed",
                    agent_id=agent.agent_id,
                    error="Agent 无执行器"
                )
                
                logger.warning(f"[MAS Bridge] {result.error}")
                
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = OrchestrationResult(
                task_id=task_id,
                status="timeout",
                agent_id=agent.agent_id,
                error=f"执行超时 ({task.timeout}s)",
                execution_time=execution_time
            )
            
            logger.error(f"[MAS Bridge] {result.error}")
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = OrchestrationResult(
                task_id=task_id,
                status="failed",
                agent_id=agent.agent_id,
                error=str(e),
                execution_time=execution_time
            )
            
            logger.error(f"[MAS Bridge] 任务执行失败: {e}")
            
        # 保存结果
        self.results[task_id] = result
        
        return result
        
    async def _select_agent(
        self,
        task: TaskSpec,
        strategy: str
    ) -> Optional[AgentSpec]:
        """选择 Agent
        
        Args:
            task: 任务规格
            strategy: 选择策略
            
        Returns:
            选中的 Agent
        """
        if strategy == "capability_match":
            # 能力匹配
            for agent in self.agents.values():
                if all(
                    cap in agent.capabilities
                    for cap in task.required_capabilities
                ):
                    return agent
                    
        elif strategy == "round_robin":
            # 轮询
            for agent in self.agents.values():
                return agent
                
        elif strategy == "priority":
            # 优先级
            sorted_agents = sorted(
                self.agents.values(),
                key=lambda a: a.priority,
                reverse=True
            )
            return sorted_agents[0] if sorted_agents else None
            
        return None
        
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "agents": len(self.agents),
            "tasks": len(self.tasks),
            "results": len(self.results),
            "pending": len([t for t in self.tasks if t not in self.results]),
            "success": len([r for r in self.results.values() if r.status == "success"]),
            "failed": len([r for r in self.results.values() if r.status == "failed"])
        }


# 单例实例
_mas_bridge: Optional[MASFactoryBridge] = None


def get_mas_bridge() -> MASFactoryBridge:
    """获取 MAS 桥接器单例"""
    global _mas_bridge
    if _mas_bridge is None:
        _mas_bridge = MASFactoryBridge()
    return _mas_bridge
