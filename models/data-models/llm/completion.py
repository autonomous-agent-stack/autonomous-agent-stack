"""LLM Completion 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class Completion(BaseModel):
    """生成模型 - 表示 LLM 的生成结果"""

    id: str = Field(..., description="生成唯一标识符")
    prompt: str = Field(..., description="输入提示")
    completion: str = Field(..., description="生成内容")
    model: str = Field(..., description="使用的模型")
    finish_reason: Literal["stop", "length", "content_filter"] = Field(
        default="stop", description="结束原因"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    usage: Dict[str, int] = Field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        },
        description="token 使用情况"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    temperature: Optional[float] = Field(
        default=None, description="温度参数"
    )
    max_tokens: Optional[int] = Field(
        default=None, description="最大 token 数"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证生成 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("生成 ID 不能为空")
        return v.strip()

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, v: str) -> str:
        """验证提示不为空"""
        if not v or not v.strip():
            raise ValueError("提示不能为空")
        return v.strip()

    @field_validator("completion")
    @classmethod
    def validate_completion(cls, v: str) -> str:
        """验证生成内容不为空"""
        if not v:
            raise ValueError("生成内容不能为空")
        return v

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:
        """验证温度参数范围"""
        if v is not None:
            if not 0 <= v <= 2:
                raise ValueError("温度参数必须在 0-2 之间")
        return v

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: Optional[int]) -> Optional[int]:
        """验证最大 token 数"""
        if v is not None:
            if v <= 0:
                raise ValueError("最大 token 数必须大于 0")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "comp_001",
                "prompt": "写一个 Python 函数",
                "completion": "def hello():\n    return 'Hello World'",
                "model": "gpt-4",
                "finish_reason": "stop",
                "created_at": "2024-01-01T00:00:00",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                },
                "metadata": {},
                "temperature": 0.7,
                "max_tokens": 1000
            }
        }
