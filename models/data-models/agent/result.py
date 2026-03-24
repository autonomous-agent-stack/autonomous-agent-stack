"""Agent Result 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class Result(BaseModel):
    """结果模型 - 表示 Agent 执行结果"""

    id: str = Field(..., description="结果唯一标识符")
    task_id: str = Field(..., description="关联任务 ID")
    plan_id: Optional[str] = Field(
        default=None, description="关联计划 ID"
    )
    success: bool = Field(..., description="是否成功")
    data: Optional[Any] = Field(default=None, description="结果数据")
    output: str = Field(default="", description="输出文本")
    error: Optional[str] = Field(default=None, description="错误信息")
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="更新时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    execution_time_ms: Optional[int] = Field(
        default=None, description="执行时间（毫秒）"
    )
    confidence: Optional[float] = Field(
        default=None, description="置信度 (0.0-1.0)"
    )
    tokens_used: Optional[int] = Field(
        default=None, description="使用的 token 数量"
    )
    tool_calls: List[Dict[str, Any]] = Field(
        default_factory=list, description="工具调用记录"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证结果 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("结果 ID 不能为空")
        return v.strip()

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, v: str) -> str:
        """验证任务 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("任务 ID 不能为空")
        return v.strip()

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: Optional[float]) -> Optional[float]:
        """验证置信度范围"""
        if v is not None:
            if not 0.0 <= v <= 1.0:
                raise ValueError("置信度必须在 0.0-1.0 之间")
        return v

    @field_validator("execution_time_ms")
    @classmethod
    def validate_execution_time_ms(cls, v: Optional[int]) -> Optional[int]:
        """验证执行时间"""
        if v is not None and v < 0:
            raise ValueError("执行时间不能为负数")
        return v

    @field_validator("tokens_used")
    @classmethod
    def validate_tokens_used(cls, v: Optional[int]) -> Optional[int]:
        """验证 token 数量"""
        if v is not None and v < 0:
            raise ValueError("token 数量不能为负数")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "success": self.success,
            "data": self.data,
            "output": self.output,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "confidence": self.confidence,
            "tokens_used": self.tokens_used
        }

    def get_summary(self) -> str:
        """获取结果摘要"""
        if self.success:
            summary = f"任务完成: {self.output[:200]}"
            if self.confidence:
                summary += f" (置信度: {self.confidence:.2%})"
        else:
            summary = f"任务失败: {self.error or '未知错误'}"
        return summary

    class Config:
        json_schema_extra = {
            "example": {
                "id": "result_001",
                "task_id": "task_001",
                "plan_id": "plan_001",
                "success": True,
                "data": {
                    "analysis": "正增长趋势",
                    "prediction": 100500
                },
                "output": "分析完成，预测下季度增长5%",
                "error": None,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "metadata": {},
                "execution_time_ms": 1500,
                "confidence": 0.95,
                "tokens_used": 2500,
                "tool_calls": [
                    {
                        "tool_id": "tool_001",
                        "action": "query_database",
                        "parameters": {"query": "SELECT * FROM sales"},
                        "execution_time_ms": 500
                    }
                ]
            }
        }
