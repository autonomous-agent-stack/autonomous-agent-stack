"""
统一节点协议，降低多模块拼接时的胶水代码成本。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class NodeStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class NodeOutput:
    status: NodeStatus
    data: dict[str, Any]
    metadata: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "data": self.data,
            "metadata": self.metadata,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "NodeOutput":
        return cls(
            status=NodeStatus(payload["status"]),
            data=dict(payload.get("data", {})),
            metadata=dict(payload.get("metadata", {})),
            error=payload.get("error"),
        )


class NodeAdapter(ABC):
    @abstractmethod
    async def execute(self, input_data: dict[str, Any]) -> NodeOutput:
        raise NotImplementedError


class NodeRegistry:
    _registry: dict[str, NodeAdapter] = {}

    @classmethod
    def register(cls, node_type: str, adapter: NodeAdapter) -> None:
        cls._registry[node_type] = adapter

    @classmethod
    def get(cls, node_type: str) -> NodeAdapter:
        if node_type not in cls._registry:
            raise KeyError(f"Node adapter not registered: {node_type}")
        return cls._registry[node_type]

    @classmethod
    def list_registered(cls) -> list[str]:
        return sorted(cls._registry)
