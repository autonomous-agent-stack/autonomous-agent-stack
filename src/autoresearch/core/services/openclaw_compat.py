from __future__ import annotations

from typing import Any

from autoresearch.shared.models import (
    JobStatus,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSessionRead,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


class OpenClawCompatService:
    """Minimal OpenClaw-compatible session memory service backed by SQLiteModelRepository."""

    def __init__(self, repository: Repository[OpenClawSessionRead]) -> None:
        self._repository = repository

    def create_session(self, request: OpenClawSessionCreateRequest) -> OpenClawSessionRead:
        now = utc_now()
        session = OpenClawSessionRead(
            session_id=create_resource_id("oc"),
            channel=request.channel,
            external_id=request.external_id,
            title=request.title,
            status=JobStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
            events=[],
            error=None,
        )
        return self._repository.save(session.session_id, session)

    def list_sessions(self) -> list[OpenClawSessionRead]:
        return self._repository.list()

    def get_session(self, session_id: str) -> OpenClawSessionRead | None:
        return self._repository.get(session_id)

    def save_session(self, session: OpenClawSessionRead) -> OpenClawSessionRead:
        return self._repository.save(session.session_id, session)

    def find_session(self, channel: str, external_id: str) -> OpenClawSessionRead | None:
        normalized_external_id = external_id.strip()
        if not normalized_external_id:
            return None
        for session in self.list_sessions():
            if session.channel != channel:
                continue
            if session.external_id == normalized_external_id:
                return session
        return None

    def append_event(
        self,
        session_id: str,
        request: OpenClawSessionEventAppendRequest,
    ) -> OpenClawSessionRead:
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")

        event = {
            "event_id": create_resource_id("evt"),
            "role": request.role,
            "content": request.content,
            "metadata": request.metadata,
            "created_at": utc_now().isoformat(),
        }
        events = list(session.events)
        events.append(event)
        updated = session.model_copy(
            update={
                "events": events,
                "updated_at": utc_now(),
            }
        )
        return self._repository.save(updated.session_id, updated)

    def set_status(
        self,
        session_id: str,
        status: JobStatus,
        error: str | None = None,
        metadata_updates: dict[str, Any] | None = None,
    ) -> OpenClawSessionRead:
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        updated_metadata = dict(session.metadata)
        if metadata_updates:
            updated_metadata.update(metadata_updates)

        updated = session.model_copy(
            update={
                "status": status,
                "updated_at": utc_now(),
                "error": error,
                "metadata": updated_metadata,
            }
        )
        return self._repository.save(updated.session_id, updated)

    def update_metadata(
        self,
        session_id: str,
        metadata_updates: dict[str, Any],
    ) -> OpenClawSessionRead:
        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        updated_metadata = dict(session.metadata)
        updated_metadata.update(metadata_updates)
        updated = session.model_copy(
            update={
                "metadata": updated_metadata,
                "updated_at": utc_now(),
            }
        )
        return self._repository.save(updated.session_id, updated)
