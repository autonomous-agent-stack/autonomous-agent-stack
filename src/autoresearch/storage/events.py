from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Protocol

from autoresearch.shared.models import SessionEventCreateRequest, SessionEventRead, utc_now
from autoresearch.shared.store import create_resource_id


class SessionEventStore(Protocol):
    def append(self, request: SessionEventCreateRequest) -> SessionEventRead: ...

    def list_events(self, session_id: str) -> list[SessionEventRead]: ...

    def replay(self, session_id: str) -> list[SessionEventRead]: ...


class InMemorySessionEventStore(SessionEventStore):
    def __init__(self) -> None:
        self._events: dict[str, SessionEventRead] = {}
        self._idempotency: dict[str, str] = {}

    def append(self, request: SessionEventCreateRequest) -> SessionEventRead:
        if request.idempotency_key and request.idempotency_key in self._idempotency:
            return self._events[self._idempotency[request.idempotency_key]]
        events = self.list_events(request.session_id)
        event = build_session_event(request, sequence_no=len(events) + 1)
        self._events[event.event_id] = event
        if event.idempotency_key:
            self._idempotency[event.idempotency_key] = event.event_id
        return event

    def list_events(self, session_id: str) -> list[SessionEventRead]:
        events = [event for event in self._events.values() if event.session_id == session_id.strip()]
        return sorted(events, key=lambda item: (item.sequence_no, item.created_at, item.event_id))

    def replay(self, session_id: str) -> list[SessionEventRead]:
        return self.list_events(session_id)


class SQLiteSessionEventStore(SessionEventStore):
    """Transactional local/dev event store with idempotency and outbox tables."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def append(self, request: SessionEventCreateRequest) -> SessionEventRead:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if request.idempotency_key:
                existing = connection.execute(
                    "SELECT payload_json FROM session_events WHERE idempotency_key = ?",
                    (request.idempotency_key,),
                ).fetchone()
                if existing is not None:
                    connection.commit()
                    return SessionEventRead.model_validate(json.loads(existing["payload_json"]))
            sequence_no = self._next_sequence_no(connection, request.session_id)
            event = build_session_event(request, sequence_no=sequence_no)
            payload_json = json.dumps(event.model_dump(mode="json"), sort_keys=True)
            connection.execute(
                """
                INSERT INTO session_events (
                    event_id, session_id, sequence_no, idempotency_key, content_hash, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.session_id,
                    event.sequence_no,
                    event.idempotency_key,
                    event.content_hash,
                    payload_json,
                    event.created_at.isoformat(),
                ),
            )
            connection.execute(
                """
                INSERT INTO session_event_outbox (event_id, session_id, payload_json, created_at, delivered_at)
                VALUES (?, ?, ?, ?, NULL)
                """,
                (event.event_id, event.session_id, payload_json, event.created_at.isoformat()),
            )
            connection.commit()
            return event

    def list_events(self, session_id: str) -> list[SessionEventRead]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json FROM session_events
                WHERE session_id = ?
                ORDER BY sequence_no ASC, created_at ASC, event_id ASC
                """,
                (session_id.strip(),),
            ).fetchall()
        return [SessionEventRead.model_validate(json.loads(row["payload_json"])) for row in rows]

    def replay(self, session_id: str) -> list[SessionEventRead]:
        return self.list_events(session_id)

    def backup(self, backup_path: Path) -> Path:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as source, sqlite3.connect(backup_path) as target:
            source.backup(target)
        return backup_path

    def restore(self, backup_path: Path) -> None:
        with sqlite3.connect(backup_path) as source, self._connect() as target:
            source.backup(target)

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    sequence_no INTEGER NOT NULL,
                    idempotency_key TEXT UNIQUE,
                    content_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(session_id, sequence_no)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_event_outbox (
                    outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    session_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    delivered_at TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_event_inbox_dedupe (
                    inbox_key TEXT PRIMARY KEY,
                    received_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    @staticmethod
    def _next_sequence_no(connection: sqlite3.Connection, session_id: str) -> int:
        row = connection.execute(
            "SELECT COALESCE(MAX(sequence_no), 0) AS max_sequence_no FROM session_events WHERE session_id = ?",
            (session_id.strip(),),
        ).fetchone()
        return int(row["max_sequence_no"] or 0) + 1


def build_session_event(request: SessionEventCreateRequest, *, sequence_no: int) -> SessionEventRead:
    payload = dict(request.payload or {})
    if not payload and request.content:
        payload = {"content": request.content}
    content_hash = request.content_hash or compute_event_hash(
        {
            "session_id": request.session_id.strip(),
            "sequence_no": sequence_no,
            "event_type": request.event_type.strip(),
            "payload": payload,
            "artifact_refs": request.artifact_refs,
            "created_by": request.actor_id,
        }
    )
    return SessionEventRead(
        event_id=create_resource_id("sev"),
        session_id=request.session_id.strip(),
        sequence_no=sequence_no,
        source=request.source.strip(),
        event_type=request.event_type.strip(),
        event_version=request.event_version,
        actor_type=request.actor_type,
        actor_id=request.actor_id,
        causation_id=request.causation_id,
        correlation_id=request.correlation_id,
        role=request.role,
        content=request.content.strip(),
        status=_clean_optional(request.status),
        runtime_id=_clean_optional(request.runtime_id),
        run_id=_clean_optional(request.run_id),
        approval_id=_clean_optional(request.approval_id),
        worker_id=_clean_optional(request.worker_id),
        external_event_id=_clean_optional(request.external_event_id),
        idempotency_key=_clean_optional(request.idempotency_key),
        payload=payload,
        artifact_refs=list(request.artifact_refs),
        policy_decision_id=_clean_optional(request.policy_decision_id),
        content_hash=content_hash,
        metadata=dict(request.metadata),
        created_at=utc_now(),
    )


def compute_event_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_event_hash(event: SessionEventRead) -> bool:
    expected = compute_event_hash(
        {
            "session_id": event.session_id,
            "sequence_no": event.sequence_no,
            "event_type": event.event_type,
            "payload": event.payload or ({"content": event.content} if event.content else {}),
            "artifact_refs": event.artifact_refs,
            "created_by": event.actor_id,
        }
    )
    return event.content_hash == expected


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
