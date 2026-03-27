"""
多 Agent 协作模板
基于角色分工的多 Agent 协作系统
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum

class AgentRole(Enum):
    """Agent 角色枚举"""
    RESEARCHER = "researcher"      # 研究员
    WRITER = "writer"              # 作者
    REVIEWER = "reviewer"          # 审稿人
    COORDINATOR = "coordinator"    # 协调者

class Task(BaseModel):
    """任务定义"""
    id: str
    description: str
    assigned_to: AgentRole
    status: str = "pending"
    result: Optional[str] = None

class Message(BaseModel):
    """Agent 间消息"""
    from_role: AgentRole
    to_role: AgentRole
    content: str
    task_id: Optional[str] = None

class MultiAgentSystem:
    """多 Agent 协作系统"""
    
    def __init__(self, agents: Dict[AgentRole, 'BaseAgent']):
        """
        初始化多 Agent 系统
        
        Args:
            agents: 角色到 Agent 的映射
        """
        self.agents = agents
        self.tasks: Dict[str, Task] = {}
        self.messages: List[Message] = []
        self.coordinator = agents.get(AgentRole.COORDINATOR)
    
    def create_task(self, description: str, assigned_to: AgentRole) -> str:
        """
        创建任务
        
        Args:
            description: 任务描述
            assigned_to: 分配给的角色
        
        Returns:
            任务 ID
        """
        task_id = f"task_{len(self.tasks) + 1}"
        task = Task(
            id=task_id,
            description=description,
            assigned_to=assigned_to
        )
        self.tasks[task_id] = task
        return task_id
    
    def send_message(self, message: Message):
        """发送消息"""
        self.messages.append(message)
    
    def run_task(self, task_id: str) -> str:
        """
        运行任务
        
        Args:
            task_id: 任务 ID
        
        Returns:
            任务结果
        """
        task = self.tasks[task_id]
        agent = self.agents[task.assigned_to]
        
        # 执行任务
        result = agent.execute(task.description)
        
        # 更新任务状态
        task.status = "completed"
        task.result = result
        
        return result
    
    def run_workflow(self, initial_input: str) -> str:
        """
        运行工作流
        
        Args:
            initial_input: 初始输入
        
        Returns:
            最终输出
        """
        # 1. 协调者分析任务
        coordination = self.coordinator.execute(
            f"分析以下任务并分配给合适的角色: {initial_input}"
        )
        
        # 2. 创建任务
        # TODO: 解析 coordination 并创建任务
        
        # 3. 执行任务
        # TODO: 按依赖关系执行任务
        
        # 4. 整合结果
        # TODO: 整合所有任务结果
        
        return "Workflow completed"


class BaseAgent:
    """Agent 基类"""
    
    def __init__(self, role: AgentRole, model: str):
        """
        初始化 Agent
        
        Args:
            role: Agent 角色
            model: LLM 模型
        """
        self.role = role
        self.model = model
    
    def execute(self, task: str) -> str:
        """
        执行任务（需要子类实现）
        
        Args:
            task: 任务描述
        
        Returns:
            执行结果
        """
        raise NotImplementedError


class ResearcherAgent(BaseAgent):
    """研究员 Agent"""
    
    def execute(self, task: str) -> str:
        """执行研究任务"""
        # TODO: 实现研究逻辑
        return f"Research result for: {task}"


class WriterAgent(BaseAgent):
    """作者 Agent"""
    
    def execute(self, task: str) -> str:
        """执行写作任务"""
        # TODO: 实现写作逻辑
        return f"Written content for: {task}"


class ReviewerAgent(BaseAgent):
    """审稿人 Agent"""
    
    def execute(self, task: str) -> str:
        """执行审稿任务"""
        # TODO: 实现审稿逻辑
        return f"Review feedback for: {task}"


class CoordinatorAgent(BaseAgent):
    """协调者 Agent"""
    
    def execute(self, task: str) -> str:
        """执行协调任务"""
        # TODO: 实现协调逻辑
        return f"Coordination plan for: {task}"


# 使用示例
if __name__ == "__main__":
    agents = {
        AgentRole.RESEARCHER: ResearcherAgent(AgentRole.RESEARCHER, "gpt-4"),
        AgentRole.WRITER: WriterAgent(AgentRole.WRITER, "gpt-4"),
        AgentRole.REVIEWER: ReviewerAgent(AgentRole.REVIEWER, "gpt-4"),
        AgentRole.COORDINATOR: CoordinatorAgent(AgentRole.COORDINATOR, "gpt-4"),
    }
    
    system = MultiAgentSystem(agents)
    result = system.run_workflow("写一篇关于 AI Agent 的文章")
    print(result)
