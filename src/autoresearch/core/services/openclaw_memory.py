from __future__ import annotations

from typing import Any

from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import (
    ActorRole,
    AssistantScope,
    MemoryScope,
    OpenClawMemoryBundleRead,
    OpenClawMemoryRecordCreateRequest,
    OpenClawMemoryRecordRead,
    OpenClawSessionRead,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


class OpenClawMemoryService:
    """Three-layer memory contract backed by SQLite.

    Session memory stays in the OpenClaw session event log.
    Personal/shared long-term memory is persisted as explicit memory records.
    """

    def __init__(
        self,
        repository: Repository[OpenClawMemoryRecordRead],
        openclaw_service: OpenClawCompatService,
    ) -> None:
        self._repository = repository
        self._openclaw_service = openclaw_service

    def remember_for_session(
        self,
        session_id: str,
        request: OpenClawMemoryRecordCreateRequest,
    ) -> OpenClawMemoryRecordRead:
        session = self._require_session(session_id)
        scope = request.scope or self._default_long_term_scope(session)
        if scope == MemoryScope.SESSION:
            raise ValueError("session scope is event-backed; use personal/shared for long-term memory")

        now = utc_now()
        actor = session.actor
        memory = OpenClawMemoryRecordRead(
            memory_id=create_resource_id("mem"),
            scope=scope,
            content=request.content.strip(),
            source=request.source.strip() or "manual",
            session_id=session.session_id,
            session_key=session.session_key,
            assistant_id=session.assistant_id,
            actor_user_id=actor.user_id if actor is not None else None,
            actor_role=actor.role if actor is not None else ActorRole.UNKNOWN,
            tags=[tag.strip() for tag in request.tags if tag.strip()],
            metadata={
                **request.metadata,
                "session_scope": session.scope.value,
            },
            created_at=now,
            updated_at=now,
        )
        return self._repository.save(memory.memory_id, memory)

    def bundle_for_session(
        self,
        session_id: str,
        *,
        session_event_limit: int = 12,
        long_term_limit: int = 5,
    ) -> OpenClawMemoryBundleRead:
        session = self._require_session(session_id)
        records = self._repository.list()

        personal_memories: list[OpenClawMemoryRecordRead] = []
        shared_memories: list[OpenClawMemoryRecordRead] = []
        actor_user_id = session.actor.user_id if session.actor is not None else None
        assistant_id = session.assistant_id

        for record in records:
            if record.scope == MemoryScope.PERSONAL and actor_user_id and record.actor_user_id == actor_user_id:
                personal_memories.append(record)
            elif record.scope == MemoryScope.SHARED and assistant_id and record.assistant_id == assistant_id:
                shared_memories.append(record)

        return OpenClawMemoryBundleRead(
            session_id=session.session_id,
            session_scope=session.scope,
            session_key=session.session_key,
            assistant_id=session.assistant_id,
            actor_user_id=actor_user_id,
            session_events=list(session.events[-max(1, session_event_limit):]),
            personal_memories=personal_memories[: max(1, long_term_limit)],
            shared_memories=shared_memories[: max(1, long_term_limit)],
        )

    def _require_session(self, session_id: str) -> OpenClawSessionRead:
        session = self._openclaw_service.get_session(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        return session

    def _default_long_term_scope(self, session: OpenClawSessionRead) -> MemoryScope:
        if session.scope == AssistantScope.SHARED:
            return MemoryScope.SHARED
        return MemoryScope.PERSONAL
