from __future__ import annotations

from typing import Generic, TypeVar
from uuid import uuid4


T = TypeVar("T")


def create_resource_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class InMemoryRepository(Generic[T]):
    """Simple in-memory repository for the API skeleton."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def save(self, resource_id: str, resource: T) -> T:
        self._items[resource_id] = resource
        return resource

    def get(self, resource_id: str) -> T | None:
        return self._items.get(resource_id)

    def list(self) -> list[T]:
        return list(self._items.values())
