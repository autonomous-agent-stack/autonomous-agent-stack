from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from autoresearch.api.dependencies import get_approval_store_service
from autoresearch.api.routers.admin._auth import _require_admin_high_risk, _require_admin_read
from autoresearch.core.services.admin_auth import AdminAccessClaims
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalNoteRequest,
    ApprovalRequestRead,
    ApprovalStatus,
)


def register_approval_routes(router: APIRouter) -> None:
    @router.get("/approvals", response_model=list[ApprovalRequestRead])
    def admin_list_approvals(
        approval_status: ApprovalStatus | None = Query(default=None, alias="status"),
        telegram_uid: str | None = Query(default=None),
        session_id: str | None = Query(default=None),
        limit: int = Query(default=100, ge=1, le=500),
        access: AdminAccessClaims = Depends(_require_admin_read),
        approval_service: ApprovalStoreService = Depends(get_approval_store_service),
    ) -> list[ApprovalRequestRead]:
        _ = access
        return approval_service.list_requests(
            status=approval_status,
            telegram_uid=telegram_uid,
            session_id=session_id,
            limit=limit,
        )

    @router.post("/approvals/{approval_id}/approve", response_model=ApprovalRequestRead)
    def admin_approve_request(
        approval_id: str,
        payload: ApprovalNoteRequest,
        access: AdminAccessClaims = Depends(_require_admin_high_risk),
        approval_service: ApprovalStoreService = Depends(get_approval_store_service),
    ) -> ApprovalRequestRead:
        try:
            return approval_service.resolve_request(
                approval_id,
                ApprovalDecisionRequest(
                    decision="approved",
                    decided_by=access.subject,
                    note=payload.note,
                    metadata={
                        **payload.metadata,
                        "resolved_via": "admin_api",
                        "admin_roles": list(access.roles),
                    },
                ),
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @router.post("/approvals/{approval_id}/reject", response_model=ApprovalRequestRead)
    def admin_reject_request(
        approval_id: str,
        payload: ApprovalNoteRequest,
        access: AdminAccessClaims = Depends(_require_admin_high_risk),
        approval_service: ApprovalStoreService = Depends(get_approval_store_service),
    ) -> ApprovalRequestRead:
        try:
            return approval_service.resolve_request(
                approval_id,
                ApprovalDecisionRequest(
                    decision="rejected",
                    decided_by=access.subject,
                    note=payload.note,
                    metadata={
                        **payload.metadata,
                        "resolved_via": "admin_api",
                        "admin_roles": list(access.roles),
                    },
                ),
            )
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
