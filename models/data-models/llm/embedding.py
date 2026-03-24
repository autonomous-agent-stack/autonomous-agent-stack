"""LLM Embedding 数据模型"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class Embedding(BaseModel):
    """向量模型 - 表示文本的向量表示"""

    id: str = Field(..., description="向量唯一标识符")
    text: str = Field(..., description="原始文本")
    embedding: List[float] = Field(..., description="向量数据")
    model: str = Field(..., description="使用的模型")
    dimensions: int = Field(..., description="向量维度")
    created_at: datetime = Field(
        default_factory=datetime.now, description="创建时间"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="额外元数据"
    )
    token_count: Optional[int] = Field(
        default=None, description="文本 token 数量"
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """验证向量 ID 不为空"""
        if not v or not v.strip():
            raise ValueError("向量 ID 不能为空")
        return v.strip()

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        """验证文本不为空"""
        if not v or not v.strip():
            raise ValueError("文本不能为空")
        return v.strip()

    @field_validator("embedding")
    @classmethod
    def validate_embedding(cls, v: List[float]) -> List[float]:
        """验证向量数据"""
        if not v:
            raise ValueError("向量数据不能为空")
        if len(v) == 0:
            raise ValueError("向量维度不能为 0")
        return v

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, v: int, info) -> int:
        """验证向量维度"""
        if v <= 0:
            raise ValueError("向量维度必须大于 0")
        # 验证维度是否与实际向量长度匹配
        if "embedding" in info.data and len(info.data["embedding"]) != v:
            raise ValueError("向量维度与实际数据不匹配")
        return v

    def similarity(self, other: "Embedding") -> float:
        """计算与另一个向量的余弦相似度"""
        if len(self.embedding) != len(other.embedding):
            raise ValueError("向量维度不匹配")

        dot_product = sum(a * b for a, b in zip(self.embedding, other.embedding))
        norm_a = sum(a ** 2 for a in self.embedding) ** 0.5
        norm_b = sum(b ** 2 for b in other.embedding) ** 0.5

        return dot_product / (norm_a * norm_b)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "emb_001",
                "text": "这是一段示例文本",
                "embedding": [0.1, 0.2, 0.3, 0.4],
                "model": "text-embedding-ada-002",
                "dimensions": 4,
                "created_at": "2024-01-01T00:00:00",
                "metadata": {},
                "token_count": 5
            }
        }
