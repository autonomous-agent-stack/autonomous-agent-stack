from __future__ import annotations

import logging
from typing import Any

from autoresearch.core.services.session_events import SessionEventService
from autoresearch.shared.models import (
    JobStatus,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSessionRead,
    SessionEventCreateRequest,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id

logger = logging.getLogger(__name__)


class OpenClawCompatService:
    """Minimal OpenClaw-compatible session memory service backed by SQLiteModelRepository."""

    def __init__(
        self,
        repository: Repository[OpenClawSessionRead],
        session_events: SessionEventService | None = None,
    ) -> None:
        self._repository = repository
        self._session_events = session_events

    def create_session(self, request: OpenClawSessionCreateRequest) -> OpenClawSessionRead:
        now = utc_now()
        session = OpenClawSessionRead(
            session_id=create_resource_id("oc"),
            channel=request.channel,
            external_id=request.external_id,
            title=request.title,
            scope=request.scope,
            session_key=request.session_key,
            assistant_id=request.assistant_id,
            actor=request.actor,
            chat_context=request.chat_context,
            status=JobStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
            events=[],
            error=None,
        )
        saved = self._repository.save(session.session_id, session)
        self._append_session_event(
            SessionEventCreateRequest(
                session_id=saved.session_id,
                source="openclaw",
                event_type="session.created",
                role="status",
                content=f"session created: {saved.session_id}",
                status=saved.status.value,
                idempotency_key=f"openclaw:{saved.session_id}:created",
                metadata={
                    "channel": saved.channel,
                    "external_id": saved.external_id,
                    "title": saved.title,
                    "session_key": saved.session_key,
                    "assistant_id": saved.assistant_id,
                },
            )
        )
        return saved

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

    def find_session_by_key(self, channel: str, session_key: str) -> OpenClawSessionRead | None:
        normalized_session_key = session_key.strip()
        if not normalized_session_key:
            return None
        for session in self.list_sessions():
            if session.channel != channel:
                continue
            if session.session_key == normalized_session_key:
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
        saved = self._repository.save(updated.session_id, updated)
        self._append_session_event(
            SessionEventCreateRequest(
                session_id=saved.session_id,
                source="openclaw",
                event_type="session.event_appended",
                role=request.role,
                content=request.content,
                status=saved.status.value,
                runtime_id=_string_or_none(request.metadata.get("runtime_id")),
                run_id=_string_or_none(
                    request.metadata.get("run_id") or request.metadata.get("agent_run_id")
                ),
                approval_id=_string_or_none(request.metadata.get("approval_id")),
                worker_id=_string_or_none(request.metadata.get("worker_id")),
                external_event_id=str(event["event_id"]),
                idempotency_key=f"openclaw:{saved.session_id}:event:{event['event_id']}",
                metadata=dict(request.metadata),
            )
        )
        return saved

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
        saved = self._repository.save(updated.session_id, updated)
        self._append_session_event(
            SessionEventCreateRequest(
                session_id=saved.session_id,
                source="openclaw",
                event_type="session.status_changed",
                role="status",
                content=f"session status: {status.value}",
                status=status.value,
                run_id=_string_or_none(updated_metadata.get("latest_agent_run_id")),
                metadata={
                    "error": error,
                    **dict(metadata_updates or {}),
                },
            )
        )
        return saved

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

    def _append_session_event(self, request: SessionEventCreateRequest) -> None:
        if self._session_events is None:
            return
        try:
            self._session_events.append(request)
        except Exception:
            logger.warning("Failed to append canonical session event", exc_info=True)


def _string_or_none(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
