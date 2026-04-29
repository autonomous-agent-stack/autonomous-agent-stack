from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, status

from autoresearch.api.dependencies import (
    get_admin_config_service,
    get_approval_store_service,
    get_capability_provider_registry,
    get_claude_agent_service,
    get_claude_session_record_service,
    get_github_issue_service,
    get_manager_agent_service,
    get_openclaw_compat_service,
    get_openclaw_memory_service,
    get_panel_access_service,
    get_telegram_notifier_service,
    get_worker_inventory_service,
    get_worker_registry_service,
    get_worker_scheduler_service,
)
from autoresearch.api.settings import load_telegram_settings
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.claude_session_records import ClaudeSessionRecordService
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.github_issue_service import GitHubIssueService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_inventory import WorkerInventoryService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    TelegramWebhookAck,
    WorkerQueueItemCreateRequest,
    WorkerTaskType,
)

from ._commands import (
    _handle_approve_command,
    _handle_help_command,
    _handle_memory_command,
    _handle_mode_command,
    _handle_reset_command,
    _handle_skills_command,
    _handle_status_query,
    _handle_task_command,
)
from ._extract import (
    _is_approve_command,
    _is_help_command,
    _is_memory_command,
    _is_mode_command,
    _is_reset_command,
    _is_skills_command,
    _is_status_query,
    _is_task_command,
    _safe_int,
)
from ._guard import _guard_webhook_replay_and_rate, _validate_secret_token
from ._handlers import (
    _classify_telegram_youtube_ingress,
    _handle_butler_excel_audit,
    _handle_telegram_youtube_autoflow,
)
from ._messages import _telegram_queue_ack_message, _utc_now
from ._policy import _evaluate_telegram_routing_policy, _resolve_telegram_session_identity
from ._session import (
    _build_task_name,
    _ensure_admin_channel_visibility,
    _find_or_create_telegram_session,
    _append_user_event,
    _resolve_contextual_followup_prompt,
)

router = APIRouter(prefix="/api/v1/gateway/telegram", tags=["gateway", "telegram"])
compat_router = APIRouter(tags=["gateway", "telegram", "compat"])
_X_BOOKMARK_KEYWORDS = (
    "书签",
    "bookmark",
    "twitter bookmark",
    "x bookmark",
    "推特书签",
    "x 书签",
)
_GITHUB_REPO_RE = re.compile(r"https?://github\.com/([^/\s]+)/([^/\s#?]+)", re.IGNORECASE)


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
    session_record_service: ClaudeSessionRecordService = Depends(get_claude_session_record_service),
) -> TelegramWebhookAck:
    return _handle_telegram_webhook(
        update=update,
        raw_request=raw_request,
        background_tasks=background_tasks,
        openclaw_service=openclaw_service,
        memory_service=memory_service,
        approval_service=approval_service,
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
        session_record_service=session_record_service,
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
    session_record_service: ClaudeSessionRecordService = Depends(get_claude_session_record_service),
) -> TelegramWebhookAck:
    return _handle_telegram_webhook(
        update=update,
        raw_request=raw_request,
        background_tasks=background_tasks,
        openclaw_service=openclaw_service,
        memory_service=memory_service,
        approval_service=approval_service,
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
        session_record_service=session_record_service,
    )


def _handle_telegram_webhook(
    *,
    update: dict[str, Any],
    raw_request: Request,
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    memory_service: OpenClawMemoryService,
    approval_service: ApprovalStoreService,
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
    session_record_service: ClaudeSessionRecordService,
) -> TelegramWebhookAck:
    from ._extract import _extract_telegram_message, _safe_str

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
            github_issue_service=github_issue_service,
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

    youtube_ingress_decision, youtube_source_url, youtube_rejection_reason = _classify_telegram_youtube_ingress(text)
    if youtube_ingress_decision != "skip":
        return _handle_telegram_youtube_autoflow(
            chat_id=chat_id,
            text=text,
            update=update,
            extracted=extracted,
            background_tasks=background_tasks,
            openclaw_service=openclaw_service,
            notifier=notifier,
            session_identity=session_identity,
            worker_scheduler=worker_scheduler,
            decision=youtube_ingress_decision,
            source_url=youtube_source_url,
            rejection_reason=youtube_rejection_reason,
        )

    # --- Butler intent router: check if message should go to a specialist agent ---
    from autoresearch.core.services.butler_router import ButlerTaskType
    from autoresearch.api.dependencies import get_butler_router, get_excel_audit_service

    butler = get_butler_router()
    butler_result = butler.classify(text)
    if butler_result.task_type == ButlerTaskType.EXCEL_AUDIT:
        return _handle_butler_excel_audit(
            chat_id=chat_id,
            update=update,
            extracted=extracted,
            text=text,
            background_tasks=background_tasks,
            notifier=notifier,
            session_identity=session_identity,
            butler_classification=butler_result,
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

    # Resolve preferred worker from sticky session record
    preferred_worker_id: str | None = None
    sticky_record = session_record_service.get_by_session_key(session_identity.session_key)
    if sticky_record and sticky_record.worker_id:
        preferred_worker_id = sticky_record.worker_id

    # Build claude_runtime task payload (optionally routed to Hermes via runtime_id)
    dispatch_runtime = telegram_settings.telegram_dispatch_runtime_id
    channel_route = _resolve_channel_route(extracted=extracted)
    if _should_force_hermes_for_bookmark_task(
        text=text,
        butler_task_type=str(getattr(butler_result.task_type, "value", butler_result.task_type)),
    ):
        dispatch_runtime = "hermes"
    hermes_fragment = telegram_settings.hermes_metadata_fragment_for_worker()
    metadata: dict[str, Any] = {}
    if hermes_fragment:
        metadata["hermes"] = hermes_fragment
    metadata["channel_route"] = channel_route
    agent_contract = _build_butler_worker_contract(
        text=text,
        butler_task_type=str(getattr(butler_result.task_type, "value", butler_result.task_type)),
        execution_mode=telegram_settings.telegram_hermes_execution_mode if dispatch_runtime == "hermes" else "oneshot",
    )
    metadata.update(agent_contract)
    image_urls = [] if dispatch_runtime == "hermes" else list(extracted.get("images") or [])

    prompt_for_worker = resolved_prompt
    if dispatch_runtime == "hermes" and telegram_settings.hermes_append_eof_instruction:
        prompt_for_worker = (
            f"{resolved_prompt}\n\n---\n"
            "[系统] 全部工作完成后，请在输出的最后一行仅写：EOF（无其它字符）。\n"
            "[System] When fully finished, print a single final line containing only: EOF"
        )

    runtime_payload: dict[str, Any] = {
        "session_id": session.session_id,
        "session_key": session_identity.session_key,
        "assistant_id": session_identity.assistant_id,
        "chat_id": chat_id,
        "message_thread_id": extracted.get("message_thread_id"),
        "is_topic_message": extracted.get("is_topic_message", False),
        "reply_to_message_id": extracted.get("reply_to_message_id"),
        "prompt": prompt_for_worker,
        "task_name": _build_task_name(chat_id, update, extracted),
        "actor_user_id": session_identity.actor.user_id,
        "actor_role": session_identity.actor.role.value,
        "actor_username": session_identity.actor.username,
        "timeout_seconds": max(1, min(telegram_settings.timeout_seconds, 7200)),
        "work_dir": str(telegram_settings.work_dir) if telegram_settings.work_dir else None,
        "agent_name": telegram_settings.agent_name,
        "cli_args": telegram_settings.claude_args or [],
        "command_override": telegram_settings.command_override,
        "skill_names": [],
        "images": image_urls,
        "preferred_worker_id": preferred_worker_id,
        "source": "telegram_webhook",
        "scope": session_identity.scope.value,
        "chat_type": session_identity.chat_context.chat_type.value,
        "runtime_id": dispatch_runtime,
    }
    if dispatch_runtime == "hermes":
        runtime_payload["execution_mode"] = telegram_settings.telegram_hermes_execution_mode
    if metadata:
        runtime_payload["metadata"] = metadata

    queue_priority = int(agent_contract.get("priority", 0))
    queue_max_retries = int(agent_contract.get("max_retries", 2))
    queue_metadata = {
        "session_key": session_identity.session_key,
        "preferred_worker_id": preferred_worker_id,
        "chat_id": chat_id,
        "channel_route": channel_route,
        **agent_contract,
    }
    if dispatch_runtime == "hermes" and telegram_settings.telegram_hermes_execution_mode == "interactive":
        queue_metadata.setdefault("interactive_lease_ttl_seconds", 900)

    queue_item = worker_scheduler.enqueue(WorkerQueueItemCreateRequest(
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload=runtime_payload,
        requested_by=session_identity.actor.user_id,
        priority=queue_priority,
        max_retries=queue_max_retries,
        metadata=queue_metadata,
    ))

    # Notify user that task is queued (sync so we capture message_id for worker editMessageText)
    thread_id_int = _safe_int(extracted.get("message_thread_id"))
    if notifier.enabled:
        ack_text = _telegram_queue_ack_message(
            task_name=str(runtime_payload["task_name"]),
            run_id=str(queue_item.run_id),
            worker_brand=telegram_settings.telegram_worker_display_name,
            runtime_id=str(runtime_payload.get("runtime_id") or "claude"),
            agent_name=str(runtime_payload.get("agent_name") or ""),
        )
        ack_message_id = notifier.send_message_get_message_id(
            chat_id=chat_id,
            text=ack_text,
            message_thread_id=thread_id_int,
        )
        if ack_message_id is not None:
            worker_scheduler.merge_queue_metadata(
                queue_item.run_id,
                {
                    "telegram_queue_ack_message_id": ack_message_id,
                    # Worker skips direct Telegram; API edits the same ack bubble with the
                    # full completion card after report_run (same bot = 管家界面).
                    "telegram_completion_via_api": True,
                },
            )

    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        agent_run_id=None,
        metadata={
            "run_id": queue_item.run_id,
            "task_name": runtime_payload["task_name"],
            "routed_to": "worker_queue",
            "preferred_worker_id": preferred_worker_id,
            "channel_route": channel_route,
        },
    )


def _should_force_hermes_for_bookmark_task(*, text: str, butler_task_type: str) -> bool:
    if butler_task_type != "content_kb":
        return False
    normalized = text.strip().lower()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in _X_BOOKMARK_KEYWORDS)


def _build_butler_worker_contract(*, text: str, butler_task_type: str, execution_mode: str) -> dict[str, Any]:
    repo = _extract_github_repo(text)
    target_agent = "butler_orchestrator"
    action = butler_task_type
    priority = 1
    max_retries = 2
    if butler_task_type == "github_admin" or repo:
        target_agent = _select_github_target_agent(repo)
        action = "github_ops.pr_ops" if "pr" in text.lower() else "github_ops.issue_ops"
        priority = 8
    elif butler_task_type == "youtube":
        target_agent = "youtube_ops"
        action = "youtube_ops.build_digest"
        priority = 5
    elif butler_task_type == "content_kb":
        target_agent = "content_kb"
        action = "content_kb.ingest"
        priority = 4
    if execution_mode == "interactive":
        max_retries = 1
    out: dict[str, Any] = {
        "target_agent": target_agent,
        "detected_task_type": butler_task_type,
        "action": action,
        "priority": priority,
        "max_retries": max_retries,
        "execution_mode": execution_mode,
    }
    if repo:
        out["repo"] = repo
    return out


def _extract_github_repo(text: str) -> str | None:
    match = _GITHUB_REPO_RE.search(text)
    if not match:
        return None
    owner = match.group(1).strip()
    repo = match.group(2).strip().removesuffix(".git")
    return f"{owner}/{repo}" if owner and repo else None


def _select_github_target_agent(repo: str | None) -> str:
    # Empty allowlists mean account A is the default operational profile.
    return "github_ops_accountA"


def _resolve_channel_route(*, extracted: dict[str, Any]) -> str:
    chat_type_raw = str(extracted.get("chat_type") or "").strip().lower()
    if chat_type_raw in {"group", "supergroup", "channel"}:
        return "group_channel"
    return "private_channel"
