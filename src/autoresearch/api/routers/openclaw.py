from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from autoresearch.api.dependencies import (
    get_claude_agent_service,
    get_mirofish_prediction_service,
    get_openclaw_compat_service,
    get_openviking_memory_service,
)
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.mirofish_prediction import MiroFishPredictionService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openviking_memory import OpenVikingMemoryService
from autoresearch.shared.models import (
    ClaudeAgentCancelRequest,
    ClaudeAgentCreateRequest,
    ClaudeAgentRetryRequest,
    ClaudeAgentRunRead,
    ClaudeAgentTreeRead,
    MiroFishPredictionRead,
    MiroFishPredictionRequest,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSessionRead,
    OpenVikingCompactRequest,
    OpenVikingMemoryProfileRead,
)


router = APIRouter(prefix="/api/v1/openclaw", tags=["openclaw-compat"])


@router.post(
    "/sessions",
    response_model=OpenClawSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    payload: OpenClawSessionCreateRequest,
    service: OpenClawCompatService = Depends(get_openclaw_compat_service),
) -> OpenClawSessionRead:
    return service.create_session(payload)


@router.get("/sessions", response_model=list[OpenClawSessionRead])
def list_sessions(
    service: OpenClawCompatService = Depends(get_openclaw_compat_service),
) -> list[OpenClawSessionRead]:
    return service.list_sessions()


@router.get("/sessions/{session_id}", response_model=OpenClawSessionRead)
def get_session(
    session_id: str,
    service: OpenClawCompatService = Depends(get_openclaw_compat_service),
) -> OpenClawSessionRead:
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OpenClaw session not found")
    return session


@router.post("/sessions/{session_id}/events", response_model=OpenClawSessionRead)
def append_session_event(
    session_id: str,
    payload: OpenClawSessionEventAppendRequest,
    service: OpenClawCompatService = Depends(get_openclaw_compat_service),
) -> OpenClawSessionRead:
    try:
        return service.append_event(session_id=session_id, request=payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OpenClaw session not found",
        ) from exc


@router.post("/sessions/{session_id}/compact", response_model=OpenVikingMemoryProfileRead)
def compact_session_memory(
    session_id: str,
    payload: OpenVikingCompactRequest,
    service: OpenVikingMemoryService = Depends(get_openviking_memory_service),
) -> OpenVikingMemoryProfileRead:
    try:
        _, profile = service.compact_session(session_id=session_id, request=payload)
        return profile
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OpenClaw session not found") from exc


@router.get("/sessions/{session_id}/memory-profile", response_model=OpenVikingMemoryProfileRead)
def get_session_memory_profile(
    session_id: str,
    service: OpenVikingMemoryService = Depends(get_openviking_memory_service),
) -> OpenVikingMemoryProfileRead:
    try:
        return service.memory_profile(session_id=session_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OpenClaw session not found") from exc


@router.post(
    "/agents",
    response_model=ClaudeAgentRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def spawn_claude_agent(
    payload: ClaudeAgentCreateRequest,
    background_tasks: BackgroundTasks,
    service: ClaudeAgentService = Depends(get_claude_agent_service),
    prediction_service: MiroFishPredictionService = Depends(get_mirofish_prediction_service),
) -> ClaudeAgentRunRead:
    enriched_payload = payload
    if _prediction_gate_enabled():
        prediction = prediction_service.evaluate_agent_request(payload)
        threshold = _prediction_min_confidence()
        if prediction.decision == "reject" or prediction.score < threshold:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": "blocked by mirofish prediction gate",
                    "prediction": prediction.model_dump(mode="json"),
                    "threshold": threshold,
                },
            )
        enriched_payload = payload.model_copy(
            update={
                "metadata": {
                    **payload.metadata,
                    "mirofish_prediction": prediction.model_dump(mode="json"),
                }
            }
        )

    try:
        agent_run = service.create(enriched_payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    background_tasks.add_task(service.execute, agent_run.agent_run_id, enriched_payload)
    return agent_run


@router.get("/agents", response_model=list[ClaudeAgentRunRead])
def list_claude_agents(
    service: ClaudeAgentService = Depends(get_claude_agent_service),
) -> list[ClaudeAgentRunRead]:
    return service.list()


@router.get("/agents/tree", response_model=ClaudeAgentTreeRead)
def get_claude_agent_tree(
    session_id: str | None = None,
    service: ClaudeAgentService = Depends(get_claude_agent_service),
) -> ClaudeAgentTreeRead:
    return service.build_task_tree(session_id=session_id)


@router.post("/predictions", response_model=MiroFishPredictionRead)
def evaluate_prediction(
    payload: MiroFishPredictionRequest,
    service: MiroFishPredictionService = Depends(get_mirofish_prediction_service),
) -> MiroFishPredictionRead:
    return service.evaluate(payload)


@router.get("/agents/{agent_run_id}", response_model=ClaudeAgentRunRead)
def get_claude_agent(
    agent_run_id: str,
    service: ClaudeAgentService = Depends(get_claude_agent_service),
) -> ClaudeAgentRunRead:
    run = service.get(agent_run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claude agent run not found")
    return run


@router.post("/agents/{agent_run_id}/cancel", response_model=ClaudeAgentRunRead)
def cancel_claude_agent(
    agent_run_id: str,
    payload: ClaudeAgentCancelRequest,
    service: ClaudeAgentService = Depends(get_claude_agent_service),
) -> ClaudeAgentRunRead:
    try:
        return service.cancel(agent_run_id=agent_run_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claude agent run not found") from exc


@router.post(
    "/agents/{agent_run_id}/retry",
    response_model=ClaudeAgentRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def retry_claude_agent(
    agent_run_id: str,
    payload: ClaudeAgentRetryRequest,
    background_tasks: BackgroundTasks,
    service: ClaudeAgentService = Depends(get_claude_agent_service),
) -> ClaudeAgentRunRead:
    try:
        replay_run, replay_request = service.retry(agent_run_id=agent_run_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claude agent run not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    background_tasks.add_task(service.execute, replay_run.agent_run_id, replay_request)
    return replay_run


def _prediction_gate_enabled() -> bool:
    raw = os.getenv("AUTORESEARCH_MIROFISH_ENABLED")
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _prediction_min_confidence() -> float:
    raw = os.getenv("AUTORESEARCH_MIROFISH_MIN_CONFIDENCE", "0.35").strip()
    try:
        value = float(raw)
    except ValueError:
        return 0.35
    return max(0.0, min(1.0, value))
