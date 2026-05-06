from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_a2a_gateway_service
from autoresearch.core.services.a2a_gateway import (
    A2AAgentCard,
    A2AGatewayService,
    A2ATaskCreateRequest,
    A2ATaskRead,
)


router = APIRouter(prefix="/api/v1/a2a", tags=["a2a"])


@router.get("/agent-card", response_model=A2AAgentCard)
def get_agent_card(
    service: A2AGatewayService = Depends(get_a2a_gateway_service),
) -> A2AAgentCard:
    return service.agent_card()


@router.post("/tasks", response_model=A2ATaskRead, status_code=status.HTTP_201_CREATED)
def create_a2a_task(
    payload: A2ATaskCreateRequest,
    service: A2AGatewayService = Depends(get_a2a_gateway_service),
) -> A2ATaskRead:
    return service.submit_task(payload)


@router.get("/tasks/{task_id}", response_model=A2ATaskRead)
def get_a2a_task(
    task_id: str,
    service: A2AGatewayService = Depends(get_a2a_gateway_service),
) -> A2ATaskRead:
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="A2A task not found")
    return task
