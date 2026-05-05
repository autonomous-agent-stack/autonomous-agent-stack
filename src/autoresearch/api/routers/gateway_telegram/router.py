from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from autoresearch.api.dependencies import (
    get_admin_config_service,
    get_approval_decision_service,
    get_approval_store_service,
    get_butler_dispatch_center,
    get_capability_provider_registry,
    get_claude_agent_service,
    get_control_plane_service,
    get_github_issue_service,
    get_manager_agent_service,
    get_openclaw_compat_service,
    get_openclaw_memory_service,
    get_panel_access_service,
    get_session_event_service,
    get_telegram_notifier_service,
    get_worker_inventory_service,
    get_worker_registry_service,
    get_worker_scheduler_service,
)
from autoresearch.api.settings import load_telegram_settings
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.approval_decisions import ApprovalDecisionService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.adapters import CapabilityProviderRegistry
from autoresearch.core.services.butler_dispatch import ButlerDispatchCenter
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.control_plane.butler_bridge import (
    ButlerControlPlaneRouteRequest,
    route_butler_message,
)
from autoresearch.control_plane.contracts import ControlPlaneTaskStatus
from autoresearch.control_plane.service import ControlPlaneService
from autoresearch.core.services.github_issue_service import GitHubIssueService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.telegram_completion_format import TELEGRAM_MARKDOWN_V2_PARSE_MODE
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_inventory import WorkerInventoryService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    OpenClawSessionEventAppendRequest,
    TelegramWebhookAck,
)

from ._commands import (
    _handle_approve_command,
    _handle_cancel_command,
    _handle_help_command,
    _handle_memory_command,
    _handle_mode_command,
    _handle_reset_command,
    _handle_retry_command,
    _handle_skills_command,
    _handle_status_query,
    _handle_task_command,
)
from ._extract import (
    _is_approve_command,
    _is_cancel_command,
    _is_help_command,
    _is_memory_command,
    _is_mode_command,
    _is_reset_command,
    _is_retry_command,
    _is_skills_command,
    _is_status_query,
    _is_task_command,
    _safe_int,
)
from ._guard import _guard_webhook_replay_and_rate, _validate_secret_token
from ._handlers import (
    _classify_telegram_youtube_ingress,
)
from ._messages import _telegram_queue_ack_message
from ._policy import _evaluate_telegram_routing_policy, _resolve_telegram_session_identity
from ._session import (
    _ensure_admin_channel_visibility,
    _find_or_create_telegram_session,
    _append_user_event,
    _resolve_contextual_followup_prompt,
)

router = APIRouter(prefix="/api/v1/gateway/telegram", tags=["gateway", "telegram"])
compat_router = APIRouter(tags=["gateway", "telegram", "compat"])


@router.get("/health", tags=["gateway"])
def telegram_gateway_health() -> dict[str, str]:
    return {"status": "ok"}


@router.post(
    "/webhook",
    response_model=TelegramWebhookAck,
    status_code=status.HTTP_200_OK,
)
def telegram_webhook(
    update: dict[str, Any],
    raw_request: Request,
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
    memory_service: OpenClawMemoryService = Depends(get_openclaw_memory_service),
    approval_service: ApprovalStoreService = Depends(get_approval_store_service),
    approval_decision_service: ApprovalDecisionService = Depends(get_approval_decision_service),
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
    manager_service: ManagerAgentService = Depends(get_manager_agent_service),
    github_issue_service: GitHubIssueService = Depends(get_github_issue_service),
    capability_registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
    panel_access_service: PanelAccessService = Depends(get_panel_access_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
    admin_config_service: AdminConfigService = Depends(get_admin_config_service),
    worker_registry: WorkerRegistryService = Depends(get_worker_registry_service),
    worker_inventory: WorkerInventoryService = Depends(get_worker_inventory_service),
    worker_scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
    dispatch_center: ButlerDispatchCenter = Depends(get_butler_dispatch_center),
    control_plane_service: ControlPlaneService = Depends(get_control_plane_service),
    session_event_service: SessionEventService = Depends(get_session_event_service),
) -> TelegramWebhookAck:
    return _handle_telegram_webhook(
        update=update,
        raw_request=raw_request,
        background_tasks=background_tasks,
        openclaw_service=openclaw_service,
        memory_service=memory_service,
        approval_service=approval_service,
        approval_decision_service=approval_decision_service,
        agent_service=agent_service,
        manager_service=manager_service,
        github_issue_service=github_issue_service,
        capability_registry=capability_registry,
        panel_access_service=panel_access_service,
        notifier=notifier,
        admin_config_service=admin_config_service,
        worker_registry=worker_registry,
        worker_inventory=worker_inventory,
        worker_scheduler=worker_scheduler,
        dispatch_center=dispatch_center,
        control_plane_service=control_plane_service,
        session_event_service=session_event_service,
    )


@compat_router.post(
    "/telegram/webhook",
    response_model=TelegramWebhookAck,
    status_code=status.HTTP_200_OK,
)
def legacy_telegram_webhook(
    update: dict[str, Any],
    raw_request: Request,
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
    memory_service: OpenClawMemoryService = Depends(get_openclaw_memory_service),
    approval_service: ApprovalStoreService = Depends(get_approval_store_service),
    approval_decision_service: ApprovalDecisionService = Depends(get_approval_decision_service),
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
    manager_service: ManagerAgentService = Depends(get_manager_agent_service),
    github_issue_service: GitHubIssueService = Depends(get_github_issue_service),
    capability_registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
    panel_access_service: PanelAccessService = Depends(get_panel_access_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
    admin_config_service: AdminConfigService = Depends(get_admin_config_service),
    worker_registry: WorkerRegistryService = Depends(get_worker_registry_service),
    worker_inventory: WorkerInventoryService = Depends(get_worker_inventory_service),
    worker_scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
    dispatch_center: ButlerDispatchCenter = Depends(get_butler_dispatch_center),
    control_plane_service: ControlPlaneService = Depends(get_control_plane_service),
    session_event_service: SessionEventService = Depends(get_session_event_service),
) -> TelegramWebhookAck:
    return _handle_telegram_webhook(
        update=update,
        raw_request=raw_request,
        background_tasks=background_tasks,
        openclaw_service=openclaw_service,
        memory_service=memory_service,
        approval_service=approval_service,
        approval_decision_service=approval_decision_service,
        agent_service=agent_service,
        manager_service=manager_service,
        github_issue_service=github_issue_service,
        capability_registry=capability_registry,
        panel_access_service=panel_access_service,
        notifier=notifier,
        admin_config_service=admin_config_service,
        worker_registry=worker_registry,
        worker_inventory=worker_inventory,
        worker_scheduler=worker_scheduler,
        dispatch_center=dispatch_center,
        control_plane_service=control_plane_service,
        session_event_service=session_event_service,
    )


def _handle_telegram_webhook(
    *,
    update: dict[str, Any],
    raw_request: Request,
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    memory_service: OpenClawMemoryService,
    approval_service: ApprovalStoreService,
    approval_decision_service: ApprovalDecisionService,
    agent_service: ClaudeAgentService,
    manager_service: ManagerAgentService,
    github_issue_service: GitHubIssueService,
    capability_registry: CapabilityProviderRegistry,
    panel_access_service: PanelAccessService,
    notifier: TelegramNotifierService,
    admin_config_service: AdminConfigService,
    worker_registry: WorkerRegistryService,
    worker_inventory: WorkerInventoryService,
    worker_scheduler: WorkerSchedulerService,
    dispatch_center: ButlerDispatchCenter,
    control_plane_service: ControlPlaneService,
    session_event_service: SessionEventService,
) -> TelegramWebhookAck:
    from ._extract import _extract_telegram_message

    _validate_secret_token(raw_request)
    _guard_webhook_replay_and_rate(update)

    extracted = _extract_telegram_message(update)
    if extracted is None:
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            reason="unsupported update type",
        )

    chat_id = extracted["chat_id"]
    text = extracted["text"]
    if chat_id is None:
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            reason="missing chat id",
        )
    if not text:
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            reason="empty message text",
        )

    telegram_settings = load_telegram_settings()
    session_identity = _resolve_telegram_session_identity(
        extracted=extracted,
        telegram_settings=telegram_settings,
        openclaw_service=openclaw_service,
    )
    routing_rejection_reason = _evaluate_telegram_routing_policy(
        extracted=extracted,
        telegram_settings=telegram_settings,
        session_identity=session_identity,
    )
    if routing_rejection_reason is not None:
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            reason=routing_rejection_reason,
            metadata={
                "source": "telegram_routing_policy",
                "scope": session_identity.scope.value,
                "session_key": session_identity.session_key,
                "chat_type": session_identity.chat_context.chat_type.value,
            },
        )

    _ensure_admin_channel_visibility(
        admin_config_service=admin_config_service,
        chat_id=chat_id,
    )

    if _is_status_query(text):
        return _handle_status_query(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            openclaw_service=openclaw_service,
            agent_service=agent_service,
            memory_service=memory_service,
            capability_registry=capability_registry,
            panel_access_service=panel_access_service,
            notifier=notifier,
            session_identity=session_identity,
            worker_registry=worker_registry,
            worker_inventory=worker_inventory,
        )

    if _is_help_command(text):
        return _handle_help_command(
            chat_id=chat_id,
            update=update,
            background_tasks=background_tasks,
            notifier=notifier,
            session_identity=session_identity,
        )

    if _is_task_command(text):
        return _handle_task_command(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            openclaw_service=openclaw_service,
            approval_service=approval_service,
            manager_service=manager_service,
            github_issue_service=github_issue_service,
            notifier=notifier,
            session_identity=session_identity,
        )

    if _is_approve_command(text):
        return _handle_approve_command(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            approval_service=approval_service,
            approval_decision_service=approval_decision_service,
            control_plane_service=control_plane_service,
            github_issue_service=github_issue_service,
            worker_scheduler=worker_scheduler,
            notifier=notifier,
            session_identity=session_identity,
        )

    if _is_mode_command(text):
        return _handle_mode_command(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            openclaw_service=openclaw_service,
            notifier=notifier,
            session_identity=session_identity,
        )

    if _is_skills_command(text):
        return _handle_skills_command(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            notifier=notifier,
            capability_registry=capability_registry,
        )

    if _is_reset_command(text):
        return _handle_reset_command(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            openclaw_service=openclaw_service,
            notifier=notifier,
            session_identity=session_identity,
        )

    if _is_cancel_command(text):
        return _handle_cancel_command(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            worker_scheduler=worker_scheduler,
            control_plane_service=control_plane_service,
            notifier=notifier,
            session_identity=session_identity,
        )

    if _is_retry_command(text):
        return _handle_retry_command(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            worker_scheduler=worker_scheduler,
            notifier=notifier,
            session_identity=session_identity,
        )

    if _is_memory_command(text):
        return _handle_memory_command(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            openclaw_service=openclaw_service,
            memory_service=memory_service,
            notifier=notifier,
            session_identity=session_identity,
        )

    youtube_ingress_decision, _, youtube_rejection_reason = _classify_telegram_youtube_ingress(text)
    if youtube_ingress_decision == "reject":
        return _handle_telegram_youtube_rejection(
            chat_id=chat_id,
            text=text,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            openclaw_service=openclaw_service,
            notifier=notifier,
            session_identity=session_identity,
            reason=youtube_rejection_reason,
        )

    session = _find_or_create_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
        background_tasks=background_tasks,
        notifier=notifier,
    )
    resolved_prompt = _resolve_contextual_followup_prompt(
        session=session,
        text=text,
    )

    _append_user_event(
        openclaw_service=openclaw_service,
        session=session,
        text=text,
        update=update,
        extracted=extracted,
        session_identity=session_identity,
    )

    return _handle_v2_butler_task(
        chat_id=chat_id,
        update=update,
        extracted=extracted,
        text=resolved_prompt,
        background_tasks=background_tasks,
        openclaw_service=openclaw_service,
        notifier=notifier,
        session_identity=session_identity,
        worker_scheduler=worker_scheduler,
        dispatch_center=dispatch_center,
        control_plane_service=control_plane_service,
        session_event_service=session_event_service,
        telegram_worker_display_name=telegram_settings.telegram_worker_display_name,
        default_runtime_id=telegram_settings.telegram_dispatch_runtime_id,
        hermes_execution_mode=telegram_settings.telegram_hermes_execution_mode,
        append_hermes_eof_instruction=telegram_settings.hermes_append_eof_instruction,
        session_id=session.session_id,
    )


def _handle_telegram_youtube_rejection(
    *,
    chat_id: str,
    text: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    session_identity,
    reason: str | None,
) -> TelegramWebhookAck:
    session = _find_or_create_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
        background_tasks=background_tasks,
        notifier=notifier,
    )
    _append_user_event(
        openclaw_service=openclaw_service,
        session=session,
        text=text,
        update=update,
        extracted=extracted,
        session_identity=session_identity,
    )
    resolved_reason = reason or "消息里必须只包含 1 条合法的 YouTube URL。"
    metadata = {
        "source": "telegram_youtube_autoflow",
        "status": "rejected",
        "reason": resolved_reason,
        "chat_id": chat_id,
        "session_key": session_identity.session_key,
        "scope": session_identity.scope.value,
    }
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content="youtube autoflow rejected",
            metadata=metadata,
        ),
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=f"YouTube 自动流已拒绝。\nYouTube autoflow rejected.\n\n{resolved_reason}",
            message_thread_id=_safe_int(extracted.get("message_thread_id")),
        )
    return TelegramWebhookAck(
        accepted=False,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        reason=resolved_reason,
        metadata=metadata,
    )


def _handle_v2_butler_task(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    text: str,
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    session_identity,
    worker_scheduler: WorkerSchedulerService,
    dispatch_center: ButlerDispatchCenter,
    control_plane_service: ControlPlaneService,
    session_event_service: SessionEventService,
    telegram_worker_display_name: str,
    default_runtime_id: str,
    hermes_execution_mode: str,
    append_hermes_eof_instruction: bool,
    session_id: str,
) -> TelegramWebhookAck:
    requested_by = session_identity.actor.user_id or str(extracted.get("from_user_id") or chat_id)
    route_request = ButlerControlPlaneRouteRequest(
        message=text,
        session_id=session_id,
        requested_by=requested_by,
        metadata={
            "source": "telegram_gateway",
            "chat_id": chat_id,
            "message_id": extracted.get("message_id"),
            "message_thread_id": extracted.get("message_thread_id"),
            "is_topic_message": extracted.get("is_topic_message", False),
            "reply_to_message_id": extracted.get("reply_to_message_id"),
            "session_key": session_identity.session_key,
            "assistant_id": session_identity.assistant_id,
            "scope": session_identity.scope.value,
            "chat_type": session_identity.chat_context.chat_type.value,
            "actor_role": session_identity.actor.role.value,
            "actor_user_id": session_identity.actor.user_id,
            "actor_username": session_identity.actor.username,
        },
    )
    routed = route_butler_message(
        route_request,
        dispatch_center=dispatch_center,
        session_events=session_event_service,
        capabilities=control_plane_service.list_capabilities(),
        default_runtime_id=default_runtime_id,
        hermes_execution_mode=hermes_execution_mode,
    )
    if routed.task_request.capability_id == "hermes_openclaw" and append_hermes_eof_instruction:
        prompt = (
            f"{routed.task_request.intent or text}\n\n---\n"
            "[系统] 全部工作完成后，请在输出的最后一行仅写：EOF（无其它字符）。\n"
            "[System] When fully finished, print a single final line containing only: EOF"
        )
        routed = routed.model_copy(
            update={
                "task_request": routed.task_request.model_copy(
                    update={
                        "intent": prompt,
                        "parameters": {
                            **routed.task_request.parameters,
                            "message": prompt,
                            "request_text": prompt,
                        },
                    }
                )
            }
        )
    task = control_plane_service.create_task(routed.task_request)

    thread_id = _safe_int(extracted.get("message_thread_id"))
    target_agent = str(task.parameters.get("target_agent") or "")
    target_agents = [
        str(item).strip()
        for item in task.parameters.get("target_agents", [])
        if str(item).strip()
    ] if isinstance(task.parameters.get("target_agents"), list) else []
    if task.run_id:
        queue_metadata = {
            "telegram_completion_via_api": True,
            "chat_id": chat_id,
            "message_thread_id": extracted.get("message_thread_id"),
            "session_key": session_identity.session_key,
            "control_plane_task_id": task.task_id,
            "control_plane_session_id": task.session_id,
            "capability_id": task.capability_id,
            "target_agent": target_agent,
            "target_agents": target_agents or ([target_agent] if target_agent else []),
            "telegram_display_primary_agent": target_agent,
            "telegram_display_agent_names": target_agents or ([target_agent] if target_agent else []),
        }
        if notifier.enabled:
            ack_text = _telegram_queue_ack_message(
                task_name=task.name,
                run_id=task.run_id,
                worker_brand=telegram_worker_display_name,
                runtime_id=task.capability_id,
                agent_name=target_agent,
                agent_names=target_agents,
            )
            ack_message_id = notifier.send_message_get_message_id(
                chat_id=chat_id,
                text=ack_text,
                message_thread_id=thread_id,
                parse_mode=TELEGRAM_MARKDOWN_V2_PARSE_MODE,
            )
            if ack_message_id is not None:
                queue_metadata["telegram_queue_ack_message_id"] = ack_message_id
        worker_scheduler.merge_queue_metadata(task.run_id, queue_metadata)
    elif notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=_control_plane_task_ack_text(task),
            message_thread_id=thread_id,
        )

    openclaw_service.update_metadata(
        session_id=session_id,
        metadata_updates={
            "latest_control_plane_task_id": task.task_id,
            "latest_control_plane_task_status": task.status.value,
            "latest_control_plane_capability_id": task.capability_id,
            "latest_control_plane_approval_id": task.approval_id,
            "latest_control_plane_run_id": task.run_id,
        },
    )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session_id,
        agent_run_id=None,
        metadata={
            "source": "telegram_control_plane_v2",
            "routed_to": "control_plane_v2",
            "control_plane_task_id": task.task_id,
            "capability_id": task.capability_id,
            "status": task.status.value,
            "approval_id": task.approval_id,
            "run_id": task.run_id,
            "butler_dispatch_source": routed.dispatch_decision.source.value,
            "butler_dispatch_route": routed.dispatch_decision.route.value,
        },
    )


def _control_plane_task_ack_text(task) -> str:
    if task.status == ControlPlaneTaskStatus.AWAITING_APPROVAL:
        return (
            "任务需要审批后执行。\n"
            "Task requires approval before execution.\n\n"
            f"task: {task.task_id}\n"
            f"capability: {task.capability_id}\n"
            f"approval: {task.approval_id}\n"
            "console: /control-plane"
        )
    return (
        "任务已提交到 Control Plane v2。\n"
        "Task submitted to Control Plane v2.\n\n"
        f"task: {task.task_id}\n"
        f"capability: {task.capability_id}\n"
        f"status: {task.status.value}\n"
        f"run: {task.run_id or '-'}"
    )
