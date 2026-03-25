from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from autoresearch.api.dependencies import get_evaluation_service
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.shared.models import EvaluationCreateRequest, EvaluationRead


router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


@router.post(
    "",
    response_model=EvaluationRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_evaluation(
    payload: EvaluationCreateRequest,
    background_tasks: BackgroundTasks,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRead:
    evaluation = service.create(payload)
    background_tasks.add_task(service.execute, evaluation.evaluation_id, payload)
    return evaluation


@router.get("", response_model=list[EvaluationRead])
def list_evaluations(
    service: EvaluationService = Depends(get_evaluation_service),
) -> list[EvaluationRead]:
    return service.list()


@router.get("/{evaluation_id}", response_model=EvaluationRead)
def get_evaluation(
    evaluation_id: str,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationRead:
    evaluation = service.get(evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    return evaluation
