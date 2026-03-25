from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Generic, TypeVar
from typing import Protocol
from uuid import uuid4


T = TypeVar("T")


def create_resource_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class Repository(Protocol, Generic[T]):
    """Minimal repository contract shared by API services."""

    def save(self, resource_id: str, resource: T) -> T: ...

    def get(self, resource_id: str) -> T | None: ...

    def list(self) -> list[T]: ...


class InMemoryRepository(Generic[T], Repository[T]):
    """Simple in-memory repository."""

    def __init__(self) -> None:
        self._items: dict[str, T] = {}

    def save(self, resource_id: str, resource: T) -> T:
        self._items[resource_id] = resource
        return resource

    def get(self, resource_id: str) -> T | None:
        return self._items.get(resource_id)

    def list(self) -> list[T]:
        return list(self._items.values())


class SQLiteModelRepository(Generic[T], Repository[T]):
    """Persist typed resource models as JSON payloads in SQLite."""

    def __init__(self, db_path: Path, table_name: str, model_cls: type[T]) -> None:
        self._db_path = db_path
        self._table_name = self._validate_identifier(table_name)
        self._model_cls = model_cls
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save(self, resource_id: str, resource: T) -> T:
        payload_json = json.dumps(self._serialize(resource), sort_keys=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                f"""
                INSERT INTO {self._table_name} (
                    resource_id,
                    payload_json,
                    updated_at
                ) VALUES (?, ?, ?)
                ON CONFLICT(resource_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (resource_id, payload_json, timestamp),
            )
            connection.commit()
        return resource

    def get(self, resource_id: str) -> T | None:
        with self._connect() as connection:
            row = connection.execute(
                f"""
                SELECT payload_json
                FROM {self._table_name}
                WHERE resource_id = ?
                """,
                (resource_id,),
            ).fetchone()
        if row is None:
            return None
        return self._deserialize(row["payload_json"])

    def list(self) -> list[T]:
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT payload_json
                FROM {self._table_name}
                ORDER BY updated_at DESC, resource_id DESC
                """
            ).fetchall()
        return [self._deserialize(row["payload_json"]) for row in rows]

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self._table_name} (
                    resource_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                f"""
                CREATE INDEX IF NOT EXISTS idx_{self._table_name}_updated_at
                ON {self._table_name}(updated_at)
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _serialize(self, resource: T) -> object:
        if hasattr(resource, "model_dump"):
            return resource.model_dump(mode="json")
        return resource

    def _deserialize(self, payload_json: str) -> T:
        payload = json.loads(payload_json)
        if hasattr(self._model_cls, "model_validate"):
            return self._model_cls.model_validate(payload)
        if isinstance(payload, dict):
            return self._model_cls(**payload)
        return self._model_cls(payload)

    def _validate_identifier(self, value: str) -> str:
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
            raise ValueError(f"Unsupported SQL identifier: {value}")
        return value
