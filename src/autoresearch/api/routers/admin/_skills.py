from __future__ import annotations

import hashlib
import hmac
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse

from autoresearch.api.dependencies import (
    get_admin_auth_service,
    get_approval_store_service,
    get_managed_skill_registry_service,
    get_panel_access_service,
    get_telegram_notifier_service,
)
from autoresearch.api.routers.admin._auth import _require_admin_high_risk, _require_admin_read, _require_admin_write
from autoresearch.core.services.admin_auth import AdminAccessClaims
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.managed_skill_registry import ManagedSkillRegistryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.models import (
    AdminManagedSkillPromotionExecuteRequest,
    AdminManagedSkillPromotionRequest,
    AdminManagedSkillPromotionRequestRead,
    AdminManagedSkillStatusGroupRead,
    AdminManagedSkillStatusSnapshotRead,
    ApprovalNoteRequest,
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ApprovalRisk,
    ApprovalStatus,
    ManagedSkillInstallRead,
    ManagedSkillInstallStatus,
    utc_now,
)
from autoresearch.shared.store import create_resource_id


_MANAGED_SKILL_GROUP_ORDER = (
    ManagedSkillInstallStatus.PENDING,
    ManagedSkillInstallStatus.QUARANTINED,
    ManagedSkillInstallStatus.COLD_VALIDATED,
    ManagedSkillInstallStatus.PROMOTED,
    ManagedSkillInstallStatus.REJECTED,
)


def _extract_telegram_init_data(request: Request) -> str:
    header_value = request.headers.get("x-telegram-init-data", "").strip()
    if header_value:
        return header_value
    query_value = request.query_params.get("initData")
    if query_value:
        return query_value.strip()
    telegram_query_value = request.query_params.get("tgWebAppData")
    if telegram_query_value:
        return telegram_query_value.strip()
    return ""


def _require_managed_skill_install(
    registry: ManagedSkillRegistryService,
    install_id: str,
) -> ManagedSkillInstallRead:
    install = registry.get_install(install_id)
    if install is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="managed skill install not found")
    return install


def _group_managed_skill_installs(installs: list[ManagedSkillInstallRead]) -> list[AdminManagedSkillStatusGroupRead]:
    grouped: dict[ManagedSkillInstallStatus, list[ManagedSkillInstallRead]] = {
        state: [] for state in _MANAGED_SKILL_GROUP_ORDER
    }
    for item in sorted(installs, key=lambda entry: entry.updated_at, reverse=True):
        grouped.setdefault(item.status, []).append(item)
    return [
        AdminManagedSkillStatusGroupRead(status=state, installs=grouped.get(state, []))
        for state in _MANAGED_SKILL_GROUP_ORDER
    ]


def _select_skill_promotion_uid(
    payload: AdminManagedSkillPromotionRequest,
    *,
    panel_access_service: PanelAccessService,
) -> str:
    candidate = (payload.telegram_uid or "").strip()
    allowed_uids = panel_access_service.allowed_uids
    if candidate:
        if allowed_uids and candidate not in allowed_uids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="telegram uid is not allowed for panel access",
            )
        return candidate
    if len(allowed_uids) == 1:
        return allowed_uids[0]
    if not allowed_uids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="telegram uid is required because no allowed panel uids are configured",
        )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="telegram uid is required because multiple panel uids are configured",
    )


def _build_panel_action_url(
    *,
    panel_access_service: PanelAccessService,
    telegram_uid: str,
    install_id: str,
    approval_id: str,
    action_nonce: str,
    action_hash: str,
    action_issued_at: str,
) -> str:
    return panel_access_service.build_action_url(
        query_params={
            "action": "managed-skill-promote",
            "installId": install_id,
            "approvalId": approval_id,
            "actionNonce": action_nonce,
            "actionHash": action_hash,
            "actionIssuedAt": action_issued_at,
        },
        telegram_uid=telegram_uid,
        prefer_mini_app=True,
    )


def _build_panel_action_markup(
    *,
    panel_access_service: PanelAccessService,
    action_url: str,
) -> dict[str, object] | None:
    markups = _build_panel_action_markups(
        panel_access_service=panel_access_service,
        action_url=action_url,
    )
    return markups[0] if markups else None


def _build_panel_action_markups(
    *,
    panel_access_service: PanelAccessService,
    action_url: str,
) -> list[dict[str, object] | None]:
    parsed = urlparse(action_url)
    if parsed.scheme != "https":
        return [None]
    url_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "打开 Panel 审批",
                    "url": action_url,
                }
            ]
        ]
    }
    if panel_access_service.mini_app_url:
        return [
            {
                "inline_keyboard": [
                    [
                        {
                            "text": "打开 Mini App 审批",
                            "web_app": {"url": action_url},
                        }
                    ]
                ]
            },
            url_markup,
            None,
        ]
    return [url_markup, None]


def _compute_managed_skill_action_hash(
    *,
    approval_id: str,
    install_id: str,
    telegram_uid: str,
    action_nonce: str,
    action_issued_at: str,
) -> str:
    digest = hashlib.sha256()
    digest.update(
        "|".join(
            [
                "managed_skill_promote",
                approval_id,
                install_id,
                telegram_uid,
                action_nonce,
                action_issued_at,
            ]
        ).encode("utf-8")
    )
    return digest.hexdigest()


def _issue_managed_skill_action_binding(
    *,
    approval_id: str,
    install_id: str,
    telegram_uid: str,
) -> dict[str, str]:
    action_nonce = create_resource_id("nonce")
    action_issued_at = utc_now().isoformat()
    action_hash = _compute_managed_skill_action_hash(
        approval_id=approval_id,
        install_id=install_id,
        telegram_uid=telegram_uid,
        action_nonce=action_nonce,
        action_issued_at=action_issued_at,
    )
    return {
        "action_nonce": action_nonce,
        "action_hash": action_hash,
        "action_issued_at": action_issued_at,
    }


def _require_valid_managed_skill_action_binding(
    *,
    approval: ApprovalRequestRead,
    install_id: str,
    telegram_uid: str,
    payload: AdminManagedSkillPromotionExecuteRequest,
) -> None:
    action_nonce = str(approval.metadata.get("action_nonce", "")).strip()
    action_hash = str(approval.metadata.get("action_hash", "")).strip().lower()
    action_issued_at = str(approval.metadata.get("action_issued_at", "")).strip()
    if not action_nonce or not action_hash or not action_issued_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="approval action binding is missing")
    if approval.metadata.get("action_consumed_at"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="approval action binding already consumed")
    if not hmac.compare_digest(payload.action_nonce.strip(), action_nonce):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="action nonce mismatch")
    if not hmac.compare_digest(payload.action_issued_at.strip(), action_issued_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="action issued_at mismatch")

    expected_hash = _compute_managed_skill_action_hash(
        approval_id=approval.approval_id,
        install_id=install_id,
        telegram_uid=telegram_uid,
        action_nonce=action_nonce,
        action_issued_at=action_issued_at,
    )
    if not hmac.compare_digest(payload.action_hash.strip().lower(), action_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="action hash mismatch")
    if not hmac.compare_digest(action_hash, expected_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="action hash verification failed")


def register_skill_routes(router: APIRouter) -> None:
    @router.get("/skills/status", response_model=AdminManagedSkillStatusSnapshotRead)
    def admin_managed_skill_status(
        access: AdminAccessClaims = Depends(_require_admin_read),
        registry: ManagedSkillRegistryService = Depends(get_managed_skill_registry_service),
    ) -> AdminManagedSkillStatusSnapshotRead:
        _ = access
        return AdminManagedSkillStatusSnapshotRead(
            groups=_group_managed_skill_installs(registry.list_installs()),
            issued_at=utc_now(),
        )

    @router.get("/skills/{install_id}", response_model=ManagedSkillInstallRead)
    def admin_managed_skill_detail(
        install_id: str,
        access: AdminAccessClaims = Depends(_require_admin_read),
        registry: ManagedSkillRegistryService = Depends(get_managed_skill_registry_service),
    ) -> ManagedSkillInstallRead:
        _ = access
        return _require_managed_skill_install(registry, install_id)

    @router.post("/skills/{install_id}/validate", response_model=ManagedSkillInstallRead)
    def admin_validate_managed_skill(
        install_id: str,
        access: AdminAccessClaims = Depends(_require_admin_write),
        registry: ManagedSkillRegistryService = Depends(get_managed_skill_registry_service),
    ) -> ManagedSkillInstallRead:
        _ = access
        _require_managed_skill_install(registry, install_id)
        try:
            return registry.run_cold_validation(install_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @router.post("/skills/{install_id}/promote", response_model=AdminManagedSkillPromotionRequestRead)
    def admin_request_managed_skill_promotion(
        install_id: str,
        payload: AdminManagedSkillPromotionRequest | None = None,
        access: AdminAccessClaims = Depends(_require_admin_high_risk),
        registry: ManagedSkillRegistryService = Depends(get_managed_skill_registry_service),
        approval_service: ApprovalStoreService = Depends(get_approval_store_service),
        panel_access_service: PanelAccessService = Depends(get_panel_access_service),
        notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
    ) -> AdminManagedSkillPromotionRequestRead:
        request_payload = payload or AdminManagedSkillPromotionRequest()
        install = _require_managed_skill_install(registry, install_id)
        if install.status is not ManagedSkillInstallStatus.COLD_VALIDATED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"managed skill is not cold_validated: {install_id}",
            )

        telegram_uid = _select_skill_promotion_uid(request_payload, panel_access_service=panel_access_service)
        approval = approval_service.create_request(
            ApprovalRequestCreateRequest(
                title=f"Promote managed skill {install.skill_id}@{install.version}",
                summary=(
                    f"Promote install {install.install_id} from cold_validated to promoted. "
                    "This will expose the skill to the managed capability surface."
                ),
                risk=ApprovalRisk.DESTRUCTIVE,
                source="managed_skill_promotion",
                telegram_uid=telegram_uid,
                expires_in_seconds=request_payload.expires_in_seconds,
                metadata={
                    **dict(request_payload.metadata),
                    "action_type": "managed_skill_promote",
                    "install_id": install.install_id,
                    "skill_id": install.skill_id,
                    "version": install.version,
                    "requested_by": access.subject,
                },
            )
        )
        action_binding = _issue_managed_skill_action_binding(
            approval_id=approval.approval_id,
            install_id=install.install_id,
            telegram_uid=telegram_uid,
        )
        approval = approval_service.update_request_metadata(
            approval.approval_id,
            action_binding,
            require_status=ApprovalStatus.PENDING,
        )

        mini_app_url = _build_panel_action_url(
            panel_access_service=panel_access_service,
            telegram_uid=telegram_uid,
            install_id=install.install_id,
            approval_id=approval.approval_id,
            action_nonce=action_binding["action_nonce"],
            action_hash=action_binding["action_hash"],
            action_issued_at=action_binding["action_issued_at"],
        )
        note = (request_payload.note or "").strip()
        message_lines = [
            "[技能提权审批]",
            f"- skill: {install.skill_id}@{install.version}",
            f"- install: {install.install_id}",
            f"- status: {install.status.value}",
            f"- approval_id: {approval.approval_id}",
        ]
        if note:
            message_lines.append(f"- note: {note}")
        if approval.expires_at is not None:
            message_lines.append(f"- expires_at: {approval.expires_at.isoformat()}")
        notification_sent = False
        for reply_markup in _build_panel_action_markups(
            panel_access_service=panel_access_service,
            action_url=mini_app_url,
        ):
            if notifier.send_message(
                chat_id=telegram_uid,
                text="\n".join(message_lines),
                reply_markup=reply_markup,
            ):
                notification_sent = True
                break
        return AdminManagedSkillPromotionRequestRead(
            install=install,
            approval=approval,
            mini_app_url=mini_app_url,
            notification_sent=notification_sent,
        )

    @router.post("/skills/{install_id}/promote/execute", response_model=ManagedSkillInstallRead)
    def admin_execute_managed_skill_promotion(
        install_id: str,
        payload: AdminManagedSkillPromotionExecuteRequest,
        request: Request,
        registry: ManagedSkillRegistryService = Depends(get_managed_skill_registry_service),
        approval_service: ApprovalStoreService = Depends(get_approval_store_service),
        panel_access_service: PanelAccessService = Depends(get_panel_access_service),
    ) -> ManagedSkillInstallRead:
        init_data = _extract_telegram_init_data(request)
        if not init_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing telegram initData",
            )
        try:
            claims = panel_access_service.verify_telegram_init_data(init_data)
        except PermissionError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

        install = _require_managed_skill_install(registry, install_id)
        approval = approval_service.get_request(payload.approval_id)
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="approval not found")
        if approval.telegram_uid != claims.telegram_uid:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        if approval.status is not ApprovalStatus.APPROVED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="approval is not approved")
        if approval.metadata.get("action_type") != "managed_skill_promote":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="approval action_type mismatch")
        if str(approval.metadata.get("install_id", "")).strip() != install_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="approval install_id mismatch")
        _require_valid_managed_skill_action_binding(
            approval=approval,
            install_id=install_id,
            telegram_uid=claims.telegram_uid,
            payload=payload,
        )

        if install.status is ManagedSkillInstallStatus.PROMOTED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="managed skill already promoted")
        if install.status is not ManagedSkillInstallStatus.COLD_VALIDATED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"managed skill is not cold_validated: {install_id}",
            )

        try:
            promoted = registry.promote_skill(install_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if promoted.status is not ManagedSkillInstallStatus.PROMOTED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=promoted.error or "managed skill promotion did not reach promoted state",
            )
        approval_service.update_request_metadata(
            approval.approval_id,
            {
                "action_consumed_at": utc_now().isoformat(),
                "action_consumed_by": claims.telegram_uid,
                "action_execute_note": (payload.note or "").strip() or None,
                **dict(payload.metadata),
            },
            require_status=ApprovalStatus.APPROVED,
        )
        return promoted
