"""API router for Excel audit endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_excel_audit_service
from autoresearch.core.services.excel_audit import ExcelAuditService
from autoresearch.shared.excel_audit_contract import (
    ExcelAuditCreateRequest,
    ExcelAuditRead,
)

router = APIRouter(prefix="/api/v1/excel-audit", tags=["excel-audit"])


@router.post(
    "/audits",
    response_model=ExcelAuditRead,
    status_code=status.HTTP_201_CREATED,
)
def create_audit(
    payload: ExcelAuditCreateRequest,
    service: ExcelAuditService = Depends(get_excel_audit_service),
) -> ExcelAuditRead:
    """Submit a new Excel audit job."""
    return service.create_and_execute(payload)


@router.get("/audits", response_model=list[ExcelAuditRead])
def list_audits(
    service: ExcelAuditService = Depends(get_excel_audit_service),
) -> list[ExcelAuditRead]:
    """List all audit jobs."""
    return service.list()


@router.get("/audits/{audit_id}", response_model=ExcelAuditRead)
def get_audit(
    audit_id: str,
    service: ExcelAuditService = Depends(get_excel_audit_service),
) -> ExcelAuditRead:
    """Get a specific audit job."""
    record = service.get(audit_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Audit {audit_id} not found")
    return record
