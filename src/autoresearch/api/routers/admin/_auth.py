from __future__ import annotations

from fastapi import HTTPException, Request, status, Depends

from autoresearch.api.dependencies import get_admin_auth_service
from autoresearch.core.services.admin_auth import AdminAccessClaims, AdminAuthService


_ADMIN_READ_ROLES = {"viewer", "editor", "admin", "owner"}
_ADMIN_WRITE_ROLES = {"editor", "admin", "owner"}
_ADMIN_HIGH_ROLES = {"admin", "owner"}


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("authorization", "").strip()
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return ""


def _require_admin_roles(
    request: Request,
    *,
    required_roles: set[str],
    auth_service: AdminAuthService,
) -> AdminAccessClaims:
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing admin bearer token")
    try:
        return auth_service.verify_token(token, required_roles=required_roles)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def _require_admin_read(
    request: Request,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminAccessClaims:
    return _require_admin_roles(request, required_roles=_ADMIN_READ_ROLES, auth_service=auth_service)


def _require_admin_write(
    request: Request,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminAccessClaims:
    return _require_admin_roles(request, required_roles=_ADMIN_WRITE_ROLES, auth_service=auth_service)


def _require_admin_high_risk(
    request: Request,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
) -> AdminAccessClaims:
    return _require_admin_roles(request, required_roles=_ADMIN_HIGH_ROLES, auth_service=auth_service)
