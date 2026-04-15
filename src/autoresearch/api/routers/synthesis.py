from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_report_service
from autoresearch.core.services.reports import ReportService
from autoresearch.shared.models import ReportCreateRequest, ReportRead

router = APIRouter(prefix="/api/v1/synthesis", tags=["synthesis"])


@router.post(
    "",
    response_model=ReportRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_synthesis(
    payload: ReportCreateRequest,
    service: ReportService = Depends(get_report_service),
) -> ReportRead:
    return service.create(payload)


@router.get("", response_model=list[ReportRead])
def list_synthesis(
    service: ReportService = Depends(get_report_service),
) -> list[ReportRead]:
    return service.list()


@router.get("/{synthesis_id}", response_model=ReportRead)
def get_synthesis(
    synthesis_id: str,
    service: ReportService = Depends(get_report_service),
) -> ReportRead:
    synthesis = service.get(synthesis_id)
    if synthesis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Synthesis task not found"
        )
    return synthesis
