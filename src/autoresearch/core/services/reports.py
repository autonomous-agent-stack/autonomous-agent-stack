from __future__ import annotations

from autoresearch.shared.models import JobStatus, ReportCreateRequest, ReportRead, utc_now
from autoresearch.shared.store import Repository, create_resource_id


class ReportService:
    """Placeholder report generation service."""

    def __init__(self, repository: Repository[ReportRead]) -> None:
        self._repository = repository

    def create(self, request: ReportCreateRequest) -> ReportRead:
        now = utc_now()
        report = ReportRead(
            report_id=create_resource_id("report"),
            evaluation_id=request.evaluation_id,
            experiment_id=request.experiment_id,
            status=JobStatus.COMPLETED,
            format=request.format,
            content=(
                "# Report Placeholder\n\n"
                "This skeleton route is live. Replace this content with GPT Researcher-backed "
                "report generation."
            ),
            sections=request.sections,
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
        )
        return self._repository.save(report.report_id, report)

    def list(self) -> list[ReportRead]:
        return self._repository.list()

    def get(self, report_id: str) -> ReportRead | None:
        return self._repository.get(report_id)
