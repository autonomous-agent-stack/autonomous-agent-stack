"""System User 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, EmailStr


class User(BaseModel):
    """用户模型 - 表示系统用户"""

    id: str = Field(..., description="用户唯一标识符")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(default=None, description="全名")
    role: Literal["admin", "user", "guest"] = Field(
        default="user", description="用户角色"
    )
    status: Literal["active", "inactive", "suspended"] = Field(
        default="active", description="用户状态"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="更新时间"
    )
    last_login_at: Optional[datetime] = Field(
        default=None, description="最后登录时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    preferences: Dict[str, Any] = Field(
        default_factory=dict, description="用户偏好设置"
    )
    session_count: int = Field(default=0, description="会话数量")
    total_tokens_used: int = Field(default=0, description="总 token 使用量")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证用户 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("用户 ID 不能为空")
        return v.strip()

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名"""
        if not v or not v.strip():
            raise ValueError("用户名不能为空")
        if len(v) < 3 or len(v) > 50:
            raise ValueError("用户名长度必须在 3-50 之间")
        if not v.replace("_", "-").replace(".", "").isalnum():
            raise ValueError("用户名只能包含字母、数字、下划线、连字符和点")
        return v.strip()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """验证全名"""
        if v is not None:
            if len(v) > 100:
                raise ValueError("全名过长")
        return v

    @field_validator("session_count")
    @classmethod
    def validate_session_count(cls, v: int) -> int:
        """验证会话数量"""
        if v < 0:
            raise ValueError("会话数量不能为负数")
        return v

    @field_validator("total_tokens_used")
    @classmethod
    def validate_total_tokens_used(cls, v: int) -> int:
        """验证 token 使用量"""
        if v < 0:
            raise ValueError("token 使用量不能为负数")
        return v

    def update_last_login(self) -> None:
        """更新最后登录时间"""
        self.last_login_at = datetime.now()
        self.session_count += 1
        self.updated_at = datetime.now()

    def add_tokens_used(self, tokens: int) -> None:
        """添加使用的 token"""
        if tokens < 0:
            raise ValueError("token 数量不能为负数")
        self.total_tokens_used += tokens
        self.updated_at = datetime.now()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "user_001",
                "username": "john_doe",
                "email": "john@example.com",
                "full_name": "John Doe",
                "role": "user",
                "status": "active",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "last_login_at": "2024-01-01T12:00:00",
                "metadata": {},
                "preferences": {
                    "language": "zh-CN",
                    "theme": "dark"
                },
                "session_count": 42,
                "total_tokens_used": 150000
            }
        }
