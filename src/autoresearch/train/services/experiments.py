from __future__ import annotations

from autoresearch.shared.models import ExperimentCreateRequest, ExperimentRead, JobStatus, utc_now
from autoresearch.shared.store import Repository, create_resource_id


class ExperimentService:
    """Placeholder experiment management service."""

    def __init__(self, repository: Repository[ExperimentRead]) -> None:
        self._repository = repository

    def create(self, request: ExperimentCreateRequest) -> ExperimentRead:
        now = utc_now()
        experiment = ExperimentRead(
            experiment_id=create_resource_id("exp"),
            name=request.name,
            problem_statement=request.problem_statement,
            mutable_paths=request.mutable_paths,
            evaluation_command=request.evaluation_command,
            score_direction=request.score_direction,
            status=JobStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
        )
        return self._repository.save(experiment.experiment_id, experiment)

    def list(self) -> list[ExperimentRead]:
        return self._repository.list()

    def get(self, experiment_id: str) -> ExperimentRead | None:
        return self._repository.get(experiment_id)
