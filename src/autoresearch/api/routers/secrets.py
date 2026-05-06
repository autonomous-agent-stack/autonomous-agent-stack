from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from autoresearch.core.services.secret_vault import (
    SecretAccessDenied,
    SecretAccessRequest,
    SecretVaultService,
)
from autoresearch.ga.contracts import SecretLeaseRead


router = APIRouter(prefix="/api/v2/secrets", tags=["secret-vault"])

_vault = SecretVaultService()


@router.post("/leases", response_model=SecretLeaseRead, status_code=status.HTTP_201_CREATED)
def issue_secret_lease(payload: SecretAccessRequest) -> SecretLeaseRead:
    try:
        return _vault.issue_lease(payload)
    except SecretAccessDenied as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get("/leases", response_model=list[SecretLeaseRead])
def list_secret_leases() -> list[SecretLeaseRead]:
    return _vault.list_leases()

