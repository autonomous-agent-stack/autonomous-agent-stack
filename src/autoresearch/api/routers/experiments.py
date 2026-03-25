from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_experiment_service
from autoresearch.shared.models import ExperimentCreateRequest, ExperimentRead
from autoresearch.train.services.experiments import ExperimentService


router = APIRouter(prefix="/api/v1/experiments", tags=["experiments"])


@router.post(
    "",
    response_model=ExperimentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_experiment(
    payload: ExperimentCreateRequest,
    service: ExperimentService = Depends(get_experiment_service),
) -> ExperimentRead:
    return service.create(payload)


@router.get("", response_model=list[ExperimentRead])
def list_experiments(
    service: ExperimentService = Depends(get_experiment_service),
) -> list[ExperimentRead]:
    return service.list()


@router.get("/{experiment_id}", response_model=ExperimentRead)
def get_experiment(
    experiment_id: str,
    service: ExperimentService = Depends(get_experiment_service),
) -> ExperimentRead:
    experiment = service.get(experiment_id)
    if experiment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experiment not found")
    return experiment
