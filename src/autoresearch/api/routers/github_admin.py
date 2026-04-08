from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from github_admin.contracts import (
    GitHubAdminInventoryRequest,
    GitHubAdminRunRead,
    GitHubAdminTransferPlanRequest,
)
from autoresearch.api.dependencies import get_github_admin_service
from autoresearch.core.services.github_admin import GitHubAdminService


router = APIRouter(prefix="/api/jobs/github-admin", tags=["github-admin"])


def _to_http_exception(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/inventory", response_model=GitHubAdminRunRead, status_code=status.HTTP_200_OK)
def create_inventory_run(
    payload: GitHubAdminInventoryRequest,
    service: GitHubAdminService = Depends(get_github_admin_service),
) -> GitHubAdminRunRead:
    try:
        return service.inventory(payload)
    except Exception as exc:
        raise _to_http_exception(exc) from exc


@router.post("/transfer-plan", response_model=GitHubAdminRunRead, status_code=status.HTTP_200_OK)
def create_transfer_plan(
    payload: GitHubAdminTransferPlanRequest,
    service: GitHubAdminService = Depends(get_github_admin_service),
) -> GitHubAdminRunRead:
    try:
        return service.transfer_plan(payload)
    except Exception as exc:
        raise _to_http_exception(exc) from exc


@router.post("/execute-transfer", status_code=status.HTTP_501_NOT_IMPLEMENTED)
def execute_transfer_not_implemented() -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Dry-run only in this slice. /api/jobs/github-admin/execute-transfer is not implemented yet.",
    )
