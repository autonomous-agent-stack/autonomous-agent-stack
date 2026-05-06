from __future__ import annotations

from pathlib import Path

from autoresearch.shared.models import SessionEventCreateRequest
from autoresearch.storage.events import SQLiteSessionEventStore, verify_event_hash
from autoresearch.storage.postgres import PostgresSessionEventStore, PostgresStorageProfile


def test_sqlite_event_store_is_transactional_local_profile_with_idempotency(tmp_path: Path) -> None:
    store = SQLiteSessionEventStore(tmp_path / "events.sqlite3")
    request = SessionEventCreateRequest(
        session_id="session-ga",
        source="test",
        event_type="run.created",
        content="created",
        idempotency_key="same-event",
        payload={"run_id": "run-1"},
    )

    first = store.append(request)
    second = store.append(request)
    third = store.append(
        request.model_copy(update={"idempotency_key": "next-event", "event_type": "run.started"})
    )

    assert first.event_id == second.event_id
    assert first.sequence_no == 1
    assert third.sequence_no == 2
    assert len(store.replay("session-ga")) == 2
    assert verify_event_hash(first)


def test_postgres_profile_declares_required_production_features() -> None:
    profile = PostgresStorageProfile()

    assert profile.profile.value == "production"
    assert "transactional_event_append" in profile.required_features
    assert "inbox_dedupe_table" in profile.required_features


def test_postgres_event_store_exposes_production_contract() -> None:
    store_type = PostgresSessionEventStore

    for method in (
        "append",
        "list_events",
        "replay",
        "migrate",
        "rollback",
        "record_inbox",
        "backup_manifest",
        "restore_manifest",
    ):
        assert callable(getattr(store_type, method))
