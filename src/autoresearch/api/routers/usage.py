from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from autoresearch.api.dependencies import get_usage_quota_service
from autoresearch.core.services.usage_quota import (
    UsageLedgerEntryRead,
    UsageLedgerStatus,
    UsageQuotaRead,
    UsageQuotaService,
    UsageSubjectType,
)

router = APIRouter(prefix="/api/v1/usage", tags=["usage"])


@router.get("/quota", response_model=UsageQuotaRead)
async def get_usage_quota(
    subject_id: str = Query(default="local-user", min_length=1),
    subject_type: UsageSubjectType = Query(default="user"),
    actor_role: str = Query(default="member", min_length=1),
    service: UsageQuotaService = Depends(get_usage_quota_service),
) -> UsageQuotaRead:
    return service.quota_for(
        subject_id=subject_id,
        subject_type=subject_type,
        actor_role=actor_role,
    )


@router.get("/ledger", response_model=list[UsageLedgerEntryRead])
async def list_usage_ledger(
    subject_id: str | None = Query(default=None),
    status: UsageLedgerStatus | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    service: UsageQuotaService = Depends(get_usage_quota_service),
) -> list[UsageLedgerEntryRead]:
    return service.list_entries(subject_id=subject_id, status=status, limit=limit)


@router.get("/doctor")
async def usage_doctor(
    service: UsageQuotaService = Depends(get_usage_quota_service),
) -> dict[str, object]:
    return service.doctor()
