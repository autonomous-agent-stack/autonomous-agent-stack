from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from autoresearch.api.dependencies import get_admin_auth_service, get_approval_store_service
from autoresearch.core.services.admin_auth import AdminAccessClaims, AdminAuthService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.shared.models import ApprovalDecisionRequest, ApprovalRequestRead, ApprovalStatus


router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])

_APPROVAL_READ_ROLES = {"viewer", "editor", "admin", "owner"}
_APPROVAL_WRITE_ROLES = {"admin", "owner"}


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "").strip()
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return ""


def _require_approval_read(
    request: Request,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminAccessClaims:
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing admin bearer token")
    try:
        return auth_service.verify_token(token, required_roles=_APPROVAL_READ_ROLES)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def _require_approval_write(
    request: Request,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminAccessClaims:
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing admin bearer token")
    try:
        return auth_service.verify_token(token, required_roles=_APPROVAL_WRITE_ROLES)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/health")
def approvals_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("", response_model=list[ApprovalRequestRead])
def list_approvals(
    approval_status: ApprovalStatus | None = Query(default=None, alias="status"),
    telegram_uid: str | None = Query(default=None),
    session_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    access: AdminAccessClaims = Depends(_require_approval_read),
    approval_service: ApprovalStoreService = Depends(get_approval_store_service),
) -> list[ApprovalRequestRead]:
    _ = access
    return approval_service.list_requests(
        status=approval_status,
        telegram_uid=telegram_uid,
        session_id=session_id,
        limit=limit,
    )


@router.get("/{approval_id}", response_model=ApprovalRequestRead)
def get_approval(
    approval_id: str,
    access: AdminAccessClaims = Depends(_require_approval_read),
    approval_service: ApprovalStoreService = Depends(get_approval_store_service),
) -> ApprovalRequestRead:
    _ = access
    item = approval_service.get_request(approval_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval not found")
    return item


@router.post("/{approval_id}/decision", response_model=ApprovalRequestRead)
def resolve_approval(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    access: AdminAccessClaims = Depends(_require_approval_write),
    approval_service: ApprovalStoreService = Depends(get_approval_store_service),
) -> ApprovalRequestRead:
    _ = access
    try:
        return approval_service.resolve_request(approval_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
