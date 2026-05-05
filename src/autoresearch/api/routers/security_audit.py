from __future__ import annotations

from fastapi import APIRouter, Depends

from autoresearch.api.dependencies import get_security_audit_service
from autoresearch.core.services.security_audit import (
    SecurityAuditDailyReportRead,
    SecurityAuditQuickScanRead,
    SecurityAuditQuickScanRequest,
    SecurityAuditService,
)


router = APIRouter(prefix="/api/v2/security-audit", tags=["security-audit"])


@router.post("/quick-scan", response_model=SecurityAuditQuickScanRead)
def quick_scan(
    payload: SecurityAuditQuickScanRequest,
    service: SecurityAuditService = Depends(get_security_audit_service),
) -> SecurityAuditQuickScanRead:
    return service.quick_scan(payload)


@router.get("/daily", response_model=SecurityAuditDailyReportRead)
def daily_report(
    service: SecurityAuditService = Depends(get_security_audit_service),
) -> SecurityAuditDailyReportRead:
    return service.generate_daily_report()
