from __future__ import annotations

import hashlib
import hmac
from typing import Any, Literal
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse

from autoresearch.api.dependencies import (
    get_admin_auth_service,
    get_admin_config_service,
    get_agent_audit_trail_service,
    get_approval_store_service,
    get_capability_provider_registry,
    get_claude_agent_service,
    get_managed_skill_registry_service,
    get_panel_access_service,
    get_telegram_notifier_service,
)
from autoresearch.core.adapters import CalendarAdapter, CapabilityProviderRegistry, GitHubAdapter, MCPProvider, SkillProvider
from autoresearch.core.services.admin_auth import AdminAccessClaims, AdminAuthService
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.managed_skill_registry import ManagedSkillRegistryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalNoteRequest,
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ApprovalRisk,
    ApprovalStatus,
    AdminAgentAuditTrailDetailRead,
    AdminAgentAuditTrailSnapshotRead,
    AdminCapabilityProviderInventoryRead,
    AdminCapabilitySnapshotRead,
    AdminCapabilityToolRead,
    AdminAgentConfigCreateRequest,
    AdminAgentConfigRead,
    AdminAgentConfigUpdateRequest,
    AdminAgentLaunchRequest,
    AdminChannelConfigCreateRequest,
    AdminChannelConfigRead,
    AdminChannelConfigUpdateRequest,
    AdminConfigRevisionRead,
    AdminConfigRollbackRequest,
    AdminConfigStatusChangeRequest,
    AdminManagedSkillPromotionExecuteRequest,
    AdminManagedSkillPromotionRequest,
    AdminManagedSkillPromotionRequestRead,
    AdminManagedSkillStatusGroupRead,
    AdminManagedSkillStatusSnapshotRead,
    AdminTokenIssueRequest,
    AdminTokenRead,
    CapabilityProviderSummaryRead,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    ManagedSkillInstallRead,
    ManagedSkillInstallStatus,
    utc_now,
)
from autoresearch.shared.store import create_resource_id


router = APIRouter(prefix="/api/v1/admin", tags=["admin-config"])

_ADMIN_READ_ROLES = {"viewer", "editor", "admin", "owner"}
_ADMIN_WRITE_ROLES = {"editor", "admin", "owner"}
_ADMIN_HIGH_ROLES = {"admin", "owner"}
_MANAGED_SKILL_GROUP_ORDER = (
    ManagedSkillInstallStatus.PENDING,
    ManagedSkillInstallStatus.QUARANTINED,
    ManagedSkillInstallStatus.COLD_VALIDATED,
    ManagedSkillInstallStatus.PROMOTED,
    ManagedSkillInstallStatus.REJECTED,
)


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


@router.get("/health")
def admin_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/capabilities", response_model=AdminCapabilitySnapshotRead)
def admin_capability_snapshot(
    access: AdminAccessClaims = Depends(_require_admin_read),
    registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
) -> AdminCapabilitySnapshotRead:
    inventories: list[AdminCapabilityProviderInventoryRead] = []
    for descriptor in registry.list_descriptors():
        provider = registry.get(descriptor.provider_id)
        if provider is None:
            continue
        skills = provider.list_skills().skills if isinstance(provider, SkillProvider) else []
        tools = (
            [
                AdminCapabilityToolRead(
                    name=tool.name,
                    description=tool.description,
                    metadata=tool.metadata,
                )
                for tool in provider.list_tools()
            ]
            if isinstance(provider, MCPProvider)
            else []
        )
        inventories.append(
            AdminCapabilityProviderInventoryRead(
                provider=CapabilityProviderSummaryRead(**descriptor.model_dump()),
                skills=skills,
                tools=tools,
                supports_calendar_query=isinstance(provider, CalendarAdapter),
                supports_github_search=isinstance(provider, GitHubAdapter),
            )
        )
    return AdminCapabilitySnapshotRead(providers=inventories, issued_at=utc_now())


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


@router.get("/view", response_class=HTMLResponse, include_in_schema=False)
def admin_view() -> HTMLResponse:
    return HTMLResponse(_ADMIN_HTML)


@router.post("/auth/token", response_model=AdminTokenRead)
def issue_admin_token(
    payload: AdminTokenIssueRequest,
    auth_service: AdminAuthService = Depends(get_admin_auth_service),
    bootstrap_key: str | None = Header(default=None, alias="x-admin-bootstrap-key"),
) -> AdminTokenRead:
    try:
        return auth_service.issue_token(
            subject=payload.subject,
            roles=list(payload.roles),
            bootstrap_key=bootstrap_key,
            ttl_seconds=payload.ttl_seconds,
        )
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/agents", response_model=AdminAgentConfigRead, status_code=status.HTTP_201_CREATED)
def create_agent_config(
    payload: AdminAgentConfigCreateRequest,
    access: AdminAccessClaims = Depends(_require_admin_write),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.create_agent(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/agents", response_model=list[AdminAgentConfigRead])
def list_agent_configs(
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminAgentConfigRead]:
    return service.list_agents()


@router.get("/agents/{agent_id}", response_model=AdminAgentConfigRead)
def get_agent_config(
    agent_id: str,
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    item = service.get_agent(agent_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found")
    return item


@router.put("/agents/{agent_id}", response_model=AdminAgentConfigRead)
def update_agent_config(
    agent_id: str,
    payload: AdminAgentConfigUpdateRequest,
    access: AdminAccessClaims = Depends(_require_admin_write),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.update_agent(agent_id=agent_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/agents/{agent_id}/activate", response_model=AdminAgentConfigRead)
def activate_agent_config(
    agent_id: str,
    payload: AdminConfigStatusChangeRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.set_agent_enabled(
            agent_id=agent_id,
            enabled=True,
            actor=payload.actor,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found") from exc


@router.post("/agents/{agent_id}/deactivate", response_model=AdminAgentConfigRead)
def deactivate_agent_config(
    agent_id: str,
    payload: AdminConfigStatusChangeRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.set_agent_enabled(
            agent_id=agent_id,
            enabled=False,
            actor=payload.actor,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found") from exc


@router.post("/agents/{agent_id}/rollback", response_model=AdminAgentConfigRead)
def rollback_agent_config(
    agent_id: str,
    payload: AdminConfigRollbackRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminAgentConfigRead:
    try:
        return service.rollback_agent(agent_id=agent_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/agents/{agent_id}/history", response_model=list[AdminConfigRevisionRead])
def list_agent_history(
    agent_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminConfigRevisionRead]:
    if service.get_agent(agent_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found")
    return service.list_revisions(target_type="agent", target_id=agent_id, limit=limit)


@router.post(
    "/agents/{agent_id}/launch",
    response_model=ClaudeAgentRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def launch_agent_from_config(
    agent_id: str,
    payload: AdminAgentLaunchRequest,
    background_tasks: BackgroundTasks,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    config_service: AdminConfigService = Depends(get_admin_config_service),
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
) -> ClaudeAgentRunRead:
    config = config_service.get_agent(agent_id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found")
    if config.status != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Agent config is inactive")

    prompt = payload.prompt_override if payload.prompt_override is not None else config.prompt_template
    metadata = {
        **config.metadata,
        **payload.metadata_updates,
        "agent_config_id": config.agent_id,
        "agent_config_version": config.version,
        "launch_mode": "admin_config",
    }
    request_payload = ClaudeAgentCreateRequest(
        task_name=config.task_name,
        prompt=prompt,
        session_id=payload.session_id,
        generation_depth=(
            payload.generation_depth_override
            if payload.generation_depth_override is not None
            else config.default_generation_depth
        ),
        timeout_seconds=(
            payload.timeout_seconds_override
            if payload.timeout_seconds_override is not None
            else config.default_timeout_seconds
        ),
        cli_args=list(config.cli_args),
        command_override=list(config.command_override) if config.command_override else None,
        append_prompt=config.append_prompt,
        env={**config.default_env, **payload.env_overrides},
        metadata=metadata,
    )
    try:
        run = agent_service.create(request_payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc

    background_tasks.add_task(agent_service.execute, run.agent_run_id, request_payload)
    return run


@router.post("/channels", response_model=AdminChannelConfigRead, status_code=status.HTTP_201_CREATED)
def create_channel_config(
    payload: AdminChannelConfigCreateRequest,
    access: AdminAccessClaims = Depends(_require_admin_write),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.create_channel(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/channels", response_model=list[AdminChannelConfigRead])
def list_channel_configs(
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminChannelConfigRead]:
    return service.list_channels()


@router.get("/channels/{channel_id}", response_model=AdminChannelConfigRead)
def get_channel_config(
    channel_id: str,
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    item = service.get_channel(channel_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found")
    return item


@router.put("/channels/{channel_id}", response_model=AdminChannelConfigRead)
def update_channel_config(
    channel_id: str,
    payload: AdminChannelConfigUpdateRequest,
    access: AdminAccessClaims = Depends(_require_admin_write),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.update_channel(channel_id=channel_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.post("/channels/{channel_id}/activate", response_model=AdminChannelConfigRead)
def activate_channel_config(
    channel_id: str,
    payload: AdminConfigStatusChangeRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.set_channel_enabled(
            channel_id=channel_id,
            enabled=True,
            actor=payload.actor,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found") from exc


@router.post("/channels/{channel_id}/deactivate", response_model=AdminChannelConfigRead)
def deactivate_channel_config(
    channel_id: str,
    payload: AdminConfigStatusChangeRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.set_channel_enabled(
            channel_id=channel_id,
            enabled=False,
            actor=payload.actor,
            reason=payload.reason,
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found") from exc


@router.post("/channels/{channel_id}/rollback", response_model=AdminChannelConfigRead)
def rollback_channel_config(
    channel_id: str,
    payload: AdminConfigRollbackRequest,
    access: AdminAccessClaims = Depends(_require_admin_high_risk),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> AdminChannelConfigRead:
    try:
        return service.rollback_channel(channel_id=channel_id, request=payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/channels/{channel_id}/history", response_model=list[AdminConfigRevisionRead])
def list_channel_history(
    channel_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminConfigRevisionRead]:
    if service.get_channel(channel_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel config not found")
    return service.list_revisions(target_type="channel", target_id=channel_id, limit=limit)


@router.get("/audit-trail", response_model=AdminAgentAuditTrailSnapshotRead)
def get_agent_audit_trail(
    limit: int = Query(default=20, ge=1, le=200),
    status_filter: Literal["all", "success", "failed", "pending", "running", "review"] | None = Query(
        default=None
    ),
    agent_role: Literal["all", "manager", "planner", "worker"] | None = Query(default=None),
    access: AdminAccessClaims = Depends(_require_admin_read),
    service=Depends(get_agent_audit_trail_service),
) -> AdminAgentAuditTrailSnapshotRead:
    return service.snapshot(limit=limit, status_filter=status_filter, agent_role=agent_role)


@router.get("/audit-trail/{entry_id}", response_model=AdminAgentAuditTrailDetailRead)
def get_agent_audit_trail_detail(
    entry_id: str,
    access: AdminAccessClaims = Depends(_require_admin_read),
    service=Depends(get_agent_audit_trail_service),
) -> AdminAgentAuditTrailDetailRead:
    try:
        return service.detail(entry_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="audit trail entry not found") from exc


@router.get("/revisions", response_model=list[AdminConfigRevisionRead])
def list_revisions(
    target_type: Literal["agent", "channel"] | None = None,
    target_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    access: AdminAccessClaims = Depends(_require_admin_read),
    service: AdminConfigService = Depends(get_admin_config_service),
) -> list[AdminConfigRevisionRead]:
    return service.list_revisions(target_type=target_type, target_id=target_id, limit=limit)


_ADMIN_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Autoresearch Admin</title>
  <style>
    :root {
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #0f1f3d;
      --muted: #5f6b81;
      --line: #d9e1ee;
      --ok: #0d7f4f;
      --warn: #92400e;
      --danger: #b42318;
      --accent: #0b6cff;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans SC", sans-serif;
    }
    main {
      max-width: 1260px;
      margin: 0 auto;
      padding: 20px;
    }
    .grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }
    @media (min-width: 1100px) {
      .grid { grid-template-columns: 1fr 1fr; }
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
    }
    h1, h2 { margin: 0 0 10px; }
    h1 { font-size: 24px; }
    h2 { font-size: 18px; }
    .muted { color: var(--muted); font-size: 13px; margin: 0; }
    .row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 10px;
    }
    input, textarea, select, button {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 13px;
      background: #fff;
      color: var(--text);
    }
    textarea {
      width: 100%;
      min-height: 94px;
      resize: vertical;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    button {
      cursor: pointer;
      font-weight: 600;
    }
    .btn-primary {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }
    .btn-danger {
      color: #fff;
      border-color: var(--danger);
      background: var(--danger);
    }
    .table-wrap {
      overflow: auto;
      max-height: 420px;
      border: 1px solid var(--line);
      border-radius: 10px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 700px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      text-align: left;
      padding: 8px;
      font-size: 12px;
      vertical-align: top;
    }
    th {
      background: #f8faff;
      position: sticky;
      top: 0;
      z-index: 1;
    }
    .pill {
      display: inline-block;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 11px;
      font-weight: 700;
      border: 1px solid transparent;
    }
    .active { color: var(--ok); border-color: #a7f3d0; background: #ecfdf3; }
    .inactive { color: var(--warn); border-color: #fcd9bd; background: #fff7ed; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 6px; }
    .subcard {
      background: #fbfdff;
      border: 1px dashed var(--line);
      border-radius: 10px;
      padding: 10px;
      margin-bottom: 10px;
    }
    h3 {
      margin: 0 0 8px;
      font-size: 15px;
    }
    .inline-check {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--muted);
      padding: 4px 0;
    }
    .inline-check input {
      width: 14px;
      height: 14px;
      margin: 0;
    }
    pre {
      margin: 0;
      padding: 10px;
      background: #0e1a33;
      color: #dbe8ff;
      border-radius: 8px;
      max-height: 200px;
      overflow: auto;
      font-size: 12px;
    }
  </style>
</head>
<body>
<main>
  <section class="card">
    <h1>Autoresearch 可编辑后台</h1>
    <div class="row">
      <button onclick="setAdminToken()">设置 Admin Token</button>
      <button class="btn-danger" onclick="clearAdminToken()">清除 Token</button>
    </div>
    <p id="summary" class="muted">加载中...</p>
  </section>

  <section class="grid">
    <section class="card">
      <h2>Agent 配置</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
        <button onclick="createAgent()">新建 Agent（表单）</button>
        <button onclick="createAgentAdvancedJson()">高级 JSON</button>
      </div>
      <div class="subcard" id="agent-form-card">
        <h3 id="agent-form-title">Agent 表单（新建）</h3>
        <p class="muted">默认走表单，复杂参数再点“高级 JSON”。</p>
        <div class="row">
          <input id="agent-form-name" placeholder="name" value="assistant-main" />
          <input id="agent-form-task" placeholder="task_name" value="general-task" />
          <input id="agent-form-timeout" type="number" min="1" max="7200" value="900" />
          <input id="agent-form-depth" type="number" min="1" max="10" value="1" />
        </div>
        <textarea id="agent-form-description" placeholder="description">default admin agent</textarea>
        <textarea id="agent-form-prompt" placeholder="prompt_template">You are my primary autonomous agent.</textarea>
        <div class="row">
          <input id="agent-form-channels" placeholder="channel_bindings, comma separated" value="telegram-main" />
          <input id="agent-form-actor" placeholder="actor" value="admin-ui" />
          <label class="inline-check"><input id="agent-form-append" type="checkbox" checked />append_prompt</label>
          <label class="inline-check"><input id="agent-form-enabled" type="checkbox" checked />enabled</label>
        </div>
        <div class="row">
          <button class="btn-primary" onclick="submitAgentForm()">保存 Agent</button>
          <button onclick="resetAgentForm()">清空</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Task</th>
              <th>Version</th>
              <th>Status</th>
              <th>Updated</th>
              <th>Ops</th>
            </tr>
          </thead>
          <tbody id="agents-body"></tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <h2>Channel 配置</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
        <button onclick="createChannel()">新建 Channel（表单）</button>
        <button onclick="createChannelAdvancedJson()">高级 JSON</button>
      </div>
      <div class="subcard">
        <h3>Telegram 快速配置（ClawX 风格）</h3>
        <p class="muted">只填 key、bot token、allowed ids，一键保存。</p>
        <div class="row">
          <input id="tg-quick-key" placeholder="key" value="telegram-main" />
          <input id="tg-quick-token" type="password" placeholder="bot token (@BotFather)" value="" />
          <input id="tg-quick-ids" placeholder="allowed ids, comma separated" value="" />
          <input id="tg-quick-actor" placeholder="actor" value="admin-ui" />
        </div>
        <div class="row">
          <button class="btn-primary" onclick="quickCreateTelegramChannel()">一键保存 Telegram Channel</button>
        </div>
      </div>
      <div class="subcard" id="channel-form-card">
        <h3 id="channel-form-title">Channel 表单（新建）</h3>
        <p class="muted">默认走表单，secret 可选。编辑时可覆盖字段并自动保存版本。</p>
        <div class="row">
          <input id="channel-form-key" placeholder="key" value="telegram-main" />
          <input id="channel-form-display" placeholder="display_name" value="Telegram Main" />
          <select id="channel-form-provider">
            <option value="telegram">telegram</option>
            <option value="webhook">webhook</option>
            <option value="http">http</option>
            <option value="custom">custom</option>
          </select>
          <input id="channel-form-endpoint" placeholder="endpoint_url (optional)" value="" />
        </div>
        <div class="row">
          <input id="channel-form-secret-ref" placeholder="secret_ref (optional)" value="" />
          <input id="channel-form-secret-value" type="password" placeholder="secret_value (optional)" value="" />
        </div>
        <div class="row">
          <input id="channel-form-allowed-chat-ids" placeholder="allowed_chat_ids, comma separated" value="" />
          <input id="channel-form-allowed-user-ids" placeholder="allowed_user_ids, comma separated" value="" />
          <input id="channel-form-actor" placeholder="actor" value="admin-ui" />
          <label class="inline-check"><input id="channel-form-enabled" type="checkbox" checked />enabled</label>
        </div>
        <div class="row">
          <button class="btn-primary" onclick="submitChannelForm()">保存 Channel</button>
          <button onclick="resetChannelForm()">清空</button>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Key</th>
              <th>Provider</th>
              <th>Secret</th>
              <th>Version</th>
              <th>Status</th>
              <th>Updated</th>
              <th>Ops</th>
            </tr>
          </thead>
          <tbody id="channels-body"></tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <h2>Capability Inventory</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Provider</th>
              <th>Domain</th>
              <th>Status</th>
              <th>Capabilities</th>
              <th>Skills</th>
              <th>Tools</th>
              <th>Read Ops</th>
            </tr>
          </thead>
          <tbody id="capabilities-body"></tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <h2>Approval Queue</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Risk</th>
              <th>Title</th>
              <th>UID</th>
              <th>Source</th>
              <th>Expires</th>
              <th>Ops</th>
            </tr>
          </thead>
          <tbody id="approvals-body"></tbody>
        </table>
      </div>
    </section>

    <section class="card">
      <h2>Managed Skill Queue</h2>
      <div class="row">
        <button class="btn-primary" onclick="refreshAll()">刷新</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Install</th>
              <th>Status</th>
              <th>Skill</th>
              <th>Version</th>
              <th>Requested By</th>
              <th>Updated</th>
              <th>Ops</th>
            </tr>
          </thead>
          <tbody id="skills-body"></tbody>
        </table>
      </div>
      <div class="subcard">
        <h3>Skill Detail</h3>
        <pre id="skill-detail-pre">{}</pre>
      </div>
    </section>
  </section>

  <section class="card">
    <h2>Agent Audit Trail</h2>
    <div class="row">
      <button class="btn-primary" onclick="loadAuditTrail()">刷新</button>
      <select id="audit-status-filter" onchange="loadAuditTrail()">
        <option value="all">全部状态</option>
        <option value="success">Success</option>
        <option value="failed">Failed</option>
        <option value="pending">Pending</option>
        <option value="running">Running</option>
        <option value="review">Review</option>
      </select>
      <select id="audit-role-filter" onchange="loadAuditTrail()">
        <option value="all">全部角色</option>
        <option value="manager">Manager</option>
        <option value="planner">Planner</option>
        <option value="worker">Worker</option>
      </select>
      <span id="audit-trail-summary">最近 20 条执行足迹</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Time</th>
            <th>Role</th>
            <th>Run</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Files</th>
            <th>Scope</th>
            <th>Changed</th>
            <th>Inspect</th>
          </tr>
        </thead>
        <tbody id="audit-trail-body"></tbody>
      </table>
    </div>
    <div class="subcard">
      <h3>Audit Detail</h3>
      <p id="audit-detail-meta" class="muted">点击单条记录查看输入、patch diff 和失败原因。</p>
      <div class="row">
        <button onclick="clearAuditDetail()">清空详情</button>
      </div>
      <div class="subcard">
        <h3>Input Context</h3>
        <pre id="audit-input-pre">暂无</pre>
      </div>
      <div class="subcard">
        <h3>Patch Diff</h3>
        <pre id="audit-patch-pre">暂无</pre>
      </div>
      <div class="subcard">
        <h3>Failure / Traceback</h3>
        <pre id="audit-error-pre">暂无</pre>
      </div>
    </div>
  </section>

  <section class="card">
    <h2>Revision Timeline</h2>
    <div class="row">
      <select id="rev-type">
        <option value="">全部</option>
        <option value="agent">agent</option>
        <option value="channel">channel</option>
      </select>
      <input id="rev-target" placeholder="target_id (可选)" />
      <button onclick="loadRevisions()">过滤</button>
    </div>
    <pre id="revisions-pre">[]</pre>
  </section>
</main>

<script>
const summary = document.getElementById("summary");
const agentsBody = document.getElementById("agents-body");
const channelsBody = document.getElementById("channels-body");
const capabilitiesBody = document.getElementById("capabilities-body");
const approvalsBody = document.getElementById("approvals-body");
const skillsBody = document.getElementById("skills-body");
const skillDetailPre = document.getElementById("skill-detail-pre");
const auditTrailSummary = document.getElementById("audit-trail-summary");
const auditTrailBody = document.getElementById("audit-trail-body");
const auditStatusFilter = document.getElementById("audit-status-filter");
const auditRoleFilter = document.getElementById("audit-role-filter");
const auditDetailMeta = document.getElementById("audit-detail-meta");
const auditInputPre = document.getElementById("audit-input-pre");
const auditPatchPre = document.getElementById("audit-patch-pre");
const auditErrorPre = document.getElementById("audit-error-pre");
const revisionsPre = document.getElementById("revisions-pre");
const tokenFromQuery = new URLSearchParams(window.location.search).get("token") || "";
let adminToken = localStorage.getItem("autoresearch_admin_token") || tokenFromQuery;
let agentFormMode = "create";
let editingAgentId = null;
let editingAgentStatus = "active";
let channelFormMode = "create";
let editingChannelId = null;
let editingChannelStatus = "active";
let selectedAuditEntryId = "";

function setAdminToken() {
  const input = prompt("请输入 Bearer Token（不含 Bearer 前缀）", adminToken || "");
  if (!input) return;
  adminToken = input.trim();
  localStorage.setItem("autoresearch_admin_token", adminToken);
  refreshAll();
}

function clearAdminToken() {
  adminToken = "";
  localStorage.removeItem("autoresearch_admin_token");
  summary.textContent = "已清除 token";
}

async function callApi(path, method = "GET", body = null) {
  if (!adminToken) {
    throw new Error("missing admin token; click 设置 Admin Token");
  }
  const headers = {"content-type": "application/json", "authorization": `Bearer ${adminToken}`};
  const res = await fetch(path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

function asJSON(value) {
  return JSON.stringify(value, null, 2);
}

function fmtDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString("zh-CN");
}

function fmtDuration(value) {
  if (value === null || value === undefined) return "-";
  if (value < 1000) return `${Math.round(value)} ms`;
  return `${(value / 1000).toFixed(value >= 10000 ? 0 : 1)} s`;
}

function compactList(values, limit = 2) {
  const items = (values || []).filter(Boolean);
  if (!items.length) return "-";
  const visible = items.slice(0, limit).join(", ");
  const extra = items.length - limit;
  return extra > 0 ? `${visible} +${extra}` : visible;
}

function csvToList(raw) {
  if (!raw) return [];
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function toInt(raw, fallback, minValue, maxValue) {
  const value = Number(raw);
  if (!Number.isFinite(value)) return fallback;
  return Math.min(maxValue, Math.max(minValue, Math.round(value)));
}

function resetAgentForm() {
  agentFormMode = "create";
  editingAgentId = null;
  editingAgentStatus = "active";
  document.getElementById("agent-form-title").textContent = "Agent 表单（新建）";
  document.getElementById("agent-form-name").value = "assistant-main";
  document.getElementById("agent-form-task").value = "general-task";
  document.getElementById("agent-form-timeout").value = "900";
  document.getElementById("agent-form-depth").value = "1";
  document.getElementById("agent-form-description").value = "default admin agent";
  document.getElementById("agent-form-prompt").value = "You are my primary autonomous agent.";
  document.getElementById("agent-form-channels").value = "telegram-main";
  document.getElementById("agent-form-actor").value = "admin-ui";
  document.getElementById("agent-form-append").checked = true;
  document.getElementById("agent-form-enabled").checked = true;
}

async function submitAgentForm() {
  const name = document.getElementById("agent-form-name").value.trim();
  const taskName = document.getElementById("agent-form-task").value.trim();
  const promptTemplate = document.getElementById("agent-form-prompt").value;
  if (!name || !taskName || !promptTemplate.trim()) {
    alert("name / task_name / prompt_template 为必填");
    return;
  }

  const actor = document.getElementById("agent-form-actor").value.trim() || "admin-ui";
  const channels = csvToList(document.getElementById("agent-form-channels").value);
  const timeout = toInt(document.getElementById("agent-form-timeout").value, 900, 1, 7200);
  const depth = toInt(document.getElementById("agent-form-depth").value, 1, 1, 10);
  const appendPrompt = document.getElementById("agent-form-append").checked;
  const enabled = document.getElementById("agent-form-enabled").checked;
  const description = document.getElementById("agent-form-description").value.trim();

  if (agentFormMode === "edit" && editingAgentId) {
    await callApi(`/api/v1/admin/agents/${editingAgentId}`, "PUT", {
      name,
      description,
      task_name: taskName,
      prompt_template: promptTemplate,
      default_timeout_seconds: timeout,
      default_generation_depth: depth,
      append_prompt: appendPrompt,
      channel_bindings: channels,
      metadata_updates: {},
      actor,
      reason: "manual edit from form",
    });
    const currentlyEnabled = editingAgentStatus === "active";
    if (enabled !== currentlyEnabled) {
      const op = enabled ? "activate" : "deactivate";
      await callApi(`/api/v1/admin/agents/${editingAgentId}/${op}`, "POST", {
        actor,
        reason: "toggle from form",
      });
    }
  } else {
    await callApi("/api/v1/admin/agents", "POST", {
      name,
      description,
      task_name: taskName,
      prompt_template: promptTemplate,
      default_timeout_seconds: timeout,
      default_generation_depth: depth,
      default_env: {},
      cli_args: [],
      command_override: null,
      append_prompt: appendPrompt,
      channel_bindings: channels,
      metadata: {},
      enabled,
      actor,
    });
  }

  await refreshAll();
  resetAgentForm();
}

function createAgent() {
  resetAgentForm();
  document.getElementById("agent-form-card").scrollIntoView({behavior: "smooth", block: "center"});
}

async function createAgentAdvancedJson() {
  const raw = prompt("输入 Agent JSON（create payload）", asJSON({
    name: "assistant-main",
    description: "default admin agent",
    task_name: "general-task",
    prompt_template: "You are my primary autonomous agent.",
    default_timeout_seconds: 900,
    default_generation_depth: 1,
    default_env: {},
    cli_args: [],
    command_override: null,
    append_prompt: true,
    channel_bindings: ["telegram-main"],
    metadata: {},
    enabled: true,
    actor: "admin-ui"
  }));
  if (!raw) return;
  await callApi("/api/v1/admin/agents", "POST", JSON.parse(raw));
  await refreshAll();
}

function agentRow(item) {
  const toggleOp = item.status === "active" ? "deactivate" : "activate";
  const toggleLabel = item.status === "active" ? "停用" : "启用";
  const encoded = encodeURIComponent(JSON.stringify(item));
  return `
    <tr>
      <td>${item.agent_id}</td>
      <td>${item.name}</td>
      <td>${item.task_name}</td>
      <td>${item.version}</td>
      <td><span class="pill ${item.status}">${item.status}</span></td>
      <td>${fmtDate(item.updated_at)}</td>
      <td>
        <div class="toolbar">
          <button onclick='editAgent("${encoded}")'>编辑</button>
          <button onclick='launchAgent("${item.agent_id}")'>启动</button>
          <button onclick='toggleAgent("${item.agent_id}", "${toggleOp}")'>${toggleLabel}</button>
          <button onclick='rollbackAgent("${item.agent_id}")'>回滚</button>
        </div>
      </td>
    </tr>`;
}

function channelRow(item) {
  const toggleOp = item.status === "active" ? "deactivate" : "activate";
  const toggleLabel = item.status === "active" ? "停用" : "启用";
  const encoded = encodeURIComponent(JSON.stringify(item));
  return `
    <tr>
      <td>${item.channel_id}</td>
      <td>${item.key}</td>
      <td>${item.provider}</td>
      <td>${item.has_secret ? "yes" : "no"}</td>
      <td>${item.version}</td>
      <td><span class="pill ${item.status}">${item.status}</span></td>
      <td>${fmtDate(item.updated_at)}</td>
      <td>
        <div class="toolbar">
          <button onclick='editChannel("${encoded}")'>编辑</button>
          <button onclick='toggleChannel("${item.channel_id}", "${toggleOp}")'>${toggleLabel}</button>
          <button onclick='rollbackChannel("${item.channel_id}")'>回滚</button>
        </div>
      </td>
    </tr>`;
}

function capabilityRow(item) {
  const provider = item.provider || {};
  const capabilityList = (provider.capabilities || []).join(", ") || "-";
  const skillList = (item.skills || []).map((skill) => skill.skill_key || skill.name).join(", ") || "-";
  const toolList = (item.tools || []).map((tool) => tool.name).join(", ") || "-";
  const readOps = [
    item.supports_calendar_query ? "calendar" : "",
    item.supports_github_search ? "github" : "",
  ].filter(Boolean).join(", ") || "-";
  return `
    <tr>
      <td>${provider.display_name || provider.provider_id || "-"}</td>
      <td>${provider.domain || "-"}</td>
      <td><span class="pill ${provider.status === "available" ? "active" : "inactive"}">${provider.status || "-"}</span></td>
      <td>${capabilityList}</td>
      <td>${skillList}</td>
      <td>${toolList}</td>
      <td>${readOps}</td>
    </tr>`;
}

function approvalRow(item) {
  return `
    <tr>
      <td>${item.approval_id}</td>
      <td>${item.status}</td>
      <td>${item.risk}</td>
      <td>${item.title}</td>
      <td>${item.telegram_uid || "-"}</td>
      <td>${item.source || "-"}</td>
      <td>${fmtDate(item.expires_at)}</td>
      <td>
        <div class="toolbar">
          <button onclick='decideApproval("${item.approval_id}", "approve")'>批准</button>
          <button class="btn-danger" onclick='decideApproval("${item.approval_id}", "reject")'>拒绝</button>
        </div>
      </td>
    </tr>`;
}

function flattenManagedSkillGroups(snapshot) {
  return (snapshot.groups || []).flatMap((group) => (group.installs || []).map((item) => ({
    ...item,
    status: item.status || group.status || "-"
  })));
}

function skillRow(item) {
  const ops = [
    `<button onclick='showSkillDetail("${item.install_id}")'>详情</button>`,
    item.status === "quarantined" ? `<button onclick='validateSkill("${item.install_id}")'>验证</button>` : "",
    item.status === "cold_validated" ? `<button onclick='requestSkillPromotion("${item.install_id}")'>提权</button>` : "",
  ].filter(Boolean).join("");
  return `
    <tr>
      <td>${item.install_id}</td>
      <td><span class="pill ${item.status === "promoted" ? "active" : "inactive"}">${item.status}</span></td>
      <td>${item.skill_id}</td>
      <td>${item.version}</td>
      <td>${item.requested_by || "-"}</td>
      <td>${fmtDate(item.updated_at)}</td>
      <td><div class="toolbar">${ops || "-"}</div></td>
    </tr>`;
}

function clearAuditDetail() {
  selectedAuditEntryId = "";
  auditDetailMeta.textContent = "点击单条记录查看输入、patch diff 和失败原因。";
  auditInputPre.textContent = "暂无";
  auditPatchPre.textContent = "暂无";
  auditErrorPre.textContent = "暂无";
}

function auditTrailRow(item) {
  const finalStatus = item.final_status || item.status || "-";
  const pillClass = ["failed", "blocked", "interrupted", "human_review", "stalled_no_progress"].includes(finalStatus) ? "inactive" : "active";
  return `
    <tr>
      <td>${fmtDate(item.recorded_at)}</td>
      <td>${item.agent_role} / ${item.source}</td>
      <td title="${item.title || item.run_id}">${item.run_id}</td>
      <td><span class="pill ${pillClass}">${finalStatus}</span></td>
      <td>${fmtDuration(item.duration_ms)}</td>
      <td>${item.files_changed || 0}</td>
      <td title="${(item.scope_paths || []).join("\\n")}">${compactList(item.scope_paths, 2)}</td>
      <td title="${(item.changed_paths || []).join("\\n")}">${compactList(item.changed_paths, 2)}</td>
      <td><button onclick='loadAuditDetail("${item.entry_id}")'>查看</button></td>
    </tr>`;
}

async function loadAuditDetail(entryId) {
  selectedAuditEntryId = entryId;
  auditDetailMeta.textContent = "加载详情中...";
  try {
    const detail = await callApi(`/api/v1/admin/audit-trail/${encodeURIComponent(entryId)}`);
    const entry = detail.entry || {};
    const detailLines = [
      `Role: ${entry.agent_role || "-"}`,
      `Source: ${entry.source || "-"}`,
      `Run: ${entry.run_id || "-"}`,
      `Title: ${entry.title || "-"}`,
      `Status: ${entry.final_status || entry.status || "-"}`,
      `Raw: ${entry.status || "-"}`,
      `Recorded: ${fmtDate(entry.recorded_at)}`,
      `First progress: ${fmtDuration(entry.first_progress_ms)}`,
      `First write: ${fmtDuration(entry.first_scoped_write_ms)}`,
      `First state: ${fmtDuration(entry.first_state_heartbeat_ms)}`,
      `Patch: ${entry.patch_uri || "-"}`,
      `Workspace: ${entry.isolated_workspace || "-"}`,
      detail.patch_truncated ? "Patch preview: truncated" : "Patch preview: full",
    ];
    auditDetailMeta.textContent = detailLines.join(" | ");
    auditInputPre.textContent = asJSON({
      prompt: detail.input_prompt || null,
      job_spec: detail.job_spec || {},
      worker_spec: detail.worker_spec || {},
      controlled_request: detail.controlled_request || {},
      raw_record: detail.raw_record || {},
    });
    auditPatchPre.textContent = detail.patch_text || (entry.patch_uri ? `Patch file: ${entry.patch_uri}` : "暂无 patch");
    auditErrorPre.textContent = detail.error_reason || detail.traceback
      ? [detail.error_reason || "no error reason", detail.traceback || ""].filter(Boolean).join("\\n\\n")
      : "无失败细节";
  } catch (err) {
    auditDetailMeta.textContent = `加载详情失败: ${err.message}`;
    auditInputPre.textContent = "加载失败";
    auditPatchPre.textContent = "加载失败";
    auditErrorPre.textContent = String(err);
  }
}

async function loadAuditTrail() {
  try {
    const params = new URLSearchParams();
    params.set("limit", "20");
    params.set("status_filter", auditStatusFilter.value || "all");
    params.set("agent_role", auditRoleFilter.value || "all");
    const snapshot = await callApi(`/api/v1/admin/audit-trail?${params.toString()}`);
    const items = snapshot.items || [];
    const stats = snapshot.stats || {};
    auditTrailBody.innerHTML = items.map(auditTrailRow).join("")
      || "<tr><td colspan='9'>暂无</td></tr>";
    auditTrailSummary.textContent =
      `Recent: ${items.length} | Success: ${stats.succeeded || 0} | Failed: ${stats.failed || 0} | Running: ${stats.running || 0} | Queued: ${stats.queued || 0} | Filter: ${(auditStatusFilter.value || "all")}/${(auditRoleFilter.value || "all")}`;
    if (selectedAuditEntryId && items.some((item) => item.entry_id === selectedAuditEntryId)) {
      await loadAuditDetail(selectedAuditEntryId);
    } else if (!selectedAuditEntryId) {
      clearAuditDetail();
    } else {
      clearAuditDetail();
      auditDetailMeta.textContent = "当前筛选结果不包含已选记录。";
    }
  } catch (err) {
    auditTrailSummary.textContent = `加载失败: ${err.message}`;
    auditTrailBody.innerHTML = "<tr><td colspan='9'>加载失败</td></tr>";
  }
}

async function refreshAll() {
  try {
    const [agents, channels, capabilitySnapshot, approvals, skillSnapshot] = await Promise.all([
      callApi("/api/v1/admin/agents"),
      callApi("/api/v1/admin/channels"),
      callApi("/api/v1/admin/capabilities"),
      callApi("/api/v1/admin/approvals?status=pending&limit=80"),
      callApi("/api/v1/admin/skills/status"),
    ]);
    const skillItems = flattenManagedSkillGroups(skillSnapshot);
    agentsBody.innerHTML = agents.map(agentRow).join("") || "<tr><td colspan='7'>暂无</td></tr>";
    channelsBody.innerHTML = channels.map(channelRow).join("") || "<tr><td colspan='8'>暂无</td></tr>";
    capabilitiesBody.innerHTML = (capabilitySnapshot.providers || []).map(capabilityRow).join("")
      || "<tr><td colspan='7'>暂无</td></tr>";
    approvalsBody.innerHTML = approvals.map(approvalRow).join("") || "<tr><td colspan='8'>暂无</td></tr>";
    skillsBody.innerHTML = skillItems.map(skillRow).join("") || "<tr><td colspan='7'>暂无</td></tr>";
    summary.textContent = `Agents: ${agents.length} | Channels: ${channels.length} | Providers: ${(capabilitySnapshot.providers || []).length} | Approvals: ${approvals.length} | Skills: ${skillItems.length} | API: /api/v1/admin`;
    await loadAuditTrail();
    await loadRevisions();
  } catch (err) {
    summary.textContent = `加载失败: ${err.message}`;
    capabilitiesBody.innerHTML = "<tr><td colspan='7'>加载失败</td></tr>";
    approvalsBody.innerHTML = "<tr><td colspan='8'>加载失败</td></tr>";
    skillsBody.innerHTML = "<tr><td colspan='7'>加载失败</td></tr>";
    auditTrailSummary.textContent = `加载失败: ${err.message}`;
    auditTrailBody.innerHTML = "<tr><td colspan='9'>加载失败</td></tr>";
    clearAuditDetail();
  }
}

async function showSkillDetail(installId) {
  try {
    const detail = await callApi(`/api/v1/admin/skills/${installId}`);
    skillDetailPre.textContent = asJSON(detail);
  } catch (err) {
    skillDetailPre.textContent = String(err);
  }
}

async function validateSkill(installId) {
  try {
    const detail = await callApi(`/api/v1/admin/skills/${installId}/validate`, "POST");
    skillDetailPre.textContent = asJSON(detail);
    await refreshAll();
  } catch (err) {
    alert(`验证失败: ${err.message}`);
  }
}

async function requestSkillPromotion(installId) {
  const telegramUid = prompt("Telegram UID（可空；若只配置了一个 allowed uid，可直接留空）", "");
  if (telegramUid === null) return;
  const note = prompt("审批备注（可空）", "");
  if (note === null) return;
  try {
    const result = await callApi(`/api/v1/admin/skills/${installId}/promote`, "POST", {
      telegram_uid: telegramUid.trim() || null,
      note: note.trim() || null,
      metadata: {source: "admin-ui"},
    });
    skillDetailPre.textContent = asJSON(result.install);
    alert(`已创建审批 ${result.approval.approval_id}${result.mini_app_url ? `\nMini App: ${result.mini_app_url}` : ""}`);
    await refreshAll();
  } catch (err) {
    alert(`提权申请失败: ${err.message}`);
  }
}

async function loadRevisions() {
  const targetType = document.getElementById("rev-type").value;
  const targetId = document.getElementById("rev-target").value.trim();
  const params = new URLSearchParams();
  params.set("limit", "80");
  if (targetType) params.set("target_type", targetType);
  if (targetId) params.set("target_id", targetId);
  try {
    const list = await callApi(`/api/v1/admin/revisions?${params.toString()}`);
    revisionsPre.textContent = asJSON(list);
  } catch (err) {
    revisionsPre.textContent = String(err);
  }
}

function editAgent(encodedItem) {
  const item = JSON.parse(decodeURIComponent(encodedItem));
  agentFormMode = "edit";
  editingAgentId = item.agent_id;
  editingAgentStatus = item.status;
  document.getElementById("agent-form-title").textContent = `Agent 表单（编辑: ${item.agent_id}）`;
  document.getElementById("agent-form-name").value = item.name || "";
  document.getElementById("agent-form-task").value = item.task_name || "";
  document.getElementById("agent-form-timeout").value = String(item.default_timeout_seconds || 900);
  document.getElementById("agent-form-depth").value = String(item.default_generation_depth || 1);
  document.getElementById("agent-form-description").value = item.description || "";
  document.getElementById("agent-form-prompt").value = item.prompt_template || "";
  document.getElementById("agent-form-channels").value = (item.channel_bindings || []).join(", ");
  document.getElementById("agent-form-actor").value = "admin-ui";
  document.getElementById("agent-form-append").checked = Boolean(item.append_prompt);
  document.getElementById("agent-form-enabled").checked = item.status === "active";
  document.getElementById("agent-form-card").scrollIntoView({behavior: "smooth", block: "center"});
}

async function toggleAgent(agentId, op) {
  await callApi(`/api/v1/admin/agents/${agentId}/${op}`, "POST", {actor: "admin-ui", reason: "toggle from ui"});
  await refreshAll();
}

async function rollbackAgent(agentId) {
  const version = prompt("回滚到哪个 version？", "1");
  if (!version) return;
  await callApi(`/api/v1/admin/agents/${agentId}/rollback`, "POST", {
    version: Number(version),
    actor: "admin-ui",
    reason: "manual rollback"
  });
  await refreshAll();
}

async function launchAgent(agentId) {
  const sessionInput = prompt("session_id（可空）", "");
  if (sessionInput === null) return;
  const promptInput = prompt("prompt_override（可空）", "");
  if (promptInput === null) return;
  const timeoutInput = prompt("timeout_seconds_override（可空）", "");
  if (timeoutInput === null) return;
  const depthInput = prompt("generation_depth_override（可空）", "");
  if (depthInput === null) return;

  const timeoutValue = timeoutInput.trim() ? toInt(timeoutInput.trim(), 900, 1, 7200) : null;
  const depthValue = depthInput.trim() ? toInt(depthInput.trim(), 1, 1, 10) : null;
  const run = await callApi(`/api/v1/admin/agents/${agentId}/launch`, "POST", {
    session_id: sessionInput.trim() || null,
    prompt_override: promptInput.trim() || null,
    timeout_seconds_override: timeoutValue,
    generation_depth_override: depthValue,
    env_overrides: {},
    metadata_updates: {trigger: "admin-ui"},
  });
  alert(`已启动 agent_run_id: ${run.agent_run_id}`);
}

async function createChannelAdvancedJson() {
  const raw = prompt("输入 Channel JSON（create payload）", asJSON({
    key: "telegram-main",
    display_name: "Telegram Main",
    provider: "telegram",
    endpoint_url: null,
    secret_ref: null,
    secret_value: null,
    allowed_chat_ids: [],
    allowed_user_ids: [],
    routing_policy: {},
    metadata: {},
    enabled: true,
    actor: "admin-ui"
  }));
  if (!raw) return;
  await callApi("/api/v1/admin/channels", "POST", JSON.parse(raw));
  await refreshAll();
}

async function quickCreateTelegramChannel() {
  const key = document.getElementById("tg-quick-key").value.trim() || "telegram-main";
  const token = document.getElementById("tg-quick-token").value.trim();
  const ids = csvToList(document.getElementById("tg-quick-ids").value);
  const actor = document.getElementById("tg-quick-actor").value.trim() || "admin-ui";

  if (!token) {
    alert("bot token 不能为空");
    return;
  }
  if (ids.length === 0) {
    alert("allowed ids 至少填一个");
    return;
  }

  const channels = await callApi("/api/v1/admin/channels");
  const existing = channels.find((item) => item.key === key);

  if (existing) {
    await callApi(`/api/v1/admin/channels/${existing.channel_id}`, "PUT", {
      display_name: existing.display_name || "Telegram Main",
      provider: "telegram",
      endpoint_url: existing.endpoint_url || null,
      secret_ref: existing.secret_ref || null,
      secret_value: token,
      clear_secret: false,
      allowed_chat_ids: ids,
      allowed_user_ids: ids,
      routing_policy: existing.routing_policy || {},
      metadata_updates: {quick_mode: "telegram"},
      actor,
      reason: "quick telegram update",
    });
    if (existing.status !== "active") {
      await callApi(`/api/v1/admin/channels/${existing.channel_id}/activate`, "POST", {
        actor,
        reason: "activate quick telegram channel",
      });
    }
  } else {
    await callApi("/api/v1/admin/channels", "POST", {
      key,
      display_name: "Telegram Main",
      provider: "telegram",
      endpoint_url: null,
      secret_ref: null,
      secret_value: token,
      allowed_chat_ids: ids,
      allowed_user_ids: ids,
      routing_policy: {quick_mode: "telegram"},
      metadata: {quick_mode: "telegram"},
      enabled: true,
      actor,
    });
  }

  await refreshAll();
  document.getElementById("tg-quick-token").value = "";
}

function resetChannelForm() {
  channelFormMode = "create";
  editingChannelId = null;
  editingChannelStatus = "active";
  document.getElementById("channel-form-title").textContent = "Channel 表单（新建）";
  document.getElementById("channel-form-key").value = "telegram-main";
  document.getElementById("channel-form-display").value = "Telegram Main";
  document.getElementById("channel-form-provider").value = "telegram";
  document.getElementById("channel-form-endpoint").value = "";
  document.getElementById("channel-form-secret-ref").value = "";
  document.getElementById("channel-form-secret-value").value = "";
  document.getElementById("channel-form-allowed-chat-ids").value = "";
  document.getElementById("channel-form-allowed-user-ids").value = "";
  document.getElementById("channel-form-actor").value = "admin-ui";
  document.getElementById("channel-form-enabled").checked = true;
}

async function submitChannelForm() {
  const key = document.getElementById("channel-form-key").value.trim();
  const displayName = document.getElementById("channel-form-display").value.trim();
  if (!key || !displayName) {
    alert("key / display_name 为必填");
    return;
  }

  const actor = document.getElementById("channel-form-actor").value.trim() || "admin-ui";
  const provider = document.getElementById("channel-form-provider").value || "telegram";
  const endpointUrl = document.getElementById("channel-form-endpoint").value.trim() || null;
  const secretRef = document.getElementById("channel-form-secret-ref").value.trim() || null;
  const secretValueRaw = document.getElementById("channel-form-secret-value").value;
  const secretValue = secretValueRaw && secretValueRaw.trim() ? secretValueRaw.trim() : null;
  const allowedChatIds = csvToList(document.getElementById("channel-form-allowed-chat-ids").value);
  const allowedUserIds = csvToList(document.getElementById("channel-form-allowed-user-ids").value);
  const enabled = document.getElementById("channel-form-enabled").checked;

  if (channelFormMode === "edit" && editingChannelId) {
    await callApi(`/api/v1/admin/channels/${editingChannelId}`, "PUT", {
      display_name: displayName,
      provider,
      endpoint_url: endpointUrl,
      secret_ref: secretRef,
      secret_value: secretValue,
      clear_secret: false,
      allowed_chat_ids: allowedChatIds,
      allowed_user_ids: allowedUserIds,
      routing_policy: {},
      metadata_updates: {},
      actor,
      reason: "manual edit from form",
    });
    const currentlyEnabled = editingChannelStatus === "active";
    if (enabled !== currentlyEnabled) {
      const op = enabled ? "activate" : "deactivate";
      await callApi(`/api/v1/admin/channels/${editingChannelId}/${op}`, "POST", {
        actor,
        reason: "toggle from form",
      });
    }
  } else {
    await callApi("/api/v1/admin/channels", "POST", {
      key,
      display_name: displayName,
      provider,
      endpoint_url: endpointUrl,
      secret_ref: secretRef,
      secret_value: secretValue,
      allowed_chat_ids: allowedChatIds,
      allowed_user_ids: allowedUserIds,
      routing_policy: {},
      metadata: {},
      enabled,
      actor,
    });
  }

  await refreshAll();
  resetChannelForm();
}

function createChannel() {
  resetChannelForm();
  document.getElementById("channel-form-card").scrollIntoView({behavior: "smooth", block: "center"});
}

function editChannel(encodedItem) {
  const item = JSON.parse(decodeURIComponent(encodedItem));
  channelFormMode = "edit";
  editingChannelId = item.channel_id;
  editingChannelStatus = item.status;
  document.getElementById("channel-form-title").textContent = `Channel 表单（编辑: ${item.channel_id}）`;
  document.getElementById("channel-form-key").value = item.key || "";
  document.getElementById("channel-form-display").value = item.display_name || "";
  document.getElementById("channel-form-provider").value = item.provider || "telegram";
  document.getElementById("channel-form-endpoint").value = item.endpoint_url || "";
  document.getElementById("channel-form-secret-ref").value = item.secret_ref || "";
  document.getElementById("channel-form-secret-value").value = "";
  document.getElementById("channel-form-allowed-chat-ids").value = (item.allowed_chat_ids || []).join(", ");
  document.getElementById("channel-form-allowed-user-ids").value = (item.allowed_user_ids || []).join(", ");
  document.getElementById("channel-form-actor").value = "admin-ui";
  document.getElementById("channel-form-enabled").checked = item.status === "active";
  document.getElementById("channel-form-card").scrollIntoView({behavior: "smooth", block: "center"});
}

async function toggleChannel(channelId, op) {
  await callApi(`/api/v1/admin/channels/${channelId}/${op}`, "POST", {actor: "admin-ui", reason: "toggle from ui"});
  await refreshAll();
}

async function rollbackChannel(channelId) {
  const version = prompt("回滚到哪个 version？", "1");
  if (!version) return;
  await callApi(`/api/v1/admin/channels/${channelId}/rollback`, "POST", {
    version: Number(version),
    actor: "admin-ui",
    reason: "manual rollback"
  });
  await refreshAll();
}

async function decideApproval(approvalId, op) {
  const note = prompt(`${op === "approve" ? "批准" : "拒绝"}备注（可空）`, "");
  if (note === null) return;
  const path = `/api/v1/admin/approvals/${approvalId}/${op}`;
  await callApi(path, "POST", {
    note: note.trim() || null,
    metadata: {source: "admin-ui"},
  });
  await refreshAll();
}

resetAgentForm();
resetChannelForm();
refreshAll();
</script>
</body>
</html>
"""
