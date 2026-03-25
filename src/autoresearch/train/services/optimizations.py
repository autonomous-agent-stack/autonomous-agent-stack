from __future__ import annotations

from autoresearch.shared.models import JobStatus, OptimizationCreateRequest, OptimizationRead, utc_now
from autoresearch.shared.store import InMemoryRepository, create_resource_id


class OptimizationService:
    """Placeholder optimizer orchestration service."""

    def __init__(self, repository: InMemoryRepository[OptimizationRead]) -> None:
        self._repository = repository

    def create(self, request: OptimizationCreateRequest) -> OptimizationRead:
        now = utc_now()
        optimization = OptimizationRead(
            optimization_id=create_resource_id("opt"),
            experiment_id=request.experiment_id,
            objective=request.objective,
            strategy=request.strategy,
            max_iterations=request.max_iterations,
            early_stop_patience=request.early_stop_patience,
            rollback_on_regression=request.rollback_on_regression,
            status=JobStatus.QUEUED,
            best_variant_id=None,
            best_score=None,
            last_score=None,
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
        )
        return self._repository.save(optimization.optimization_id, optimization)

    def list(self) -> list[OptimizationRead]:
        return self._repository.list()

    def get(self, optimization_id: str) -> OptimizationRead | None:
        return self._repository.get(optimization_id)
