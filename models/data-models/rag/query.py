"""RAG Query 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class Query(BaseModel):
    """查询模型 - 表示 RAG 查询"""

    id: str = Field(..., description="查询唯一标识符")
    text: str = Field(..., description="查询文本")
    embedding_id: Optional[str] = Field(
        default=None, description="查询向量 ID"
    )
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="查询过滤条件"
    )
    top_k: int = Field(default=5, description="返回前 k 个结果")
    threshold: Optional[float] = Field(
        default=None, description="相似度阈值"
    )
    query_type: Literal["semantic", "keyword", "hybrid"] = Field(
        default="semantic", description="查询类型"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证查询 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("查询 ID 不能为空")
        return v.strip()

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """验证查询文本不为空"""
        if not v or not v.strip():
            raise ValueError("查询文本不能为空")
        if len(v) > 2000:
            raise ValueError("查询文本过长")
        return v.strip()

    @field_validator("top_k")
    @classmethod
    def validate_top_k(cls, v: int) -> int:
        """验证 top_k 参数"""
        if v <= 0:
            raise ValueError("top_k 必须大于 0")
        if v > 100:
            raise ValueError("top_k 不能超过 100")
        return v

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v: Optional[float]) -> Optional[float]:
        """验证阈值参数"""
        if v is not None:
            if not 0 <= v <= 1:
                raise ValueError("阈值必须在 0-1 之间")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "query_001",
                "text": "如何使用 Python 进行数据可视化？",
                "embedding_id": "emb_002",
                "created_at": "2024-01-01T00:00:00",
                "metadata": {},
                "filters": {"doc_type": "markdown"},
                "top_k": 5,
                "threshold": 0.7,
                "query_type": "semantic"
            }
        }
