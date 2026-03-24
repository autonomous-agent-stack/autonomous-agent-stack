"""System Log 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class Log(BaseModel):
    """日志模型 - 表示系统日志"""

    id: str = Field(..., description="日志唯一标识符")
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        ..., description="日志级别"
    )
    message: str = Field(..., description="日志消息")
    source: str = Field(..., description="日志来源")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="时间戳"
    )
    user_id: Optional[str] = Field(default=None, description="关联用户 ID")
    session_id: Optional[str] = Field(default=None, description="关联会话 ID")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    tags: List[str] = Field(
        default_factory=list, description="日志标签"
    )
    exception: Optional[Dict[str, Any]] = Field(
        default=None, description="异常信息"
    )
    duration_ms: Optional[int] = Field(
        default=None, description="持续时间（毫秒）"
    )
    request_id: Optional[str] = Field(
        default=None, description="请求 ID"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证日志 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("日志 ID 不能为空")
        return v.strip()

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """验证日志消息"""
        if not v or not v.strip():
            raise ValueError("日志消息不能为空")
        if len(v) > 10000:
            raise ValueError("日志消息过长")
        return v.strip()

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """验证日志来源"""
        if not v or not v.strip():
            raise ValueError("日志来源不能为空")
        return v.strip()

    @field_validator("duration_ms")
    @classmethod
    def validate_duration_ms(cls, v: Optional[int]) -> Optional[int]:
        """验证持续时间"""
        if v is not None and v < 0:
            raise ValueError("持续时间不能为负数")
        return v

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """验证标签列表"""
        # 去重并过滤空标签
        tags = list(set(tag for tag in v if tag and tag.strip()))
        if len(tags) > 20:
            raise ValueError("标签数量不能超过 20 个")
        return tags

    def add_tag(self, tag: str) -> None:
        """添加标签"""
        if tag and tag.strip() and tag not in self.tags:
            self.tags.append(tag.strip())

    def has_tag(self, tag: str) -> bool:
        """检查是否包含标签"""
        return tag in self.tags

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "tags": self.tags,
            "exception": self.exception,
            "duration_ms": self.duration_ms,
            "request_id": self.request_id
        }

    def is_error(self) -> bool:
        """检查是否为错误日志"""
        return self.level in ["ERROR", "CRITICAL"]

    class Config:
        json_schema_extra = {
            "example": {
                "id": "log_001",
                "level": "INFO",
                "message": "任务执行成功",
                "source": "agent.task",
                "timestamp": "2024-01-01T00:00:00",
                "user_id": "user_001",
                "session_id": "session_001",
                "metadata": {
                    "task_id": "task_001",
                    "result_count": 1
                },
                "tags": ["task", "success"],
                "exception": None,
                "duration_ms": 1500,
                "request_id": "req_001"
            }
        }
