from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from autoresearch.ga.contracts import StorageProfileKind
from autoresearch.shared.models import SessionEventCreateRequest, SessionEventRead, utc_now
from autoresearch.storage.events import SessionEventStore, build_session_event, verify_event_hash


@dataclass(frozen=True)
class PostgresStorageProfile:
    """Production storage profile marker.

    The runtime intentionally does not import a PostgreSQL driver at module import time.
    Deployments wire the concrete driver through this profile; GA gates verify that the
    production profile is PostgreSQL and that event-store contract tests cover the
    transactional semantics.
    """

    dsn_env: str = "AUTORESEARCH_POSTGRES_DSN"
    profile: StorageProfileKind = StorageProfileKind.PRODUCTION
    required_features: tuple[str, ...] = (
        "transactional_event_append",
        "sequence_no_allocation",
        "idempotency_key_unique_constraint",
        "content_hash_verification",
        "event_replay",
        "backup_restore",
        "migration_rollback",
        "outbox_table",
        "inbox_dedupe_table",
    )


class PostgresSessionEventStore(SessionEventStore):
    """Transactional PostgreSQL production SessionEvent store.

    SQLite remains the local/dev store. This store owns the production append-only
    path with per-session sequence allocation, idempotency, content-hash checks,
    replay ordering, outbox, inbox dedupe, and rollback-safe migrations.
    """

    schema_version = 1

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn.strip()
        if not self._dsn:
            raise ValueError("PostgresSessionEventStore requires a PostgreSQL DSN")

    def migrate(self) -> None:
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_event_schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_event_sequences (
                        session_id TEXT PRIMARY KEY,
                        next_sequence_no BIGINT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_events (
                        event_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        sequence_no BIGINT NOT NULL,
                        idempotency_key TEXT UNIQUE,
                        content_hash TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        UNIQUE(session_id, sequence_no)
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_event_outbox (
                        outbox_id BIGSERIAL PRIMARY KEY,
                        event_id TEXT NOT NULL UNIQUE REFERENCES session_events(event_id),
                        session_id TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL,
                        delivered_at TIMESTAMPTZ
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_event_inbox_dedupe (
                        inbox_key TEXT PRIMARY KEY,
                        received_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    INSERT INTO session_event_schema_migrations (version, applied_at)
                    VALUES (%s, NOW())
                    ON CONFLICT(version) DO NOTHING
                    """,
                    (self.schema_version,),
                )
            connection.commit()

    def rollback(self, *, target_version: int) -> None:
        """Record rollback intent without deleting SessionEvent facts."""
        if target_version >= self.schema_version:
            return
        self.append(
            SessionEventCreateRequest(
                session_id="system",
                source="postgres_event_store",
                event_type="schema.rollback.requested",
                content=f"rollback from {self.schema_version} to {target_version}",
                payload={"from_version": self.schema_version, "target_version": target_version},
                idempotency_key=f"schema-rollback-{self.schema_version}-to-{target_version}",
            )
        )

    def append(self, request: SessionEventCreateRequest) -> SessionEventRead:
        self.migrate()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                if request.idempotency_key:
                    existing = self._fetch_existing_by_idempotency(cursor, request.idempotency_key)
                    if existing is not None:
                        return existing
                sequence_no = self._next_sequence_no(cursor, request.session_id)
                event = build_session_event(request, sequence_no=sequence_no)
                if not verify_event_hash(event):
                    raise ValueError("SessionEvent content_hash verification failed")
                payload_json = json.dumps(event.model_dump(mode="json"), sort_keys=True)
                cursor.execute(
                    """
                    INSERT INTO session_events (
                        event_id, session_id, sequence_no, idempotency_key, content_hash, payload_json, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        event.event_id,
                        event.session_id,
                        event.sequence_no,
                        event.idempotency_key,
                        event.content_hash,
                        payload_json,
                        event.created_at,
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO session_event_outbox (event_id, session_id, payload_json, created_at, delivered_at)
                    VALUES (%s, %s, %s, %s, NULL)
                    """,
                    (event.event_id, event.session_id, payload_json, event.created_at),
                )
            connection.commit()
            return event

    def list_events(self, session_id: str) -> list[SessionEventRead]:
        self.migrate()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT payload_json FROM session_events
                    WHERE session_id = %s
                    ORDER BY sequence_no ASC, created_at ASC, event_id ASC
                    """,
                    (session_id.strip(),),
                )
                rows = cursor.fetchall()
        return [SessionEventRead.model_validate(json.loads(row[0])) for row in rows]

    def replay(self, session_id: str) -> list[SessionEventRead]:
        return self.list_events(session_id)

    def record_inbox(self, inbox_key: str) -> bool:
        self.migrate()
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO session_event_inbox_dedupe (inbox_key, received_at)
                    VALUES (%s, %s)
                    ON CONFLICT(inbox_key) DO NOTHING
                    """,
                    (inbox_key.strip(), utc_now()),
                )
                inserted = cursor.rowcount == 1
            connection.commit()
        return inserted

    def backup_manifest(self) -> dict[str, Any]:
        return {
            "driver": "postgresql",
            "strategy": "use pg_dump with transaction snapshot for production backup",
            "dsn_configured": bool(self._dsn),
            "schema_version": self.schema_version,
        }

    def restore_manifest(self) -> dict[str, Any]:
        return {
            "driver": "postgresql",
            "strategy": "restore with pg_restore into a new database, validate content_hash, then cut over",
            "schema_version": self.schema_version,
        }

    def _fetch_existing_by_idempotency(self, cursor: Any, idempotency_key: str) -> SessionEventRead | None:
        cursor.execute(
            "SELECT payload_json FROM session_events WHERE idempotency_key = %s",
            (idempotency_key,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return SessionEventRead.model_validate(json.loads(row[0]))

    @staticmethod
    def _next_sequence_no(cursor: Any, session_id: str) -> int:
        cursor.execute(
            """
            INSERT INTO session_event_sequences (session_id, next_sequence_no)
            VALUES (%s, 2)
            ON CONFLICT(session_id) DO UPDATE
            SET next_sequence_no = session_event_sequences.next_sequence_no + 1
            RETURNING next_sequence_no - 1
            """,
            (session_id.strip(),),
        )
        row = cursor.fetchone()
        return int(row[0])

    def _connect(self) -> Any:
        try:
            import psycopg

            return psycopg.connect(self._dsn)
        except ModuleNotFoundError:
            try:
                import psycopg2

                return psycopg2.connect(self._dsn)
            except ModuleNotFoundError as exc:
                raise RuntimeError("PostgreSQL production event store requires psycopg or psycopg2") from exc
