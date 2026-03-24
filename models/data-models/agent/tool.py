"""Agent Tool 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class ToolParameter(BaseModel):
    """工具参数模型"""

    name: str = Field(..., description="参数名称")
    type: Literal["string", "number", "boolean", "array", "object"] = Field(
        ..., description="参数类型"
    )
    required: bool = Field(default=False, description="是否必需")
    description: str = Field(default="", description="参数描述")
    default: Optional[Any] = Field(default=None, description="默认值")
    enum: Optional[List[Any]] = Field(default=None, description="枚举值")


class Tool(BaseModel):
    """工具模型 - 表示 Agent 可用的工具"""

    id: str = Field(..., description="工具唯一标识符")
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    type: Literal["function", "api", "custom"] = Field(
        default="function", description="工具类型"
    )
    parameters: List[ToolParameter] = Field(
        default_factory=list, description="工具参数列表"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="更新时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    is_enabled: bool = Field(default=True, description="是否启用")
    usage_count: int = Field(default=0, description="使用次数")
    execution_time_ms: Optional[int] = Field(
        default=None, description="平均执行时间（毫秒）"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证工具 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("工具 ID 不能为空")
        return v.strip()

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证工具名称"""
        if not v or not v.strip():
            raise ValueError("工具名称不能为空")
        # 工具名称只能包含字母、数字、下划线和连字符
        if not v.replace("-", "_").replace("_", "").isalnum():
            raise ValueError("工具名称只能包含字母、数字、下划线和连字符")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """验证描述不为空"""
        if not v:
            raise ValueError("工具描述不能为空")
        if len(v) > 500:
            raise ValueError("工具描述过长")
        return v

    @field_validator("usage_count")
    @classmethod
    def validate_usage_count(cls, v: int) -> int:
        """验证使用次数"""
        if v < 0:
            raise ValueError("使用次数不能为负数")
        return v

    @field_validator("execution_time_ms")
    @classmethod
    def validate_execution_time_ms(cls, v: Optional[int]) -> Optional[int]:
        """验证执行时间"""
        if v is not None and v < 0:
            raise ValueError("执行时间不能为负数")
        return v

    def record_usage(self, execution_time_ms: int) -> None:
        """记录工具使用"""
        self.usage_count += 1
        if self.execution_time_ms is None:
            self.execution_time_ms = execution_time_ms
        else:
            # 简单的移动平均
            self.execution_time_ms = int(
                (self.execution_time_ms * (self.usage_count - 1) + execution_time_ms) / self.usage_count
            )
        self.updated_at = datetime.now()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "tool_001",
                "name": "web_search",
                "description": "执行网络搜索并返回结果",
                "type": "function",
                "parameters": [
                    {
                        "name": "query",
                        "type": "string",
                        "required": True,
                        "description": "搜索关键词"
                    },
                    {
                        "name": "limit",
                        "type": "number",
                        "required": False,
                        "description": "返回结果数量",
                        "default": 10
                    }
                ],
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "metadata": {},
                "is_enabled": True,
                "usage_count": 150,
                "execution_time_ms": 500
            }
        }
