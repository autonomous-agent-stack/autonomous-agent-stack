from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from autoresearch.api.dependencies import get_execution_service
from autoresearch.core.services.executions import ExecutionService
from autoresearch.shared.models import ExecutionCreateRequest, ExecutionRead


router = APIRouter(prefix="/api/v1/executors", tags=["executors"])


@router.post(
    "",
    response_model=ExecutionRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_executor_task(
    payload: ExecutionCreateRequest,
    background_tasks: BackgroundTasks,
    service: ExecutionService = Depends(get_execution_service),
) -> ExecutionRead:
    execution = service.create(payload)
    background_tasks.add_task(service.execute, execution.execution_id, payload)
    return execution


@router.get("", response_model=list[ExecutionRead])
def list_executor_tasks(
    service: ExecutionService = Depends(get_execution_service),
) -> list[ExecutionRead]:
    return service.list()


@router.get("/{execution_id}", response_model=ExecutionRead)
def get_executor_task(
    execution_id: str,
    service: ExecutionService = Depends(get_execution_service),
) -> ExecutionRead:
    execution = service.get(execution_id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution task not found")
    return execution
