from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from autoresearch.agent_protocol.runtime_models import (
    RuntimeCancelRead,
    RuntimeCancelRequest,
    RuntimeRunRead,
    RuntimeRunRequest,
    RuntimeSessionCreateRequest,
    RuntimeSessionRead,
    RuntimeStatusRead,
    RuntimeStatusRequest,
    RuntimeStreamEvent,
    RuntimeStreamRequest,
)
from autoresearch.api.dependencies import get_runtime_adapter_registry_service
from autoresearch.core.services.runtime_adapter_contract import RuntimeAdapterContract
from autoresearch.core.services.runtime_adapter_registry import RuntimeAdapterServiceRegistry

router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"])


def _resolve_runtime_adapter(
    runtime_id: str,
    registry: RuntimeAdapterServiceRegistry = Depends(get_runtime_adapter_registry_service),
) -> RuntimeAdapterContract:
    try:
        return registry.get(runtime_id)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post("/{runtime_id}/sessions", response_model=RuntimeSessionRead, status_code=status.HTTP_201_CREATED)
def create_runtime_session(
    runtime_id: str,
    payload: RuntimeSessionCreateRequest,
    adapter: RuntimeAdapterContract = Depends(_resolve_runtime_adapter),
) -> RuntimeSessionRead:
    try:
        request = payload.model_copy(update={"runtime_id": runtime_id})
        return adapter.create_session(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{runtime_id}/runs", response_model=RuntimeRunRead, status_code=status.HTTP_201_CREATED)
def run_runtime_task(
    runtime_id: str,
    payload: RuntimeRunRequest,
    adapter: RuntimeAdapterContract = Depends(_resolve_runtime_adapter),
) -> RuntimeRunRead:
    try:
        request = payload.model_copy(update={"runtime_id": runtime_id})
        return adapter.run(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{runtime_id}/sessions/{session_id}/events", response_model=list[RuntimeStreamEvent])
def stream_runtime_events(
    runtime_id: str,
    session_id: str,
    after_event_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    adapter: RuntimeAdapterContract = Depends(_resolve_runtime_adapter),
) -> list[RuntimeStreamEvent]:
    try:
        return adapter.stream(
            RuntimeStreamRequest(
                runtime_id=runtime_id,
                session_id=session_id,
                after_event_id=after_event_id,
                limit=limit,
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{runtime_id}/status", response_model=RuntimeStatusRead)
def get_runtime_status(
    runtime_id: str,
    run_id: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    event_limit: int = Query(default=20, ge=1, le=200),
    adapter: RuntimeAdapterContract = Depends(_resolve_runtime_adapter),
) -> RuntimeStatusRead:
    try:
        return adapter.status(
            RuntimeStatusRequest(
                runtime_id=runtime_id,
                run_id=run_id,
                session_id=session_id,
                event_limit=event_limit,
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{runtime_id}/runs/{run_id}/cancel", response_model=RuntimeCancelRead)
def cancel_runtime_run(
    runtime_id: str,
    run_id: str,
    payload: RuntimeCancelRequest,
    adapter: RuntimeAdapterContract = Depends(_resolve_runtime_adapter),
) -> RuntimeCancelRead:
    try:
        request = payload.model_copy(update={"runtime_id": runtime_id, "run_id": run_id})
        return adapter.cancel(request)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
