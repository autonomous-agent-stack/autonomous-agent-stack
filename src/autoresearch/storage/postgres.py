from __future__ import annotations

from dataclasses import dataclass

from autoresearch.ga.contracts import StorageProfileKind


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

