"""Agent Plan 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class PlanStep(BaseModel):
    """计划步骤模型"""

    step_id: str = Field(..., description="步骤 ID")
    action: str = Field(..., description="动作描述")
    tool_id: Optional[str] = Field(default=None, description="使用的工具 ID")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="参数"
    )
    depends_on: List[str] = Field(
        default_factory=list, description="依赖的步骤 ID"
    )
    estimated_duration: Optional[int] = Field(
        default=None, description="预计耗时（秒）"
    )
    status: Literal["pending", "running", "completed", "failed", "skipped"] = Field(
        default="pending", description="步骤状态"
    )
    result: Optional[Any] = Field(default=None, description="执行结果")
    error: Optional[str] = Field(default=None, description="错误信息")


class Plan(BaseModel):
    """计划模型 - 表示 Agent 的执行计划"""

    id: str = Field(..., description="计划唯一标识符")
    task_id: str = Field(..., description="关联任务 ID")
    goal: str = Field(..., description="计划目标")
    steps: List[PlanStep] = Field(
        default_factory=list, description="计划步骤列表"
    )
    status: Literal["draft", "approved", "executing", "completed", "failed", "cancelled"] = Field(
        default="draft", description="计划状态"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="更新时间"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="开始执行时间"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="完成时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    reasoning: str = Field(default="", description="计划推理过程")
    estimated_duration: Optional[int] = Field(
        default=None, description="预计总耗时（秒）"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证计划 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("计划 ID 不能为空")
        return v.strip()

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """验证任务 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("任务 ID 不能为空")
        return v.strip()

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        """验证目标不为空"""
        if not v or not v.strip():
            raise ValueError("计划目标不能为空")
        if len(v) > 1000:
            raise ValueError("计划目标过长")
        return v.strip()

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, v: List[PlanStep]) -> List[PlanStep]:
        """验证步骤列表"""
        if not v:
            raise ValueError("计划必须包含至少一个步骤")
        return v

    @field_validator("estimated_duration")
    @classmethod
    def validate_estimated_duration(cls, v: Optional[int]) -> Optional[int]:
        """验证预计时长"""
        if v is not None and v <= 0:
            raise ValueError("预计时长必须大于 0")
        return v

    def get_progress(self) -> float:
        """计算计划进度"""
        if not self.steps:
            return 0.0
        completed = sum(1 for step in self.steps if step.status == "completed")
        return completed / len(self.steps)

    def get_pending_steps(self) -> List[PlanStep]:
        """获取待执行的步骤"""
        return [step for step in self.steps if step.status == "pending"]

    def get_executable_steps(self) -> List[PlanStep]:
        """获取可执行的步骤（依赖已满足）"""
        completed_steps = {step.step_id for step in self.steps if step.status == "completed"}
        pending_steps = self.get_pending_steps()

        executable = []
        for step in pending_steps:
            # 检查所有依赖是否已完成
            if all(dep in completed_steps for dep in step.depends_on):
                executable.append(step)

        return executable

    class Config:
        json_schema_extra = {
            "example": {
                "id": "plan_001",
                "task_id": "task_001",
                "goal": "完成数据分析和报告生成",
                "steps": [
                    {
                        "step_id": "step_001",
                        "action": "收集数据",
                        "tool_id": "tool_001",
                        "parameters": {"source": "database"},
                        "depends_on": [],
                        "estimated_duration": 30,
                        "status": "completed",
                        "result": {"count": 1000},
                        "error": None
                    },
                    {
                        "step_id": "step_002",
                        "action": "分析数据",
                        "tool_id": "tool_002",
                        "parameters": {"algorithm": "regression"},
                        "depends_on": ["step_001"],
                        "estimated_duration": 60,
                        "status": "pending",
                        "result": None,
                        "error": None
                    }
                ],
                "status": "executing",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "started_at": "2024-01-01T00:00:00",
                "completed_at": None,
                "metadata": {},
                "reasoning": "先收集数据，再进行分析",
                "estimated_duration": 90
            }
        }
