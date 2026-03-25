from __future__ import annotations

from autoresearch.shared.models import JobStatus, VariantCreateRequest, VariantRead, utc_now
from autoresearch.shared.store import InMemoryRepository, create_resource_id


class VariantService:
    """Placeholder variant generation service."""

    def __init__(self, repository: InMemoryRepository[VariantRead]) -> None:
        self._repository = repository

    def create(self, request: VariantCreateRequest) -> VariantRead:
        now = utc_now()
        variant = VariantRead(
            variant_id=create_resource_id("variant"),
            experiment_id=request.experiment_id,
            status=JobStatus.COMPLETED,
            base_prompt=request.base_prompt,
            strategy_hint=request.strategy_hint,
            content=(
                "Skeleton variant generated. Replace this field with a prompt/program candidate "
                "from the selected generator."
            ),
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
        )
        return self._repository.save(variant.variant_id, variant)

    def list(self) -> list[VariantRead]:
        return self._repository.list()

    def get(self, variant_id: str) -> VariantRead | None:
        return self._repository.get(variant_id)
