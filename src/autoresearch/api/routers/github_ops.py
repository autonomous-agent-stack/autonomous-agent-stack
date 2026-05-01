from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from autoresearch.api.dependencies import get_github_ops_service
from autoresearch.core.services.github_ops import GitHubOpsRequest, GitHubOpsResult, GitHubOpsService


router = APIRouter(prefix="/api/v1/github-ops", tags=["github ops"])


@router.get("/doctor", status_code=status.HTTP_200_OK)
def github_ops_doctor(
    account_profile: str = "accountA",
    service: GitHubOpsService = Depends(get_github_ops_service),
) -> dict[str, object]:
    return service.doctor(account_profile=account_profile)


@router.post("/execute", response_model=GitHubOpsResult, status_code=status.HTTP_200_OK)
def execute_github_ops(
    payload: GitHubOpsRequest,
    service: GitHubOpsService = Depends(get_github_ops_service),
) -> GitHubOpsResult:
    try:
        return service.execute(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
