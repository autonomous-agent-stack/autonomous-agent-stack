from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Protocol

from autoresearch.shared.models import (
    YouTubeDigestRead,
    YouTubeRunKind,
    YouTubeRunRead,
    YouTubeSubscriptionRead,
    YouTubeSubscriptionStatus,
    YouTubeTranscriptRead,
    YouTubeVideoRead,
)
from autoresearch.shared.store import InMemoryRepository, SQLiteModelRepository


class YouTubeRepository(Protocol):
    def save_subscription(self, subscription: YouTubeSubscriptionRead) -> YouTubeSubscriptionRead: ...

    def get_subscription(self, subscription_id: str) -> YouTubeSubscriptionRead | None: ...

    def get_subscription_by_normalized_url(self, normalized_url: str) -> YouTubeSubscriptionRead | None: ...

    def list_subscriptions(
        self,
        *,
        status: YouTubeSubscriptionStatus | None = None,
        include_deleted: bool = False,
    ) -> list[YouTubeSubscriptionRead]: ...

    def save_video(self, video: YouTubeVideoRead) -> YouTubeVideoRead: ...

    def get_video(self, video_id: str) -> YouTubeVideoRead | None: ...

    def list_videos(self, subscription_id: str | None = None) -> list[YouTubeVideoRead]: ...

    def save_transcript(self, transcript: YouTubeTranscriptRead) -> YouTubeTranscriptRead: ...

    def get_transcript(self, transcript_id: str) -> YouTubeTranscriptRead | None: ...

    def get_transcript_by_video_id(self, video_id: str) -> YouTubeTranscriptRead | None: ...

    def list_transcripts(self) -> list[YouTubeTranscriptRead]: ...

    def save_digest(self, digest: YouTubeDigestRead) -> YouTubeDigestRead: ...

    def get_digest(self, digest_id: str) -> YouTubeDigestRead | None: ...

    def get_digest_by_video_id(self, video_id: str) -> YouTubeDigestRead | None: ...

    def list_digests(self) -> list[YouTubeDigestRead]: ...

    def save_run(self, run: YouTubeRunRead) -> YouTubeRunRead: ...

    def get_run(self, run_id: str) -> YouTubeRunRead | None: ...

    def list_runs(
        self,
        *,
        subscription_id: str | None = None,
        video_id: str | None = None,
        kind: YouTubeRunKind | None = None,
    ) -> list[YouTubeRunRead]: ...


class InMemoryYouTubeRepository:
    def __init__(self) -> None:
        self._subscriptions = InMemoryRepository[YouTubeSubscriptionRead]()
        self._videos = InMemoryRepository[YouTubeVideoRead]()
        self._transcripts = InMemoryRepository[YouTubeTranscriptRead]()
        self._digests = InMemoryRepository[YouTubeDigestRead]()
        self._runs = InMemoryRepository[YouTubeRunRead]()
        self._subscription_by_url: dict[str, str] = {}
        self._transcript_by_video: dict[str, str] = {}
        self._digest_by_video: dict[str, str] = {}

    def save_subscription(self, subscription: YouTubeSubscriptionRead) -> YouTubeSubscriptionRead:
        self._subscription_by_url[subscription.normalized_url] = subscription.subscription_id
        return self._subscriptions.save(subscription.subscription_id, subscription)

    def get_subscription(self, subscription_id: str) -> YouTubeSubscriptionRead | None:
        return self._subscriptions.get(subscription_id)

    def get_subscription_by_normalized_url(self, normalized_url: str) -> YouTubeSubscriptionRead | None:
        resource_id = self._subscription_by_url.get(normalized_url)
        if resource_id is None:
            return None
        return self._subscriptions.get(resource_id)

    def list_subscriptions(
        self,
        *,
        status: YouTubeSubscriptionStatus | None = None,
        include_deleted: bool = False,
    ) -> list[YouTubeSubscriptionRead]:
        items = sorted(
            self._subscriptions.list(),
            key=lambda item: (item.updated_at, item.subscription_id),
            reverse=True,
        )
        if status is not None:
            return [item for item in items if item.status == status]
        if include_deleted:
            return items
        return [item for item in items if item.status != YouTubeSubscriptionStatus.DELETED]

    def save_video(self, video: YouTubeVideoRead) -> YouTubeVideoRead:
        return self._videos.save(video.video_id, video)

    def get_video(self, video_id: str) -> YouTubeVideoRead | None:
        return self._videos.get(video_id)

    def list_videos(self, subscription_id: str | None = None) -> list[YouTubeVideoRead]:
        items = sorted(
            self._videos.list(),
            key=lambda item: (item.updated_at, item.video_id),
            reverse=True,
        )
        if subscription_id is None:
            return items
        return [item for item in items if item.subscription_id == subscription_id]

    def save_transcript(self, transcript: YouTubeTranscriptRead) -> YouTubeTranscriptRead:
        self._transcript_by_video[transcript.video_id] = transcript.transcript_id
        return self._transcripts.save(transcript.transcript_id, transcript)

    def get_transcript(self, transcript_id: str) -> YouTubeTranscriptRead | None:
        return self._transcripts.get(transcript_id)

    def get_transcript_by_video_id(self, video_id: str) -> YouTubeTranscriptRead | None:
        resource_id = self._transcript_by_video.get(video_id)
        if resource_id is None:
            return None
        return self._transcripts.get(resource_id)

    def list_transcripts(self) -> list[YouTubeTranscriptRead]:
        return sorted(
            self._transcripts.list(),
            key=lambda item: (item.updated_at, item.transcript_id),
            reverse=True,
        )

    def save_digest(self, digest: YouTubeDigestRead) -> YouTubeDigestRead:
        self._digest_by_video[digest.video_id] = digest.digest_id
        return self._digests.save(digest.digest_id, digest)

    def get_digest(self, digest_id: str) -> YouTubeDigestRead | None:
        return self._digests.get(digest_id)

    def get_digest_by_video_id(self, video_id: str) -> YouTubeDigestRead | None:
        resource_id = self._digest_by_video.get(video_id)
        if resource_id is None:
            return None
        return self._digests.get(resource_id)

    def list_digests(self) -> list[YouTubeDigestRead]:
        return sorted(
            self._digests.list(),
            key=lambda item: (item.updated_at, item.digest_id),
            reverse=True,
        )

    def save_run(self, run: YouTubeRunRead) -> YouTubeRunRead:
        return self._runs.save(run.run_id, run)

    def get_run(self, run_id: str) -> YouTubeRunRead | None:
        return self._runs.get(run_id)

    def list_runs(
        self,
        *,
        subscription_id: str | None = None,
        video_id: str | None = None,
        kind: YouTubeRunKind | None = None,
    ) -> list[YouTubeRunRead]:
        items = sorted(
            self._runs.list(),
            key=lambda item: (item.created_at, item.run_id),
            reverse=True,
        )
        if subscription_id is not None:
            items = [item for item in items if item.subscription_id == subscription_id]
        if video_id is not None:
            items = [item for item in items if item.video_id == video_id]
        if kind is not None:
            items = [item for item in items if item.kind == kind]
        return items


class SQLiteYouTubeRepository:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._subscriptions = SQLiteModelRepository(
            db_path=db_path,
            table_name="youtube_subscriptions",
            model_cls=YouTubeSubscriptionRead,
        )
        self._videos = SQLiteModelRepository(
            db_path=db_path,
            table_name="youtube_videos",
            model_cls=YouTubeVideoRead,
        )
        self._transcripts = SQLiteModelRepository(
            db_path=db_path,
            table_name="youtube_transcripts",
            model_cls=YouTubeTranscriptRead,
        )
        self._digests = SQLiteModelRepository(
            db_path=db_path,
            table_name="youtube_digests",
            model_cls=YouTubeDigestRead,
        )
        self._runs = SQLiteModelRepository(
            db_path=db_path,
            table_name="youtube_runs",
            model_cls=YouTubeRunRead,
        )
        self._initialize_indexes()

    def save_subscription(self, subscription: YouTubeSubscriptionRead) -> YouTubeSubscriptionRead:
        saved = self._subscriptions.save(subscription.subscription_id, subscription)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_subscription_lookup (normalized_url, subscription_id, status, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(normalized_url) DO UPDATE SET
                    subscription_id = excluded.subscription_id,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    saved.normalized_url,
                    saved.subscription_id,
                    saved.status.value,
                    saved.updated_at.isoformat(),
                ),
            )
            connection.commit()
        return saved

    def get_subscription(self, subscription_id: str) -> YouTubeSubscriptionRead | None:
        return self._subscriptions.get(subscription_id)

    def get_subscription_by_normalized_url(self, normalized_url: str) -> YouTubeSubscriptionRead | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT subscription_id
                FROM youtube_subscription_lookup
                WHERE normalized_url = ?
                """,
                (normalized_url,),
            ).fetchone()
        if row is None:
            return None
        return self._subscriptions.get(row["subscription_id"])

    def list_subscriptions(
        self,
        *,
        status: YouTubeSubscriptionStatus | None = None,
        include_deleted: bool = False,
    ) -> list[YouTubeSubscriptionRead]:
        where_clauses: list[str] = []
        params: list[str] = []
        if status is not None:
            where_clauses.append("status = ?")
            params.append(status.value)
        elif not include_deleted:
            where_clauses.append("status != ?")
            params.append(YouTubeSubscriptionStatus.DELETED.value)
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT subscription_id
                FROM youtube_subscription_lookup
                {where_sql}
                ORDER BY updated_at DESC, subscription_id DESC
                """,
                params,
            ).fetchall()
        items: list[YouTubeSubscriptionRead] = []
        for row in rows:
            subscription = self._subscriptions.get(row["subscription_id"])
            if subscription is not None:
                items.append(subscription)
        return items

    def save_video(self, video: YouTubeVideoRead) -> YouTubeVideoRead:
        saved = self._videos.save(video.video_id, video)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_video_lookup (video_id, subscription_id, source_url, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    subscription_id = excluded.subscription_id,
                    source_url = excluded.source_url,
                    updated_at = excluded.updated_at
                """,
                (saved.video_id, saved.subscription_id, saved.source_url, saved.updated_at.isoformat()),
            )
            connection.commit()
        return saved

    def get_video(self, video_id: str) -> YouTubeVideoRead | None:
        return self._videos.get(video_id)

    def list_videos(self, subscription_id: str | None = None) -> list[YouTubeVideoRead]:
        if subscription_id is None:
            return self._videos.list()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT video_id
                FROM youtube_video_lookup
                WHERE subscription_id = ?
                ORDER BY updated_at DESC, video_id DESC
                """,
                (subscription_id,),
            ).fetchall()
        return [self._videos.get(row["video_id"]) for row in rows if self._videos.get(row["video_id"]) is not None]

    def save_transcript(self, transcript: YouTubeTranscriptRead) -> YouTubeTranscriptRead:
        saved = self._transcripts.save(transcript.transcript_id, transcript)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_transcript_lookup (video_id, transcript_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    transcript_id = excluded.transcript_id,
                    updated_at = excluded.updated_at
                """,
                (saved.video_id, saved.transcript_id, saved.updated_at.isoformat()),
            )
            connection.commit()
        return saved

    def get_transcript(self, transcript_id: str) -> YouTubeTranscriptRead | None:
        return self._transcripts.get(transcript_id)

    def get_transcript_by_video_id(self, video_id: str) -> YouTubeTranscriptRead | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT transcript_id
                FROM youtube_transcript_lookup
                WHERE video_id = ?
                """,
                (video_id,),
            ).fetchone()
        if row is None:
            return None
        return self._transcripts.get(row["transcript_id"])

    def list_transcripts(self) -> list[YouTubeTranscriptRead]:
        return self._transcripts.list()

    def save_digest(self, digest: YouTubeDigestRead) -> YouTubeDigestRead:
        saved = self._digests.save(digest.digest_id, digest)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_digest_lookup (video_id, digest_id, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(video_id) DO UPDATE SET
                    digest_id = excluded.digest_id,
                    updated_at = excluded.updated_at
                """,
                (saved.video_id, saved.digest_id, saved.updated_at.isoformat()),
            )
            connection.commit()
        return saved

    def get_digest(self, digest_id: str) -> YouTubeDigestRead | None:
        return self._digests.get(digest_id)

    def get_digest_by_video_id(self, video_id: str) -> YouTubeDigestRead | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT digest_id
                FROM youtube_digest_lookup
                WHERE video_id = ?
                """,
                (video_id,),
            ).fetchone()
        if row is None:
            return None
        return self._digests.get(row["digest_id"])

    def list_digests(self) -> list[YouTubeDigestRead]:
        return self._digests.list()

    def save_run(self, run: YouTubeRunRead) -> YouTubeRunRead:
        saved = self._runs.save(run.run_id, run)
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO youtube_run_lookup (run_id, kind, subscription_id, video_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    kind = excluded.kind,
                    subscription_id = excluded.subscription_id,
                    video_id = excluded.video_id,
                    updated_at = excluded.updated_at
                """,
                (
                    saved.run_id,
                    saved.kind.value,
                    saved.subscription_id,
                    saved.video_id,
                    saved.created_at.isoformat(),
                    saved.updated_at.isoformat(),
                ),
            )
            connection.commit()
        return saved

    def get_run(self, run_id: str) -> YouTubeRunRead | None:
        return self._runs.get(run_id)

    def list_runs(
        self,
        *,
        subscription_id: str | None = None,
        video_id: str | None = None,
        kind: YouTubeRunKind | None = None,
    ) -> list[YouTubeRunRead]:
        where_clauses: list[str] = []
        params: list[str] = []
        if subscription_id is not None:
            where_clauses.append("subscription_id = ?")
            params.append(subscription_id)
        if video_id is not None:
            where_clauses.append("video_id = ?")
            params.append(video_id)
        if kind is not None:
            where_clauses.append("kind = ?")
            params.append(kind.value)
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT run_id
                FROM youtube_run_lookup
                {where_sql}
                ORDER BY created_at DESC, run_id DESC
                """,
                params,
            ).fetchall()
        items: list[YouTubeRunRead] = []
        for row in rows:
            run = self._runs.get(row["run_id"])
            if run is not None:
                items.append(run)
        return items

    def _initialize_indexes(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_subscription_lookup (
                    normalized_url TEXT PRIMARY KEY,
                    subscription_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    updated_at TEXT NOT NULL DEFAULT '1970-01-01T00:00:00+00:00'
                )
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(youtube_subscription_lookup)").fetchall()
            }
            if "status" not in columns:
                connection.execute(
                    "ALTER TABLE youtube_subscription_lookup ADD COLUMN status TEXT NOT NULL DEFAULT 'active'"
                )
            if "updated_at" not in columns:
                connection.execute(
                    "ALTER TABLE youtube_subscription_lookup ADD COLUMN updated_at TEXT NOT NULL DEFAULT '1970-01-01T00:00:00+00:00'"
                )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_youtube_subscription_lookup_status
                ON youtube_subscription_lookup(status, updated_at)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_video_lookup (
                    video_id TEXT PRIMARY KEY,
                    subscription_id TEXT,
                    source_url TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_youtube_video_lookup_subscription
                ON youtube_video_lookup(subscription_id, updated_at)
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_transcript_lookup (
                    video_id TEXT PRIMARY KEY,
                    transcript_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_digest_lookup (
                    video_id TEXT PRIMARY KEY,
                    digest_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS youtube_run_lookup (
                    run_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    subscription_id TEXT,
                    video_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_youtube_run_lookup_filters
                ON youtube_run_lookup(subscription_id, video_id, kind, created_at)
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
