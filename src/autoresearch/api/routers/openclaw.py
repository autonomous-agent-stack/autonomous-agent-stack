from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from autoresearch.api.settings import load_feature_settings
from autoresearch.api.dependencies import (
    get_claude_agent_service,
    get_mirofish_prediction_service,
    get_openclaw_compat_service,
    get_openclaw_memory_service,
    get_openclaw_skill_service,
)
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.mirofish_prediction import MiroFishPredictionService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from autoresearch.shared.models import (
    ClaudeAgentCancelRequest,
    ClaudeAgentCreateRequest,
    ClaudeAgentRetryRequest,
    ClaudeAgentRunRead,
    ClaudeAgentTreeRead,
    MiroFishPredictionRead,
    MiroFishPredictionRequest,
    OpenClawMemoryBundleRead,
    OpenClawMemoryRecordCreateRequest,
    OpenClawMemoryRecordRead,
    OpenClawSessionSkillLoadRequest,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSkillDetailRead,
    OpenClawSkillRead,
    OpenClawSessionRead,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OpenClaw session not found"
        )
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


@router.get("/sessions/{session_id}/memory", response_model=OpenClawMemoryBundleRead)
def get_session_memory(
    session_id: str,
    session_event_limit: int = 12,
    long_term_limit: int = 5,
    service: OpenClawMemoryService = Depends(get_openclaw_memory_service),
) -> OpenClawMemoryBundleRead:
    try:
        return service.bundle_for_session(
            session_id=session_id,
            session_event_limit=max(1, min(session_event_limit, 100)),
            long_term_limit=max(1, min(long_term_limit, 50)),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OpenClaw session not found",
        ) from exc


@router.post(
    "/sessions/{session_id}/memory",
    response_model=OpenClawMemoryRecordRead,
    status_code=status.HTTP_201_CREATED,
)
def remember_for_session(
    session_id: str,
    payload: OpenClawMemoryRecordCreateRequest,
    service: OpenClawMemoryService = Depends(get_openclaw_memory_service),
) -> OpenClawMemoryRecordRead:
    try:
        return service.remember_for_session(session_id=session_id, request=payload)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OpenClaw session not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/skills", response_model=list[OpenClawSkillRead])
def list_openclaw_skills(
    service: OpenClawSkillService = Depends(get_openclaw_skill_service),
) -> list[OpenClawSkillRead]:
    return service.list_skills()


@router.get("/skills/{skill_name}", response_model=OpenClawSkillDetailRead)
def get_openclaw_skill(
    skill_name: str,
    service: OpenClawSkillService = Depends(get_openclaw_skill_service),
) -> OpenClawSkillDetailRead:
    skill = service.get_skill(skill_name)
    if skill is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OpenClaw skill not found"
        )
    return skill


@router.post("/sessions/{session_id}/skills", response_model=OpenClawSessionRead)
def load_session_skills(
    session_id: str,
    payload: OpenClawSessionSkillLoadRequest,
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
    skill_service: OpenClawSkillService = Depends(get_openclaw_skill_service),
) -> OpenClawSessionRead:
    session = openclaw_service.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="OpenClaw session not found"
        )

    resolved, missing = skill_service.resolve_skill_names(payload.skill_names)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OpenClaw skills not found: {', '.join(missing)}",
        )

    requested = [skill.name for skill in resolved]
    if payload.merge:
        existing = _normalize_skill_name_list(session.metadata.get("loaded_skill_names"))
        existing_lower = {item.lower() for item in existing}
        merged = existing + [name for name in requested if name.lower() not in existing_lower]
    else:
        merged = requested

    try:
        updated = openclaw_service.update_metadata(
            session_id=session_id,
            metadata_updates={
                "loaded_skill_names": merged,
                "loaded_skill_count": len(merged),
                "loaded_skill_sources": [skill.source for skill in resolved],
            },
        )
        openclaw_service.append_event(
            session_id=session_id,
            request=OpenClawSessionEventAppendRequest(
                role="status",
                content=f"skills loaded: {', '.join(merged)}",
                metadata={
                    "loaded_skill_names": merged,
                },
            ),
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OpenClaw session not found",
        ) from exc
    return updated


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Claude agent run not found"
        )
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Claude agent run not found"
        ) from exc


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Claude agent run not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    background_tasks.add_task(service.execute, replay_run.agent_run_id, replay_request)
    return replay_run


def _normalize_skill_name_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, str):
            continue
        value = item.strip()
        if not value:
            continue
        lowered = value.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        normalized.append(value)
    return normalized


def _prediction_gate_enabled() -> bool:
    return load_feature_settings().enable_mirofish_gate


def _prediction_min_confidence() -> float:
    value = load_feature_settings().mirofish_min_confidence
    return max(0.0, min(value, 1.0))
