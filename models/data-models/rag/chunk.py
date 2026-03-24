"""RAG Chunk 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class Chunk(BaseModel):
    """分块模型 - 表示文档的一个分块"""

    id: str = Field(..., description="分块唯一标识符")
    document_id: str = Field(..., description="所属文档 ID")
    content: str = Field(..., description="分块内容")
    chunk_index: int = Field(..., description="分块索引")
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    embedding_id: Optional[str] = Field(
        default=None, description="关联的向量 ID"
    )
    token_count: Optional[int] = Field(
        default=None, description="分块 token 数量"
    )
    char_count: int = Field(default=0, description="分块字符数")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证分块 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("分块 ID 不能为空")
        return v.strip()

    @field_validator("document_id")
    @classmethod
    def validate_document_id(cls, v: str) -> str:
        """验证文档 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("文档 ID 不能为空")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """验证内容不为空"""
        if not v:
            raise ValueError("分块内容不能为空")
        return v

    @field_validator("chunk_index")
    @classmethod
    def validate_chunk_index(cls, v: int) -> int:
        """验证分块索引"""
        if v < 0:
            raise ValueError("分块索引不能为负数")
        return v

    @field_validator("char_count")
    @classmethod
    def validate_char_count(cls, v: int) -> int:
        """验证字符数"""
        if v < 0:
            raise ValueError("字符数不能为负数")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "chunk_001",
                "document_id": "doc_001",
                "content": "这是文档的第一个分块...",
                "chunk_index": 0,
                "created_at": "2024-01-01T00:00:00",
                "metadata": {"position": "start"},
                "embedding_id": "emb_001",
                "token_count": 100,
                "char_count": 500
            }
        }
