"""RAG Result 数据模型"""
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class Result(BaseModel):
    """结果模型 - 表示 RAG 查询结果"""

    id: str = Field(..., description="结果唯一标识符")
    query_id: str = Field(..., description="关联查询 ID")
    chunk_id: str = Field(..., description="分块 ID")
    document_id: str = Field(..., description="文档 ID")
    score: float = Field(..., description="相似度分数")
    rank: int = Field(..., description="排名")
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    is_selected: bool = Field(default=False, description="是否被选中")

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证结果 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("结果 ID 不能为空")
        return v.strip()

    @field_validator("query_id")
    @classmethod
    def validate_query_id(cls, v: str) -> str:
        """验证查询 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("查询 ID 不能为空")
        return v.strip()

    @field_validator("chunk_id")
    @classmethod
    def validate_chunk_id(cls, v: str) -> str:
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

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: float) -> float:
        """验证相似度分数"""
        if not 0 <= v <= 1:
            raise ValueError("相似度分数必须在 0-1 之间")
        return v

    @field_validator("rank")
    @classmethod
    def validate_rank(cls, v: int) -> int:
        """验证排名"""
        if v < 0:
            raise ValueError("排名不能为负数")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "result_001",
                "query_id": "query_001",
                "chunk_id": "chunk_001",
                "document_id": "doc_001",
                "score": 0.85,
                "rank": 1,
                "created_at": "2024-01-01T00:00:00",
                "metadata": {},
                "is_selected": True
            }
        }
