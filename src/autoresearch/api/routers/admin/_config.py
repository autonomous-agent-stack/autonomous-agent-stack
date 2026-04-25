from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from autoresearch.api.dependencies import (
    get_admin_auth_service,
    get_admin_config_service,
    get_agent_audit_trail_service,
    get_capability_provider_registry,
    get_claude_agent_service,
)
from autoresearch.api.routers.admin._auth import _require_admin_high_risk, _require_admin_read, _require_admin_write
from autoresearch.core.adapters import CapabilityProviderRegistry, CalendarAdapter, GitHubAdapter, MCPProvider, SkillProvider
from autoresearch.core.services.admin_auth import AdminAccessClaims
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.agent_audit_trail import AgentAuditTrailService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.shared.models import (
    AdminAgentAuditTrailDetailRead,
    AdminAgentAuditTrailSnapshotRead,
    AdminAgentConfigCreateRequest,
    AdminAgentConfigRead,
    AdminAgentConfigUpdateRequest,
    AdminAgentLaunchRequest,
    AdminCapabilityProviderInventoryRead,
    AdminCapabilitySnapshotRead,
    AdminCapabilityToolRead,
    AdminChannelConfigCreateRequest,
    AdminChannelConfigRead,
    AdminChannelConfigUpdateRequest,
    AdminConfigRevisionRead,
    AdminConfigRollbackRequest,
    AdminConfigStatusChangeRequest,
    AdminTokenIssueRequest,
    AdminTokenRead,
    CapabilityProviderSummaryRead,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    utc_now,
)


def register_config_routes(router: APIRouter) -> None:
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

    @router.post("/auth/token", response_model=AdminTokenRead)
    def issue_admin_token(
        payload: AdminTokenIssueRequest,
        auth_service: Any = Depends(get_admin_auth_service),
        bootstrap_key: str | None = Depends(lambda: None),
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

    # Agent config endpoints
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

    # Channel config endpoints
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

    # Audit trail endpoints
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

    # Revision endpoints
    @router.get("/revisions", response_model=list[AdminConfigRevisionRead])
    def list_revisions(
        target_type: Literal["agent", "channel"] | None = None,
        target_id: str | None = None,
        limit: int = Query(default=100, ge=1, le=1000),
        access: AdminAccessClaims = Depends(_require_admin_read),
        service: AdminConfigService = Depends(get_admin_config_service),
    ) -> list[AdminConfigRevisionRead]:
        return service.list_revisions(target_type=target_type, target_id=target_id, limit=limit)
