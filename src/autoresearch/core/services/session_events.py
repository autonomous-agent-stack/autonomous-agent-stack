from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from autoresearch.shared.models import (
    SessionEventCreateRequest,
    SessionEventRead,
    SessionTimelineRead,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


class SessionEventService:
    """Append-only canonical timeline for sessions and correlated product objects."""

    def __init__(self, repository: Repository[SessionEventRead]) -> None:
        self._repository = repository

    def append(self, request: SessionEventCreateRequest) -> SessionEventRead:
        idempotency_key = _clean_optional(request.idempotency_key)
        if idempotency_key:
            existing = self._find_by_idempotency_key(idempotency_key)
            if existing is not None:
                return existing

        event = SessionEventRead(
            event_id=create_resource_id("sev"),
            session_id=request.session_id.strip(),
            source=request.source.strip(),
            event_type=request.event_type.strip(),
            role=request.role,
            content=request.content.strip(),
            status=_clean_optional(request.status),
            runtime_id=_clean_optional(request.runtime_id),
            run_id=_clean_optional(request.run_id),
            approval_id=_clean_optional(request.approval_id),
            worker_id=_clean_optional(request.worker_id),
            external_event_id=_clean_optional(request.external_event_id),
            idempotency_key=idempotency_key,
            metadata=dict(request.metadata),
            created_at=utc_now(),
        )
        return self._repository.save(event.event_id, event)

    def list_events(
        self,
        *,
        session_id: str,
        after_event_id: str | None = None,
        limit: int = 100,
        source: str | None = None,
        run_id: str | None = None,
        approval_id: str | None = None,
    ) -> list[SessionEventRead]:
        normalized_session_id = session_id.strip()
        normalized_source = _clean_optional(source)
        normalized_run_id = _clean_optional(run_id)
        normalized_approval_id = _clean_optional(approval_id)
        events = [
            event
            for event in self._repository.list()
            if event.session_id == normalized_session_id
            and (normalized_source is None or event.source == normalized_source)
            and (normalized_run_id is None or event.run_id == normalized_run_id)
            and (normalized_approval_id is None or event.approval_id == normalized_approval_id)
        ]
        events.sort(key=lambda item: (item.created_at, item.event_id))
        if after_event_id:
            after_index = next(
                (idx for idx, item in enumerate(events) if item.event_id == after_event_id),
                None,
            )
            if after_index is not None:
                events = events[after_index + 1 :]
        return events[: max(1, min(int(limit), 1000))]

    def timeline(
        self,
        *,
        session_id: str,
        after_event_id: str | None = None,
        limit: int = 100,
        source: str | None = None,
        run_id: str | None = None,
        approval_id: str | None = None,
    ) -> SessionTimelineRead:
        events = self.list_events(
            session_id=session_id,
            after_event_id=after_event_id,
            limit=limit,
            source=source,
            run_id=run_id,
            approval_id=approval_id,
        )
        latest = events[-1] if events else None
        correlations = {
            "run_ids": _ordered_unique(event.run_id for event in events),
            "approval_ids": _ordered_unique(event.approval_id for event in events),
            "worker_ids": _ordered_unique(event.worker_id for event in events),
            "runtime_ids": _ordered_unique(event.runtime_id for event in events),
            "sources": _ordered_unique(event.source for event in events),
        }
        return SessionTimelineRead(
            session_id=session_id.strip(),
            events=events,
            latest_event=latest,
            summary={
                "event_count": len(events),
                "first_event_id": events[0].event_id if events else None,
                "latest_event_id": latest.event_id if latest else None,
                "latest_status": latest.status if latest else None,
            },
            correlations=correlations,
        )

    def _find_by_idempotency_key(self, idempotency_key: str) -> SessionEventRead | None:
        for event in self._repository.list():
            if event.idempotency_key == idempotency_key:
                return event
        return None


def resolve_session_id_from_payload(metadata: dict[str, Any] | None, payload: dict[str, Any] | None) -> str | None:
    """Resolve the V1 canonical session id from existing metadata/payload conventions."""
    metadata = dict(metadata or {})
    payload = dict(payload or {})
    candidates = [
        metadata.get("aas_session_id"),
        metadata.get("session_id"),
        payload.get("session_id"),
    ]
    payload_metadata = payload.get("metadata")
    if isinstance(payload_metadata, dict):
        candidates.append(payload_metadata.get("session_id"))
    for value in candidates:
        normalized = _clean_optional(value)
        if normalized:
            return normalized
    return None


def _clean_optional(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _ordered_unique(values: Iterable[object]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = _clean_optional(value)
        if normalized is None or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out
