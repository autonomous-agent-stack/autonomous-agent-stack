from __future__ import annotations

from contextlib import contextmanager
import threading
from typing import Iterator


class WriterLeaseService:
    """Per-key single-writer lease for mutable control-plane state."""

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._locks: dict[str, threading.Lock] = {}

    @contextmanager
    def acquire(self, key: str, *, blocking: bool = True) -> Iterator[None]:
        normalized = key.strip()
        if not normalized:
            raise ValueError("writer lease key is required")

        with self._guard:
            lock = self._locks.setdefault(normalized, threading.Lock())

        acquired = lock.acquire(blocking=blocking)
        if not acquired:
            raise TimeoutError(f"writer lease is currently held: {normalized}")
        try:
            yield
        finally:
            lock.release()
