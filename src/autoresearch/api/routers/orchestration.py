from __future__ import annotations

import inspect

from fastapi import APIRouter, HTTPException, status

from autoresearch.shared.models import (
    PromptOrchestrationExecuteRequest,
    PromptOrchestrationExecutionRead,
    utc_now,
)
from autoresearch.shared.store import create_resource_id

try:  # tests inject both ROOT and SRC into sys.path, runtime may vary by launcher.
    from orchestrator import create_graph_from_prompt
except ModuleNotFoundError:  # pragma: no cover - fallback for direct module execution.
    from src.orchestrator import create_graph_from_prompt


router = APIRouter(prefix="/api/v1/orchestration", tags=["orchestration"])


def _supports_kwarg(func: object, name: str) -> bool:
    try:
        return name in inspect.signature(func).parameters
    except (TypeError, ValueError):
        return False


@router.get("/health")
def orchestration_health() -> dict[str, object]:
    return {
        "status": "ok",
        "entrypoints": ["prompt/execute"],
        "supports": ["goal", "nodes", "retry", "max_steps", "max_concurrency"],
    }


@router.post(
    "/prompt/execute",
    response_model=PromptOrchestrationExecutionRead,
    status_code=status.HTTP_200_OK,
)
async def execute_prompt_orchestration(
    payload: PromptOrchestrationExecuteRequest,
) -> PromptOrchestrationExecutionRead:
    graph_id = payload.graph_id or create_resource_id("graph")
    create_kwargs: dict[str, object] = {
        "goal": payload.goal,
        "graph_id": graph_id,
    }
    if payload.max_concurrency is not None and _supports_kwarg(
        create_graph_from_prompt, "max_concurrency"
    ):
        create_kwargs["max_concurrency"] = payload.max_concurrency
    try:
        graph = create_graph_from_prompt(payload.prompt, **create_kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    for key, value in payload.context.items():
        graph.context.set(key, value)

    started_at = utc_now()
    error: str | None = None
    run_status = "completed"
    execute_kwargs: dict[str, object] = {}
    if payload.max_steps is not None:
        execute_kwargs["max_steps"] = payload.max_steps
    if payload.max_concurrency is not None and _supports_kwarg(graph.execute, "max_concurrency"):
        execute_kwargs["max_concurrency"] = payload.max_concurrency
    try:
        results = await graph.execute(**execute_kwargs)
    except Exception as exc:  # Runtime errors are returned in payload for VS task visibility.
        run_status = "failed"
        results = {}
        error = str(exc)

    finished_at = utc_now()
    duration_seconds = max(0.0, (finished_at - started_at).total_seconds())
    resolved_goal = str(graph.context.get("goal", payload.goal or payload.prompt.strip()))
    resolved_max_steps = int(graph.context.get("orchestration_max_steps", payload.max_steps or 32))
    resolved_max_concurrency = int(
        graph.context.get("orchestration_max_concurrency", payload.max_concurrency or 1)
    )

    response_metadata = {
        "source": "api.orchestration.prompt.execute",
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
    }
    response_metadata.update(payload.metadata)

    return PromptOrchestrationExecutionRead(
        graph_id=graph_id,
        status=run_status,
        goal=resolved_goal,
        max_steps=resolved_max_steps,
        max_concurrency=resolved_max_concurrency,
        started_at=started_at,
        finished_at=finished_at,
        duration_seconds=duration_seconds,
        results=results,
        graph=graph.to_dict() if payload.include_graph else None,
        error=error,
        metadata=response_metadata,
    )
