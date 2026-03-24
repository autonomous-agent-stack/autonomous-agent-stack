"""LLM Conversation 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from .message import Message


class Conversation(BaseModel):
    """对话模型 - 表示完整的 LLM 对话"""

    id: str = Field(..., description="对话唯一标识符")
    messages: List[Message] = Field(
        default_factory=list, description="消息列表"
    )
    title: Optional[str] = Field(
        default=None, description="对话标题"
    )
    model_name: str = Field(..., description="使用的模型名称")
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="更新时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    total_tokens: int = Field(default=0, description="总 token 数量")
    is_active: bool = Field(default=True, description="是否活跃")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证对话 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("对话 ID 不能为空")
        return v.strip()

    @field_validator("model_name")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """验证模型名称"""
        if not v or not v.strip():
            raise ValueError("模型名称不能为空")
        return v.strip()

    def add_message(self, message: Message) -> None:
        """添加消息到对话"""
        self.messages.append(message)
        self.updated_at = datetime.now()
        if message.token_count:
            self.total_tokens += message.token_count

    def get_last_message(self) -> Optional[Message]:
        """获取最后一条消息"""
        return self.messages[-1] if self.messages else None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "conv_001",
                "messages": [],
                "title": "代码助手对话",
                "model_name": "gpt-4",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "metadata": {},
                "total_tokens": 0,
                "is_active": True
            }
        }
