"""
Excel Operations Router - API endpoints for Excel processing

Provides REST API for:
- Job creation and management
- Commission calculation requests
- Validation operations
- Requirement #4 status queries

IMPORTANT: This is a scaffold. Actual business logic will be implemented
when requirement #4 business assets arrive.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.shared.excel_ops_models import (
    CommissionCalculationRequest,
    CommissionCalculationResponse,
    ExcelJobCreateRequest,
    ExcelJobRead,
    ExcelJobStatusResponse,
    ExcelValidationRequest,
    ExcelValidationResult,
    Requirement4StatusResponse,
)
from autoresearch.core.services.excel_ops import ExcelOpsService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/excel-ops",
    tags=["excel-ops"],
)


async def get_excel_ops_service() -> ExcelOpsService:
    """
    Dependency injection for ExcelOpsService.

    TODO: Wire up real service instance with repository and engine.
    For now, raise explicit error indicating scaffold status.
    """
    # This is a scaffold - service will be wired up in dependencies.py
    # when business assets arrive
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=(
            "Excel operations service is not yet wired up. "
            "This is a scaffold implementation awaiting requirement #4 "
            "business assets. See docs/requirement4/ for details."
        ),
    )


@router.post(
    "/jobs",
    response_model=ExcelJobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Excel processing job",
    description=(
        "Create a new Excel processing job. "
        "Input file roles will be defined by business-provided contracts."
    ),
)
def create_job(
    request: ExcelJobCreateRequest,
    service: ExcelOpsService = Depends(get_excel_ops_service),
) -> ExcelJobRead:
    """
    Create a new Excel processing job.

    Currently accepts jobs but blocks actual processing until
    business rule contracts are provided.
    """
    return service.create_job(request)


@router.get(
    "/jobs/{job_id}",
    response_model=ExcelJobRead,
    summary="Get Excel job",
    description="Retrieve details of a specific Excel processing job.",
)
def get_job(
    job_id: str,
    service: ExcelOpsService = Depends(get_excel_ops_service),
) -> ExcelJobRead:
    """Get job by ID."""
    job = service.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    return job


@router.get(
    "/jobs",
    response_model=list[ExcelJobRead],
    summary="List Excel jobs",
    description="List all Excel processing jobs, optionally filtered by status.",
)
def list_jobs(
    status: str | None = None,
    service: ExcelOpsService = Depends(get_excel_ops_service),
) -> list[ExcelJobRead]:
    """List all jobs, optionally filtered by status."""
    # TODO: Map status string to JobStatus enum
    # For now, return all jobs
    return service.list_jobs()


@router.get(
    "/jobs/{job_id}/status",
    response_model=ExcelJobStatusResponse,
    summary="Get job status",
    description="Get detailed job status with readiness info and next steps.",
)
def get_job_status(
    job_id: str,
    service: ExcelOpsService = Depends(get_excel_ops_service),
) -> ExcelJobStatusResponse:
    """Get job status."""
    job_status = service.get_job_status(job_id)
    if job_status is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    return job_status


@router.post(
    "/jobs/{job_id}/calculate",
    response_model=CommissionCalculationResponse,
    summary="Calculate commissions",
    description=(
        "Calculate commissions for a job. "
        "IMPORTANT: Currently blocked awaiting business rule contracts. "
        "Returns explicit blocked status when contracts are missing."
    ),
)
def calculate_commission(
    job_id: str,
    request: CommissionCalculationRequest,
    service: ExcelOpsService = Depends(get_excel_ops_service),
) -> CommissionCalculationResponse:
    """
    Calculate commissions for a job.

    IMPORTANT: This is a scaffold implementation. When requirement #4
    business assets arrive, this will execute deterministic calculations
    based on business-provided rules.
    """
    return service.calculate_commission(job_id, request)


@router.post(
    "/jobs/{job_id}/validate",
    response_model=ExcelValidationResult,
    summary="Validate job outputs",
    description=(
        "Validate job outputs against business rules. "
        "Currently blocked awaiting business validation contracts."
    ),
)
def validate_job(
    job_id: str,
    request: ExcelValidationRequest,
    service: ExcelOpsService = Depends(get_excel_ops_service),
) -> ExcelValidationResult:
    """Validate job outputs."""
    return service.validate_job(
        job_id,
        request.validation_type,
        request.options,
    )


@router.get(
    "/status/requirement4",
    response_model=Requirement4StatusResponse,
    summary="Get requirement #4 readiness status",
    description=(
        "Get status of requirement #4 preparation. "
        "Shows what scaffolding is in place and what business assets are still required."
    ),
)
def get_requirement4_status(
    service: ExcelOpsService = Depends(get_excel_ops_service),
) -> Requirement4StatusResponse:
    """
    Get requirement #4 readiness status.

    Returns information about:
    - What engineering scaffolding is complete
    - What business assets are still required
    - Next steps for implementation
    """
    return service.get_requirement4_status()
