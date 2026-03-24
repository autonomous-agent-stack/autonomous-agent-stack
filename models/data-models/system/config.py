"""System Config 数据模型"""
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """配置模型 - 表示系统配置"""

    id: str = Field(..., description="配置唯一标识符")
    key: str = Field(..., description="配置键")
    value: Any = Field(..., description="配置值")
    description: Optional[str] = Field(default=None, description="配置描述")
    config_type: str = Field(default="string", description="配置类型")
    is_sensitive: bool = Field(default=False, description="是否敏感信息")
    is_readonly: bool = Field(default=False, description="是否只读")
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="更新时间"
    )
    updated_by: Optional[str] = Field(
        default=None, description="更新者 ID"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    validation_rules: Optional[Dict[str, Any]] = Field(
        default=None, description="验证规则"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证配置 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("配置 ID 不能为空")
        return v.strip()

    @field_validator("key")
    @classmethod
    def validate_key(cls, v: str) -> str:
        """验证配置键"""
        if not v or not v.strip():
            raise ValueError("配置键不能为空")
        # 配置键格式: section.key_name
        if not v.replace(".", "_").isalnum():
            raise ValueError("配置键只能包含字母、数字、下划线和点")
        if v.startswith(".") or v.endswith("."):
            raise ValueError("配置键不能以点开头或结尾")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """验证描述"""
        if v is not None:
            if len(v) > 500:
                raise ValueError("配置描述过长")
        return v

    @field_validator("config_type")
    @classmethod
    def validate_config_type(cls, v: str) -> str:
        """验证配置类型"""
        valid_types = ["string", "number", "boolean", "json", "array"]
        if v not in valid_types:
            raise ValueError(f"配置类型必须是: {', '.join(valid_types)}")
        return v

    def validate_value(self) -> bool:
        """验证配置值是否有效"""
        if self.validation_rules is None:
            return True

        rules = self.validation_rules

        # 检查是否为必填
        if rules.get("required") and self.value is None:
            return False

        # 检查枚举值
        if "enum" in rules and self.value not in rules["enum"]:
            return False

        # 检查范围
        if self.config_type == "number":
            if "min" in rules and self.value < rules["min"]:
                return False
            if "max" in rules and self.value > rules["max"]:
                return False

        # 检查字符串长度
        if self.config_type == "string" and isinstance(self.value, str):
            if "min_length" in rules and len(self.value) < rules["min_length"]:
                return False
            if "max_length" in rules and len(self.value) > rules["max_length"]:
                return False

        return True

    def update_value(self, new_value: Any, updated_by: str) -> None:
        """更新配置值"""
        self.value = new_value
        self.updated_by = updated_by
        self.updated_at = datetime.now()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "config_001",
                "key": "llm.model_name",
                "value": "gpt-4",
                "description": "默认 LLM 模型",
                "config_type": "string",
                "is_sensitive": False,
                "is_readonly": False,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "updated_by": "user_001",
                "metadata": {},
                "validation_rules": {
                    "required": True,
                    "enum": ["gpt-3.5-turbo", "gpt-4", "claude-3"]
                }
            }
        }
