"""RAG Document 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class Document(BaseModel):
    """文档模型 - 表示 RAG 中的文档"""

    id: str = Field(..., description="文档唯一标识符")
    title: str = Field(..., description="文档标题")
    content: str = Field(..., description="文档内容")
    source: str = Field(..., description="文档来源")
    doc_type: Literal["text", "pdf", "markdown", "html", "json"] = Field(
        default="text", description="文档类型"
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
    tags: List[str] = Field(
        default_factory=list, description="文档标签"
    )
    chunk_count: int = Field(default=0, description="分块数量")
    is_indexed: bool = Field(default=False, description="是否已索引")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证文档 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("文档 ID 不能为空")
        return v.strip()

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """验证标题不为空"""
        if not v or not v.strip():
            raise ValueError("文档标题不能为空")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """验证内容不为空"""
        if not v:
            raise ValueError("文档内容不能为空")
        return v

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        """验证来源不为空"""
        if not v or not v.strip():
            raise ValueError("文档来源不能为空")
        return v.strip()

    @field_validator("chunk_count")
    @classmethod
    def validate_chunk_count(cls, v: int) -> int:
        """验证分块数量"""
        if v < 0:
            raise ValueError("分块数量不能为负数")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_001",
                "title": "Python 入门指南",
                "content": "Python 是一种高级编程语言...",
                "source": "https://example.com/python",
                "doc_type": "markdown",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "metadata": {"author": "John Doe"},
                "tags": ["编程", "Python", "入门"],
                "chunk_count": 10,
                "is_indexed": True
            }
        }
