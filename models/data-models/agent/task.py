"""Agent Task 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class Task(BaseModel):
    """任务模型 - 表示 Agent 的任务"""

    id: str = Field(..., description="任务唯一标识符")
    title: str = Field(..., description="任务标题")
    description: str = Field(..., description="任务描述")
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = Field(
        default="pending", description="任务状态"
    )
    priority: Literal["low", "medium", "high", "critical"] = Field(
        default="medium", description="任务优先级"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="更新时间"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="开始时间"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="完成时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    parent_task_id: Optional[str] = Field(
        default=None, description="父任务 ID"
    )
    subtasks: List[str] = Field(
        default_factory=list, description="子任务 ID 列表"
    )
    progress: float = Field(default=0.0, description="进度 (0.0-1.0)")
    error_message: Optional[str] = Field(
        default=None, description="错误信息"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证任务 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("任务 ID 不能为空")
        return v.strip()

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """验证标题不为空"""
        if not v or not v.strip():
            raise ValueError("任务标题不能为空")
        if len(v) > 200:
            raise ValueError("任务标题过长")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """验证描述不为空"""
        if not v:
            raise ValueError("任务描述不能为空")
        if len(v) > 5000:
            raise ValueError("任务描述过长")
        return v

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v: float) -> float:
        """验证进度范围"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("进度必须在 0.0-1.0 之间")
        return v

    def update_progress(self, progress: float) -> None:
        """更新任务进度"""
        self.progress = max(0.0, min(1.0, progress))
        self.updated_at = datetime.now()

    def mark_completed(self) -> None:
        """标记任务为完成"""
        self.status = "completed"
        self.progress = 1.0
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_failed(self, error: str) -> None:
        """标记任务为失败"""
        self.status = "failed"
        self.error_message = error
        self.updated_at = datetime.now()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "task_001",
                "title": "数据预处理",
                "description": "对原始数据进行清洗和格式化",
                "status": "running",
                "priority": "high",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "started_at": "2024-01-01T00:00:00",
                "completed_at": None,
                "metadata": {},
                "parent_task_id": None,
                "subtasks": [],
                "progress": 0.5,
                "error_message": None
            }
        }
