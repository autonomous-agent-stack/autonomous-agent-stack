from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from autoresearch.api.dependencies import get_session_event_service
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.shared.models import SessionEventRead, SessionTimelineRead

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("/{session_id}/events", response_model=list[SessionEventRead])
def list_session_events(
    session_id: str,
    after_event_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    source: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    approval_id: str | None = Query(default=None),
    service: SessionEventService = Depends(get_session_event_service),
) -> list[SessionEventRead]:
    return service.list_events(
        session_id=session_id,
        after_event_id=after_event_id,
        limit=limit,
        source=source,
        run_id=run_id,
        approval_id=approval_id,
    )


@router.get("/{session_id}/timeline", response_model=SessionTimelineRead)
def get_session_timeline(
    session_id: str,
    after_event_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    source: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    approval_id: str | None = Query(default=None),
    service: SessionEventService = Depends(get_session_event_service),
) -> SessionTimelineRead:
    return service.timeline(
        session_id=session_id,
        after_event_id=after_event_id,
        limit=limit,
        source=source,
        run_id=run_id,
        approval_id=approval_id,
    )
