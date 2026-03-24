"""LLM Message 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class Message(BaseModel):
    """消息模型 - 表示 LLM 对话中的单条消息"""

    id: str = Field(..., description="消息唯一标识符")
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="消息角色"
    )
    content: str = Field(..., description="消息内容")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="消息时间戳"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    tool_calls: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="工具调用信息"
    )
    token_count: Optional[int] = Field(
        default=None, description="消息 token 数量"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证消息 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("消息 ID 不能为空")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """验证消息内容"""
        if not v:
            raise ValueError("消息内容不能为空")
        if len(v) > 100000:
            raise ValueError("消息内容过长")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "msg_001",
                "role": "user",
                "content": "你好，请帮我写一段代码",
                "timestamp": "2024-01-01T00:00:00",
                "metadata": {"source": "web"},
                "tool_calls": None,
                "token_count": 42
            }
        }
