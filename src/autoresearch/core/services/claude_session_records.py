"""Sticky session records for claude_runtime worker tasks.

Binds a session_key to a specific worker_id / project_dir / claude_home
so that consecutive requests for the same session hit the same runtime
environment, enabling stateful CLI session resumption later.
"""
from __future__ import annotations

import logging
from typing import Protocol

from autoresearch.shared.models import ClaudeRuntimeSessionRecordRead, utc_now
from autoresearch.shared.store import Repository

logger = logging.getLogger(__name__)


class ClaudeSessionRecordService:
    """Read/write sticky session records backed by a generic repository."""

    def __init__(self, repository: Repository[ClaudeRuntimeSessionRecordRead]) -> None:
        self._repo = repository

    def get_by_session_key(self, session_key: str) -> ClaudeRuntimeSessionRecordRead | None:
        return self._repo.get(session_key)

    def upsert(
        self,
        *,
        session_key: str,
        worker_id: str | None = None,
        project_dir: str | None = None,
        claude_home: str | None = None,
        latest_session_ref: str | None = None,
        last_summary: str | None = None,
        metadata: dict | None = None,
    ) -> ClaudeRuntimeSessionRecordRead:
        existing = self._repo.get(session_key)
        now = utc_now()
        if existing is None:
            record = ClaudeRuntimeSessionRecordRead(
                session_key=session_key,
                worker_id=worker_id,
                project_dir=project_dir,
                claude_home=claude_home,
                latest_session_ref=latest_session_ref,
                last_summary=last_summary,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )
        else:
            record = existing.model_copy(update={
                k: v
                for k, v in {
                    "worker_id": worker_id,
                    "project_dir": project_dir,
                    "claude_home": claude_home,
                    "latest_session_ref": latest_session_ref,
                    "last_summary": last_summary,
                    "updated_at": now,
                    "metadata": {**existing.metadata, **(metadata or {})},
                }.items()
                if v is not None
            })
        return self._repo.save(session_key, record)

    def bind_session_to_worker(
        self,
        *,
        session_key: str,
        worker_id: str,
        project_dir: str | None = None,
        claude_home: str | None = None,
    ) -> ClaudeRuntimeSessionRecordRead:
        return self.upsert(
            session_key=session_key,
            worker_id=worker_id,
            project_dir=project_dir,
            claude_home=claude_home,
        )

    def update_latest(
        self,
        *,
        session_key: str,
        latest_session_ref: str | None = None,
        last_summary: str | None = None,
    ) -> ClaudeRuntimeSessionRecordRead:
        return self.upsert(
            session_key=session_key,
            latest_session_ref=latest_session_ref,
            last_summary=last_summary,
        )
