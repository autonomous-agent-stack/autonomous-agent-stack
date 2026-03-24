"""System Session 数据模型"""
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class Session(BaseModel):
    """会话模型 - 表示用户会话"""

    id: str = Field(..., description="会话唯一标识符")
    user_id: str = Field(..., description="关联用户 ID")
    session_type: Literal["chat", "api", "bot"] = Field(
        default="chat", description="会话类型"
    )
    status: Literal["active", "inactive", "expired"] = Field(
        default="active", description="会话状态"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="更新时间"
    )
    expired_at: Optional[datetime] = Field(
        default=None, description="过期时间"
    )
    last_activity_at: datetime = Field(
        default_factory=datetime.now, description="最后活动时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    message_count: int = Field(default=0, description="消息数量")
    token_count: int = Field(default=0, description="token 数量")
    client_info: Optional[Dict[str, Any]] = Field(
        default=None, description="客户端信息"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证会话 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("会话 ID 不能为空")
        return v.strip()

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """验证用户 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("用户 ID 不能为空")
        return v.strip()

    @field_validator("message_count")
    @classmethod
    def validate_message_count(cls, v: int) -> int:
        """验证消息数量"""
        if v < 0:
            raise ValueError("消息数量不能为负数")
        return v

    @field_validator("token_count")
    @classmethod
    def validate_token_count(cls, v: int) -> int:
        """验证 token 数量"""
        if v < 0:
            raise ValueError("token 数量不能为负数")
        return v

    def is_expired(self) -> bool:
        """检查会话是否过期"""
        if self.expired_at is None:
            return False
        return datetime.now() > self.expired_at

    def update_activity(self) -> None:
        """更新活动时间"""
        self.last_activity_at = datetime.now()
        self.updated_at = datetime.now()

    def add_message(self, token_count: int = 0) -> None:
        """添加消息记录"""
        self.message_count += 1
        self.token_count += token_count
        self.update_activity()

    def close(self) -> None:
        """关闭会话"""
        self.status = "inactive"
        self.updated_at = datetime.now()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "session_001",
                "user_id": "user_001",
                "session_type": "chat",
                "status": "active",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "expired_at": "2024-01-01T01:00:00",
                "last_activity_at": "2024-01-01T00:30:00",
                "metadata": {},
                "message_count": 25,
                "token_count": 3500,
                "client_info": {
                    "platform": "web",
                    "browser": "Chrome",
                    "os": "macOS"
                }
            }
        }
