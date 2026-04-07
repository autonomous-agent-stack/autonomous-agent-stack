from __future__ import annotations

from datetime import datetime, timezone
import inspect
import re
import threading
import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

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
    get_worker_registry_service,
    get_worker_scheduler_service,
)
from autoresearch.api.settings import load_panel_settings, load_runtime_settings, load_telegram_settings
from autoresearch.core.adapters import CapabilityDomain, CapabilityProviderRegistry, SkillProvider
from autoresearch.core.runtime_identity import get_runtime_identity
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.github_issue_service import GitHubIssueRead, GitHubIssueService
from autoresearch.core.services.group_access import GroupAccessManager
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.standby_youtube_autoflow import (
    extract_urls_from_text,
    extract_youtube_urls_from_text,
)
from autoresearch.core.services.telegram_identity import (
    TelegramSessionIdentityRead,
    build_telegram_session_identity,
)
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.claude_session_records import ClaudeSessionRecordService
from autoresearch.shared.models import (
    AdminChannelConfigCreateRequest,
    AdminChannelConfigUpdateRequest,
    ActorRole,
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalRisk,
    ApprovalStatus,
    AssistantScope,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    JobStatus,
    OpenClawMemoryBundleRead,
    OpenClawMemoryRecordCreateRequest,
    OpenClawMemoryRecordRead,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSessionRead,
    ChatType,
    StandbyYouTubeAutoflowRequest,
    TelegramWebhookAck,
    WorkerMode,
    WorkerQueueItemCreateRequest,
    WorkerTaskType,
)
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead, ManagerDispatchRequest


router = APIRouter(prefix="/api/v1/gateway/telegram", tags=["gateway", "telegram"])
compat_router = APIRouter(tags=["gateway", "telegram", "compat"])
_UPDATE_REPLAY_TTL_SECONDS = 600
_RATE_WINDOW_SECONDS = 60
_RATE_MAX_REQUESTS_PER_CHAT = 30
_SEEN_UPDATES: dict[str, float] = {}
_CHAT_RATE_WINDOWS: dict[str, list[float]] = {}
_GUARD_LOCK = threading.Lock()
_SHORT_AFFIRMATIVE_RE = re.compile(r"^(好|好的|好啊|好呀|行|行啊|行呀|可以|可以啊|可以呀|开始|开始吧|来吧|继续|确认|是|是的|嗯|嗯嗯)\s*[.!。！？~～]*$")
_YOUTUBE_PROCESS_CONFIRM_RE = re.compile(r"(现在)?触发(?:一次)?(?:视频)?(?:字幕)?处理")


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
    worker_scheduler: WorkerSchedulerService,
    session_record_service: ClaudeSessionRecordService,
) -> TelegramWebhookAck:
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

    # Build claude_runtime task payload
    runtime_payload = {
        "session_id": session.session_id,
        "session_key": session_identity.session_key,
        "assistant_id": session_identity.assistant_id,
        "chat_id": chat_id,
        "message_thread_id": extracted.get("message_thread_id"),
        "is_topic_message": extracted.get("is_topic_message", False),
        "reply_to_message_id": extracted.get("reply_to_message_id"),
        "prompt": resolved_prompt,
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
        "images": extracted.get("images", []),
        "preferred_worker_id": preferred_worker_id,
        "source": "telegram_webhook",
        "scope": session_identity.scope.value,
        "chat_type": session_identity.chat_context.chat_type.value,
    }

    queue_item = worker_scheduler.enqueue(WorkerQueueItemCreateRequest(
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload=runtime_payload,
        requested_by=session_identity.actor.user_id,
        metadata={
            "session_key": session_identity.session_key,
            "preferred_worker_id": preferred_worker_id,
            "chat_id": chat_id,
        },
    ))

    # Notify user that task is queued
    thread_id_int = _safe_int(extracted.get("message_thread_id"))
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=f"已接收，已排队：{runtime_payload['task_name']} (run: {queue_item.run_id})",
            message_thread_id=thread_id_int,
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
        },
    )


def _validate_secret_token(raw_request: Request) -> None:
    expected = (load_telegram_settings().secret_token or "").strip()
    if _is_production_env() and not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="telegram secret token is required in production",
        )
    if not expected:
        return
    provided = raw_request.headers.get("x-telegram-bot-api-secret-token", "").strip()
    if provided != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid telegram secret token")


def _is_production_env() -> bool:
    return load_runtime_settings().is_production


def _extract_telegram_message(update: dict[str, Any]) -> dict[str, Any] | None:
    message = update.get("message") or update.get("edited_message")
    if isinstance(message, dict):
        chat = message.get("chat", {})
        from_user = message.get("from", {})
        
        # 提取图片信息
        photos = message.get("photo", [])
        image_urls = []
        if photos:
            # 获取最大尺寸的图片（最后一个）
            largest_photo = photos[-1] if photos else None
            if largest_photo:
                file_id = largest_photo.get("file_id")
                if file_id:
                    # 构造图片 URL（需要 Bot Token）
                    bot_token = load_telegram_settings().bot_token or ""
                    if bot_token:
                        image_urls.append(f"telegram://{file_id}")
        
        return {
            "chat_id": _safe_str(chat.get("id")),
            "chat_type": _safe_str(chat.get("type")),
            "text": (message.get("text") or message.get("caption") or "").strip(),
            "message_id": message.get("message_id"),
            "username": from_user.get("username"),
            "from_user_id": _safe_int(from_user.get("id")),
            "from_id": from_user.get("id"),
            "reply_to_user_id": _safe_int(((message.get("reply_to_message") or {}).get("from") or {}).get("id")),
            "reply_to_username": _safe_str(((message.get("reply_to_message") or {}).get("from") or {}).get("username")),
            "reply_to_is_bot": bool(((message.get("reply_to_message") or {}).get("from") or {}).get("is_bot")),
            "message_thread_id": message.get("message_thread_id"),
            "is_topic_message": bool(message.get("is_topic_message", False)),
            "reply_to_message_id": message.get("reply_to_message", {}).get("message_id") if isinstance(message.get("reply_to_message"), dict) else None,
            "raw_type": "message",
            "images": image_urls,
        }

    callback = update.get("callback_query")
    if isinstance(callback, dict):
        callback_message = callback.get("message", {})
        chat = callback_message.get("chat", {})
        from_user = callback.get("from", {})
        return {
            "chat_id": _safe_str(chat.get("id")),
            "chat_type": _safe_str(chat.get("type")),
            "text": (callback.get("data") or "").strip(),
            "message_id": callback_message.get("message_id"),
            "username": from_user.get("username"),
            "from_user_id": _safe_int(from_user.get("id")),
            "from_id": from_user.get("id"),
            "reply_to_user_id": None,
            "reply_to_username": None,
            "reply_to_is_bot": False,
            "message_thread_id": callback_message.get("message_thread_id"),
            "is_topic_message": bool(callback_message.get("is_topic_message", False)),
            "reply_to_message_id": None,
            "raw_type": "callback_query",
        }
    return None


def _guard_webhook_replay_and_rate(update: dict[str, Any]) -> None:
    update_id = _safe_int(update.get("update_id"))
    if update_id is None:
        return
    message = update.get("message") or update.get("edited_message") or {}
    chat_id = _safe_str((message.get("chat") or {}).get("id"))
    now_ts = time.time()

    with _GUARD_LOCK:
        _gc_guard_state(now_ts)
        update_key = str(update_id)
        if update_key in _SEEN_UPDATES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="duplicate telegram update rejected",
            )
        _SEEN_UPDATES[update_key] = now_ts

        if not chat_id:
            return
        window = _CHAT_RATE_WINDOWS.setdefault(chat_id, [])
        window_start = now_ts - _RATE_WINDOW_SECONDS
        window[:] = [ts for ts in window if ts >= window_start]
        if len(window) >= _RATE_MAX_REQUESTS_PER_CHAT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="telegram webhook rate limit exceeded",
            )
        window.append(now_ts)


def _evaluate_telegram_routing_policy(
    *,
    extracted: dict[str, Any],
    telegram_settings,
    session_identity: TelegramSessionIdentityRead,
) -> str | None:
    actor_user_id = session_identity.actor.user_id
    allowed_uids = _effective_allowed_uids(telegram_settings)
    if allowed_uids and actor_user_id not in allowed_uids:
        return "telegram user is not allowlisted"

    chat_type = session_identity.chat_context.chat_type
    if chat_type not in {ChatType.GROUP, ChatType.SUPERGROUP}:
        return None

    chat_id = session_identity.chat_context.chat_id
    if telegram_settings.internal_groups and chat_id not in telegram_settings.internal_groups:
        return "telegram group is not allowlisted"
    if _message_addresses_bot(extracted=extracted, telegram_settings=telegram_settings):
        return None
    return "group message ignored without explicit bot address"


def _effective_allowed_uids(telegram_settings) -> set[str]:
    return set(telegram_settings.allowed_uids) | set(telegram_settings.owner_uids) | set(telegram_settings.partner_uids)


def _message_addresses_bot(*, extracted: dict[str, Any], telegram_settings) -> bool:
    raw_type = str(extracted.get("raw_type") or "").strip().lower()
    if raw_type == "callback_query":
        return True

    text = str(extracted.get("text") or "").strip()
    if not text:
        return False
    if text.startswith("/"):
        return True
    if bool(extracted.get("reply_to_is_bot")):
        return True

    normalized_text = text.lower()
    normalized_usernames = {
        item.strip().lower().lstrip("@")
        for item in telegram_settings.bot_usernames
        if str(item).strip()
    }
    if not normalized_usernames:
        return False
    return any(f"@{username}" in normalized_text for username in normalized_usernames)


def _gc_guard_state(now_ts: float) -> None:
    replay_cutoff = now_ts - _UPDATE_REPLAY_TTL_SECONDS
    expired_updates = [key for key, ts in _SEEN_UPDATES.items() if ts < replay_cutoff]
    for key in expired_updates:
        _SEEN_UPDATES.pop(key, None)

    empty_chats: list[str] = []
    rate_cutoff = now_ts - _RATE_WINDOW_SECONDS
    for chat_id, timestamps in _CHAT_RATE_WINDOWS.items():
        timestamps[:] = [ts for ts in timestamps if ts >= rate_cutoff]
        if not timestamps:
            empty_chats.append(chat_id)
    for chat_id in empty_chats:
        _CHAT_RATE_WINDOWS.pop(chat_id, None)


def _classify_telegram_youtube_ingress(text: str) -> tuple[str, str | None, str | None]:
    normalized_text = text.strip()
    if not normalized_text:
        return ("skip", None, None)

    all_urls = extract_urls_from_text(normalized_text)
    youtube_urls = extract_youtube_urls_from_text(normalized_text)
    has_youtube_hint = "youtu" in normalized_text.lower()

    if not all_urls:
        if has_youtube_hint:
            return ("reject", None, "未找到合法的 YouTube URL。")
        return ("skip", None, None)

    if len(all_urls) > 1:
        if youtube_urls or has_youtube_hint:
            return ("reject", None, "当前只支持每条消息提交 1 条 YouTube 链接。")
        return ("skip", None, None)

    only_url = all_urls[0]
    if len(youtube_urls) == 1 and youtube_urls[0] == only_url:
        return ("accept", only_url, None)
    if has_youtube_hint:
        return ("reject", None, "消息里必须只包含 1 条合法的 YouTube URL。")
    return ("skip", None, None)

def _handle_butler_excel_audit(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    text: str,
    background_tasks: BackgroundTasks,
    notifier: TelegramNotifierService,
    session_identity: _TelegramSessionIdentity,
    butler_classification: Any,
) -> TelegramWebhookAck:
    """Route detected Excel audit intent to ExcelAuditService."""
    from autoresearch.shared.excel_audit_contract import ExcelAuditCreateRequest
    from autoresearch.api.dependencies import get_excel_audit_service

    attachments = butler_classification.extracted_params.get("attachments", [])

    try:
        service = get_excel_audit_service()
        req = ExcelAuditCreateRequest(
            task_brief=text,
            source_files=attachments,
        )
        result = service.create_and_execute(req)

        summary_lines = [
            "📊 Excel 核对完成",
            f"状态: {result.status.value}",
            f"检查行数: {result.result.rows_checked}",
            f"差异行数: {result.result.rows_mismatched}",
            f"差异金额: {result.result.mismatch_amount_total:.2f}",
        ]
        if result.artifacts:
            summary_lines.append("")
            summary_lines.append("报告文件:")
            for a in result.artifacts:
                summary_lines.append(f"  - {a}")
        if result.error:
            summary_lines.append(f"错误: {result.error}")

        reply_text = "\n".join(summary_lines)
    except Exception as exc:
        reply_text = f"Excel 核对失败: {exc}"

    if notifier.enabled:
        thread_id = _safe_int(extracted.get("message_thread_id"))
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=reply_text,
            message_thread_id=thread_id,
        )

    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        reason="butler routed to excel_audit",
        metadata={
            "butler_task_type": "excel_audit",
            "butler_confidence": butler_classification.confidence,
        },
    )


def _handle_telegram_youtube_autoflow(
    *,
    chat_id: str,
    text: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
    worker_scheduler: WorkerSchedulerService,
    decision: str,
    source_url: str | None,
    rejection_reason: str | None,
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

    metadata = {
        "source": "telegram_youtube_autoflow",
        "chat_id": chat_id,
        "update_id": _safe_int(update.get("update_id")),
        "message_id": extracted.get("message_id"),
        "username": extracted.get("username"),
        "scope": session_identity.scope.value,
        "session_key": session_identity.session_key,
        "assistant_id": session_identity.assistant_id,
        "chat_type": session_identity.chat_context.chat_type.value,
        "actor_role": session_identity.actor.role.value,
        "actor_user_id": session_identity.actor.user_id,
        "session_id": session.session_id,
    }

    if decision != "accept" or source_url is None:
        reason = rejection_reason or "消息里必须只包含 1 条合法的 YouTube URL。"
        _record_telegram_youtube_autoflow_status(
            openclaw_service=openclaw_service,
            session_id=session.session_id,
            content="youtube autoflow rejected",
            metadata={
                **metadata,
                "status": "rejected",
                "reason": reason,
            },
        )
        if notifier.enabled:
            background_tasks.add_task(
                notifier.send_message,
                chat_id=chat_id,
                text=_build_telegram_youtube_autoflow_message(
                    status="rejected",
                    reason=reason,
                ),
            )
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            session_id=session.session_id,
            reason=reason,
            metadata={
                **metadata,
                "status": "rejected",
            },
        )

    requested_by = session_identity.actor.user_id or _safe_str(extracted.get("from_user_id")) or chat_id
    request_payload = StandbyYouTubeAutoflowRequest(
        source_url=source_url,
        input_text=text,
        requested_by=requested_by,
        source="telegram_gateway",
        metadata=metadata,
    )

    try:
        queued_run = worker_scheduler.enqueue(
            WorkerQueueItemCreateRequest(
                task_name="telegram_youtube_autoflow",
                task_type=WorkerTaskType.YOUTUBE_AUTOFLOW,
                payload=request_payload.model_dump(mode="json"),
                requested_by=requested_by,
                metadata={
                    **metadata,
                    "source_url": source_url,
                },
            )
        )
    except Exception as exc:
        reason = str(exc).strip() or "failed to enqueue youtube_autoflow"
        _record_telegram_youtube_autoflow_status(
            openclaw_service=openclaw_service,
            session_id=session.session_id,
            content="youtube autoflow enqueue failed",
            metadata={
                **metadata,
                "status": "failed",
                "reason": reason,
                "source_url": source_url,
            },
        )
        if notifier.enabled:
            background_tasks.add_task(
                notifier.send_message,
                chat_id=chat_id,
                text=_build_telegram_youtube_autoflow_message(
                    status="failed",
                    reason=reason,
                    source_url=source_url,
                ),
            )
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            session_id=session.session_id,
            reason=reason,
            metadata={
                **metadata,
                "status": "failed",
                "source_url": source_url,
            },
        )

    _record_telegram_youtube_autoflow_status(
        openclaw_service=openclaw_service,
        session_id=session.session_id,
        content=f"youtube autoflow queued: {queued_run.run_id}",
        metadata={
            **metadata,
            "status": "accepted",
            "run_id": queued_run.run_id,
            "task_type": queued_run.task_type.value,
            "source_url": source_url,
        },
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=_build_telegram_youtube_autoflow_message(
                status="accepted",
                run_id=queued_run.run_id,
                source_url=source_url,
            ),
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            **metadata,
            "status": "accepted",
            "run_id": queued_run.run_id,
            "task_type": queued_run.task_type.value,
            "source_url": source_url,
        },
    )


def _record_telegram_youtube_autoflow_status(
    *,
    openclaw_service: OpenClawCompatService,
    session_id: str,
    content: str,
    metadata: dict[str, Any],
) -> None:
    openclaw_service.append_event(
        session_id=session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=content,
            metadata=metadata,
        ),
    )
    openclaw_service.update_metadata(
        session_id=session_id,
        metadata_updates={
            "latest_telegram_youtube_autoflow_status": metadata.get("status"),
            "latest_telegram_youtube_autoflow_reason": metadata.get("reason"),
            "latest_telegram_youtube_autoflow_run_id": metadata.get("run_id"),
            "latest_telegram_youtube_autoflow_task_type": metadata.get("task_type"),
            "latest_telegram_youtube_autoflow_source_url": metadata.get("source_url"),
        },
    )


def _build_telegram_youtube_autoflow_message(
    *,
    status: str,
    reason: str | None = None,
    run_id: str | None = None,
    source_url: str | None = None,
) -> str:
    lines = [
        "[YouTube Autoflow]",
        f"status: {status}",
    ]
    if run_id:
        lines.append(f"run: {run_id}")
    if source_url:
        lines.append(f"url: {source_url}")
    if reason:
        lines.extend(["", reason])
    return _truncate_telegram_text("\n".join(lines).strip())


def _append_user_event(
    openclaw_service: OpenClawCompatService,
    session: OpenClawSessionRead,
    text: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    session_identity: TelegramSessionIdentityRead,
) -> None:
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="user",
            content=text,
            metadata={
                "source": "telegram_webhook",
                "chat_id": extracted.get("chat_id"),
                "message_id": extracted.get("message_id"),
                "username": extracted.get("username"),
                "update_id": _safe_int(update.get("update_id")),
                "update_type": extracted.get("raw_type"),
                "scope": session_identity.scope.value,
                "session_key": session_identity.session_key,
                "chat_type": session_identity.chat_context.chat_type.value,
                "actor_role": session_identity.actor.role.value,
                "actor_user_id": session_identity.actor.user_id,
            },
        ),
    )


def _resolve_contextual_followup_prompt(
    *,
    session: OpenClawSessionRead,
    text: str,
) -> str:
    normalized_text = text.strip()
    if not _SHORT_AFFIRMATIVE_RE.fullmatch(normalized_text):
        return text

    last_assistant_message = _latest_assistant_message(session)
    if not last_assistant_message:
        return text

    if _YOUTUBE_PROCESS_CONFIRM_RE.search(last_assistant_message) and (
        "?" in last_assistant_message or "？" in last_assistant_message
    ):
        return (
            "请按我上一条确认，立即触发一次今天的视频字幕处理。"
            "如果当前系统仍是手动触发模式，就直接执行可用的手动处理入口，"
            "并返回本次实际执行结果，不要再重复问我要不要开始。"
        )

    return text


def _latest_assistant_message(session: OpenClawSessionRead) -> str | None:
    for event in reversed(session.events):
        role = event.get("role") if isinstance(event, dict) else None
        content = event.get("content") if isinstance(event, dict) else None
        if role == "assistant" and isinstance(content, str):
            normalized = content.strip()
            if normalized:
                return normalized
    return None


def _find_or_create_telegram_session(
    *,
    openclaw_service: OpenClawCompatService,
    chat_id: str,
    session_identity: TelegramSessionIdentityRead,
    background_tasks: BackgroundTasks,
    notifier: TelegramNotifierService,
) -> OpenClawSessionRead:
    session = _find_existing_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
    )
    if session is None:
        session = openclaw_service.create_session(
            OpenClawSessionCreateRequest(
                channel="telegram",
                external_id=chat_id,
                title=_build_session_title(chat_id=chat_id, session_identity=session_identity),
                scope=session_identity.scope,
                session_key=session_identity.session_key,
                assistant_id=session_identity.assistant_id,
                actor=session_identity.actor,
                chat_context=session_identity.chat_context,
                metadata={
                    "source": "telegram_webhook",
                    "created_at": _utc_now(),
                    "identity_version": 1,
                    "scope": session_identity.scope.value,
                    "session_key": session_identity.session_key,
                    "assistant_id": session_identity.assistant_id,
                    "chat_type": session_identity.chat_context.chat_type.value,
                    "actor_role": session_identity.actor.role.value,
                    "actor_user_id": session_identity.actor.user_id,
                    "telegram_mode_preference": session_identity.scope.value,
                },
            )
        )

    return _sync_session_runtime_identity(
        openclaw_service=openclaw_service,
        session=session,
        background_tasks=background_tasks,
        notifier=notifier,
        chat_id=chat_id,
    )


def _sync_session_runtime_identity(
    *,
    openclaw_service: OpenClawCompatService,
    session: OpenClawSessionRead,
    background_tasks: BackgroundTasks,
    notifier: TelegramNotifierService,
    chat_id: str,
) -> OpenClawSessionRead:
    runtime = get_runtime_identity()
    current_fingerprint = runtime["runtime_fingerprint"]
    current_display = runtime["runtime_display"]
    previous_fingerprint = str(session.metadata.get("runtime_fingerprint") or "").strip()
    previous_display = str(session.metadata.get("runtime_display") or "").strip() or previous_fingerprint
    now_iso = _utc_now()
    switched = bool(previous_fingerprint and previous_fingerprint != current_fingerprint)

    metadata_updates: dict[str, Any] = {
        **runtime,
        "runtime_last_seen_at": now_iso,
    }
    if switched:
        metadata_updates.update(
            {
                "runtime_switched_at": now_iso,
                "runtime_previous_display": previous_display,
            }
        )

    updated_session = openclaw_service.update_metadata(
        session.session_id,
        metadata_updates=metadata_updates,
    )
    if not switched:
        return updated_session

    openclaw_service.append_event(
        session_id=updated_session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"runtime switched: {previous_display} -> {current_display}",
            metadata={
                "source": "telegram_runtime_switch",
                "previous_runtime_display": previous_display,
                "previous_runtime_fingerprint": previous_fingerprint,
                **runtime,
            },
        ),
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=_build_runtime_switch_message(
                previous_display=previous_display,
                current_display=current_display,
            ),
        )
    refreshed = openclaw_service.get_session(updated_session.session_id)
    return refreshed or updated_session


def _build_runtime_switch_message(*, previous_display: str, current_display: str) -> str:
    return _truncate_telegram_text(
        "\n".join(
            [
                "[Runtime]",
                "执行环境已切换",
                f"from: {previous_display}",
                f"to: {current_display}",
            ]
        )
    )


def _handle_task_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    approval_service: ApprovalStoreService,
    manager_service: ManagerAgentService,
    github_issue_service: GitHubIssueService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    task_query, approval_requested = _parse_task_command(extracted["text"])
    if not task_query:
        message_text = (
            "用法:\n"
            "/task <需求>\n"
            "/task --approve <需求>\n"
            "/task issue <owner/repo#123 | #123 | GitHub issue URL> [补充说明]"
        )
        if notifier.enabled:
            background_tasks.add_task(notifier.send_message, chat_id=chat_id, text=message_text)
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            reason="missing task payload",
            metadata={"source": "telegram_manager_task", "scope": session_identity.scope.value},
        )

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
        text=extracted["text"],
        update=update,
        extracted=extracted,
        session_identity=session_identity,
    )

    issue: GitHubIssueRead | None = None
    manager_prompt = task_query
    task_source = "prompt"
    operator_note = ""
    issue_reference: str | None = None
    issue_url: str | None = None
    approval_granted = approval_requested and _can_telegram_task_self_approve(
        session_identity=session_identity
    )

    if approval_requested and not approval_granted and notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text="`--approve` 仅对 owner/partner 生效；本次仍按常规审批流执行。",
        )

    if task_query.casefold().startswith("issue "):
        issue_reference, operator_note = _extract_issue_task_parts(task_query)
        try:
            issue = github_issue_service.fetch_issue(issue_reference)
        except Exception as exc:
            return TelegramWebhookAck(
                accepted=False,
                update_id=_safe_int(update.get("update_id")),
                chat_id=chat_id,
                session_id=session.session_id,
                reason=str(exc),
                metadata={
                    "source": "telegram_manager_task",
                    "task_source": "issue",
                    "scope": session_identity.scope.value,
                },
            )
        manager_prompt = github_issue_service.build_manager_prompt(issue, operator_note=operator_note or None)
        task_source = "issue"
        issue_reference = issue.reference.display
        issue_url = issue.url

    dispatch = manager_service.create_dispatch(
        ManagerDispatchRequest(
            prompt=manager_prompt,
            approval_granted=approval_granted,
            auto_dispatch=True,
            metadata={
                "source": "telegram_manager_task",
                "task_source": task_source,
                "telegram_chat_id": chat_id,
                "telegram_user_id": session_identity.actor.user_id,
                "telegram_session_id": session.session_id,
                "telegram_scope": session_identity.scope.value,
                "raw_task_query": task_query,
                "operator_note": operator_note,
                "github_issue_reference": issue_reference,
                "github_issue_url": issue_url,
                "github_issue_title": issue.title if issue is not None else None,
                "approval_requested": approval_requested,
                "approval_granted": approval_granted,
                "approval_source": "telegram_task_flag" if approval_granted else None,
            },
        )
    )
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"manager dispatch queued: {dispatch.dispatch_id}",
            metadata={
                "source": "telegram_manager_task",
                "dispatch_id": dispatch.dispatch_id,
                "task_source": task_source,
                "issue_reference": issue_reference,
            },
        ),
    )
    openclaw_service.set_status(
        session_id=session.session_id,
        status=JobStatus.QUEUED,
        metadata_updates={"latest_manager_dispatch_id": dispatch.dispatch_id},
    )

    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=_build_manager_dispatch_queued_message(dispatch, issue_reference=issue_reference),
        )

    background_tasks.add_task(
        _execute_manager_dispatch_and_notify,
        manager_service=manager_service,
        approval_service=approval_service,
        openclaw_service=openclaw_service,
        notifier=notifier,
        chat_id=chat_id,
        session_id=session.session_id,
        approval_uid=session_identity.actor.user_id or chat_id,
        assistant_scope=session_identity.scope,
        dispatch_id=dispatch.dispatch_id,
        issue_reference=issue_reference,
        issue_url=issue_url,
        issue_title=issue.title if issue is not None else None,
    )

    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            "source": "telegram_manager_task",
            "dispatch_id": dispatch.dispatch_id,
            "task_source": task_source,
            "issue_reference": issue_reference,
            "issue_url": issue_url,
            "scope": session_identity.scope.value,
        },
    )


def _handle_memory_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    memory_service: OpenClawMemoryService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    session = _find_or_create_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
        background_tasks=background_tasks,
        notifier=notifier,
    )
    memory_content = _extract_memory_content(extracted["text"])
    if not memory_content:
        bundle = memory_service.bundle_for_session(session.session_id)
        if notifier.enabled:
            background_tasks.add_task(
                notifier.send_message,
                chat_id=chat_id,
                text="\n".join(_build_memory_summary_lines(bundle)),
            )
        return TelegramWebhookAck(
            accepted=True,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            session_id=session.session_id,
            metadata={
                "source": "telegram_memory_summary",
                "scope": session.scope.value,
                "session_key": session.session_key,
                "personal_memory_count": len(bundle.personal_memories),
                "shared_memory_count": len(bundle.shared_memories),
            },
        )

    record = memory_service.remember_for_session(
        session.session_id,
        OpenClawMemoryRecordCreateRequest(
            content=memory_content,
            source="telegram_explicit_memory",
            metadata={
                "chat_id": chat_id,
                "update_id": _safe_int(update.get("update_id")),
                "message_id": extracted.get("message_id"),
                "chat_type": session_identity.chat_context.chat_type.value,
            },
        ),
    )
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"memory stored: {record.scope.value}",
            metadata={
                "memory_id": record.memory_id,
                "scope": record.scope.value,
                "source": record.source,
            },
        ),
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=f"记忆已保存到 {record.scope.value}: {record.memory_id}",
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            "source": "telegram_memory_store",
            "memory_id": record.memory_id,
            "scope": record.scope.value,
            "session_key": session.session_key,
        },
    )


def _handle_skills_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    notifier: TelegramNotifierService,
    capability_registry: CapabilityProviderRegistry,
) -> TelegramWebhookAck:
    skill_query = _extract_skill_query(extracted["text"])
    skill_providers = _list_skill_providers(capability_registry)
    catalogs = [(provider_id, provider.list_skills()) for provider_id, provider in skill_providers]
    total_skills = sum(len(catalog.skills) for _, catalog in catalogs)

    if skill_query:
        detail = _find_skill_detail(skill_query=skill_query, skill_providers=skill_providers)
        if detail is None:
            message_text = f"未找到 skill: {skill_query}"
        else:
            message_text = _build_skill_detail_message(provider_id=detail[0], skill=detail[1])
    else:
        message_text = _build_skills_catalog_message(catalogs)

    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=message_text,
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        metadata={
            "source": "telegram_skills_query",
            "skill_query": skill_query or None,
            "skill_provider_count": len(skill_providers),
            "skill_count": total_skills,
        },
    )


def _handle_reset_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    existing_session = _find_existing_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
    )

    previous_session_id: str | None = None
    if existing_session is not None:
        previous_session_id = existing_session.session_id
        existing_metadata = dict(existing_session.metadata)
        existing_metadata.update(
            {
                "reset_at": _utc_now(),
                "reset_source": "telegram_command",
                "archived_session_key": existing_session.session_key,
            }
        )
        archived_session_key = (
            f"{existing_session.session_key}#archived:{int(time.time())}"
            if existing_session.session_key
            else None
        )
        archived_session = existing_session.model_copy(
            update={
                "session_key": archived_session_key,
                "status": JobStatus.INTERRUPTED,
                "updated_at": datetime.now(timezone.utc),
                "metadata": existing_metadata,
            }
        )
        openclaw_service.save_session(archived_session)

    session = openclaw_service.create_session(
        OpenClawSessionCreateRequest(
            channel="telegram",
            external_id=chat_id,
            title=_build_session_title(chat_id=chat_id, session_identity=session_identity),
            scope=session_identity.scope,
            session_key=session_identity.session_key,
            assistant_id=session_identity.assistant_id,
            actor=session_identity.actor,
            chat_context=session_identity.chat_context,
            metadata={
                "source": "telegram_reset",
                "created_at": _utc_now(),
                "reset_from_session_id": previous_session_id,
                "scope": session_identity.scope.value,
                "session_key": session_identity.session_key,
                "assistant_id": session_identity.assistant_id,
                "chat_type": session_identity.chat_context.chat_type.value,
                "actor_role": session_identity.actor.role.value,
                "actor_user_id": session_identity.actor.user_id,
                "telegram_mode_preference": session_identity.scope.value,
            },
        )
    )
    session = _sync_session_runtime_identity(
        openclaw_service=openclaw_service,
        session=session,
        background_tasks=background_tasks,
        notifier=notifier,
        chat_id=chat_id,
    )
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content="session reset via telegram",
            metadata={
                "source": "telegram_reset",
                "previous_session_id": previous_session_id,
            },
        ),
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=(
                f"会话已重置。\nnew_session: {session.session_id}"
                + (f"\nprevious_session: {previous_session_id}" if previous_session_id else "")
            ),
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            "source": "telegram_reset",
            "previous_session_id": previous_session_id,
            "scope": session.scope.value,
            "session_key": session.session_key,
        },
    )


def _handle_mode_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    target_scope = _extract_mode_target(extracted["text"])
    chat_type = session_identity.chat_context.chat_type

    if chat_type != ChatType.PRIVATE:
        message_text = f"当前 chat_type={chat_type.value}，群组或频道固定为 shared 模式。"
        if notifier.enabled:
            background_tasks.add_task(notifier.send_message, chat_id=chat_id, text=message_text)
        return TelegramWebhookAck(
            accepted=True,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            metadata={
                "source": "telegram_mode_query",
                "scope": session_identity.scope.value,
                "chat_type": chat_type.value,
                "switch_allowed": False,
            },
        )

    if target_scope is None:
        message_text = (
            f"当前模式: {session_identity.scope.value}\n"
            "用法:\n"
            "- /mode personal\n"
            "- /mode shared"
        )
        if notifier.enabled:
            background_tasks.add_task(notifier.send_message, chat_id=chat_id, text=message_text)
        return TelegramWebhookAck(
            accepted=True,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            metadata={
                "source": "telegram_mode_query",
                "scope": session_identity.scope.value,
                "switch_allowed": True,
            },
        )

    target_identity = build_telegram_session_identity(
        extracted,
        load_telegram_settings(),
        scope_override=target_scope,
    )
    session = _find_or_create_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=target_identity,
        background_tasks=background_tasks,
        notifier=notifier,
    )
    session = openclaw_service.update_metadata(
        session.session_id,
        {
            "telegram_mode_preference": target_scope.value,
            "mode_switched_at": _utc_now(),
            "mode_switched_from": session_identity.scope.value,
        },
    )
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"mode selected: {target_scope.value}",
            metadata={
                "source": "telegram_mode_command",
                "scope": target_scope.value,
                "previous_scope": session_identity.scope.value,
            },
        ),
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=(
                f"模式已切换到 {target_scope.value}。\n"
                f"session: {session.session_id}\n"
                f"session_key: {session.session_key}"
            ),
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            "source": "telegram_mode_switch",
            "scope": session.scope.value,
            "session_key": session.session_key,
            "assistant_id": session.assistant_id,
        },
    )


def _handle_help_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=_build_help_message(session_identity=session_identity),
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        metadata={
            "source": "telegram_help",
            "scope": session_identity.scope.value,
            "chat_type": session_identity.chat_context.chat_type.value,
        },
    )


def _handle_approve_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    approval_service: ApprovalStoreService,
    github_issue_service: GitHubIssueService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    approval_query = _extract_approve_query(extracted["text"])
    approval_id, approval_action, approval_note = _parse_approve_query(approval_query)
    approval_uid = session_identity.actor.user_id or chat_id
    message_source = "telegram_approve_query"
    if approval_action is not None and approval_id:
        approval = approval_service.get_request(approval_id)
        if approval is None or approval.telegram_uid != approval_uid:
            message_text = f"未找到 approval: {approval_id}"
        else:
            decision = "approved" if approval_action == "approve" else "rejected"
            try:
                approval = approval_service.resolve_request(
                    approval.approval_id,
                    ApprovalDecisionRequest(
                        decision=decision,
                        decided_by=approval_uid,
                        note=approval_note or None,
                        metadata={
                            "resolved_via": "telegram_command",
                            "chat_id": chat_id,
                            "scope": session_identity.scope.value,
                        },
                    ),
                )
                message_text = _build_approval_decision_message(approval)
                message_source = "telegram_approve_decision"
                approval_query = approval.approval_id
                if decision == "approved" and approval.metadata.get("action_type") == "github_issue_comment":
                    comment_output = _post_github_issue_comment_for_approval(
                        approval=approval,
                        approval_service=approval_service,
                        github_issue_service=github_issue_service,
                        chat_id=chat_id,
                        scope=session_identity.scope.value,
                    )
                    message_text = "\n\n".join(
                        [
                            message_text,
                            _build_github_issue_comment_posted_message(
                                approval_id=approval.approval_id,
                                issue_reference=str(approval.metadata.get("issue_reference") or "unknown"),
                                output=comment_output or None,
                            ),
                        ]
                    ).strip()
            except ValueError as exc:
                message_text = str(exc)
                message_source = "telegram_approve_decision"
            except RuntimeError as exc:
                message_text = "\n\n".join(
                    [
                        _build_approval_decision_message(approval),
                        f"[GitHub Reply Failed]\n{str(exc).strip()}",
                    ]
                ).strip()
                message_source = "telegram_approve_decision"
    elif approval_id:
        approval = approval_service.get_request(approval_id)
        if approval is None or approval.telegram_uid != approval_uid:
            message_text = f"未找到 approval: {approval_id}"
        else:
            approval_query = approval.approval_id
            message_text = _build_approval_detail_message(approval)
    else:
        approvals = approval_service.list_requests(
            status=ApprovalStatus.PENDING,
            telegram_uid=approval_uid,
            limit=10,
        )
        message_text = _build_approval_list_message(approvals)

    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=message_text,
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        metadata={
            "source": message_source,
            "approval_id": approval_query or None,
            "decision": approval_action or None,
            "scope": session_identity.scope.value,
        },
    )


def _ensure_admin_channel_visibility(
    *,
    admin_config_service: AdminConfigService,
    chat_id: str,
) -> None:
    if not chat_id:
        return

    telegram_settings = load_telegram_settings()
    key = telegram_settings.channel_key.strip()
    if not key:
        key = "telegram-main"
    display_name = telegram_settings.channel_display_name.strip() or "Telegram Main"
    actor = telegram_settings.channel_actor.strip() or "telegram-webhook"

    channels = admin_config_service.list_channels()
    existing = next((item for item in channels if item.key == key), None)
    if existing is None:
        try:
            admin_config_service.create_channel(
                AdminChannelConfigCreateRequest(
                    key=key,
                    display_name=display_name,
                    provider="telegram",
                    endpoint_url=None,
                    secret_ref=None,
                    secret_value=None,
                    allowed_chat_ids=[chat_id],
                    allowed_user_ids=[],
                    routing_policy={"auto_synced_by": "telegram_webhook"},
                    metadata={"auto_synced_by": "telegram_webhook"},
                    enabled=True,
                    actor=actor,
                )
            )
        except ValueError:
            return
        return

    updated_chat_ids: list[str] = []
    seen_chat_ids: set[str] = set()
    for item in [*existing.allowed_chat_ids, chat_id]:
        value = item.strip()
        if not value or value in seen_chat_ids:
            continue
        seen_chat_ids.add(value)
        updated_chat_ids.append(value)
    if updated_chat_ids == existing.allowed_chat_ids and existing.provider == "telegram":
        return

    try:
        admin_config_service.update_channel(
            channel_id=existing.channel_id,
            request=AdminChannelConfigUpdateRequest(
                display_name=existing.display_name,
                provider="telegram",
                endpoint_url=existing.endpoint_url,
                secret_ref=existing.secret_ref,
                secret_value=None,
                clear_secret=False,
                allowed_chat_ids=updated_chat_ids,
                allowed_user_ids=existing.allowed_user_ids,
                routing_policy=existing.routing_policy,
                metadata_updates={"auto_synced_by": "telegram_webhook"},
                actor=actor,
                reason="sync telegram chat id from webhook",
            ),
        )
    except (KeyError, ValueError):
        return


def _execute_agent_and_notify(
    *,
    agent_service: ClaudeAgentService,
    notifier: TelegramNotifierService,
    chat_id: str,
    agent_run_id: str,
    request_payload: ClaudeAgentCreateRequest,
) -> None:
    agent_service.execute(agent_run_id, request_payload)
    if not notifier.enabled:
        return
    run = agent_service.get(agent_run_id)
    if run is None:
        return
    notifier.send_message(chat_id=chat_id, text=_build_agent_result_message(run))


def _build_agent_result_message(run: ClaudeAgentRunRead) -> str:
    status_value = run.status.value
    lines = [
        f"[任务结果] {run.task_name}",
        f"状态: {status_value}",
        f"run: {run.agent_run_id}",
    ]
    if status_value == "completed":
        output = (run.stdout_preview or "").strip()
        if output:
            lines.extend(["", "输出:", output])
        else:
            lines.extend(["", "输出为空。"])
    else:
        err = (run.error or run.stderr_preview or "unknown error").strip()
        lines.extend(["", "错误:", err])

    text = "\n".join(lines).strip()
    # Telegram text message hard limit is 4096 chars.
    if len(text) > 3900:
        return text[:3900] + "\n...[truncated]"
    return text


def _execute_manager_dispatch_and_notify(
    *,
    manager_service: ManagerAgentService,
    approval_service: ApprovalStoreService,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    chat_id: str,
    session_id: str,
    approval_uid: str,
    assistant_scope: AssistantScope,
    dispatch_id: str,
    issue_reference: str | None,
    issue_url: str | None,
    issue_title: str | None,
) -> None:
    dispatch: ManagerDispatchRead | None = None
    try:
        dispatch = manager_service.execute_dispatch(dispatch_id)
    except Exception as exc:
        dispatch = manager_service.get_dispatch(dispatch_id)
        error_text = str(exc).strip() or "manager dispatch failed"
        if dispatch is None:
            if notifier.enabled:
                notifier.send_message(
                    chat_id=chat_id,
                    text=_truncate_telegram_text(
                        "\n".join(
                            [
                                "[Manager Task]",
                                f"dispatch: {dispatch_id}",
                                "status: failed",
                                "",
                                error_text,
                            ]
                        )
                    ),
                )
            return
        dispatch = dispatch.model_copy(update={"error": dispatch.error or error_text})

    final_status = dispatch.status
    openclaw_service.append_event(
        session_id=session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"manager dispatch finished: {dispatch.dispatch_id}",
            metadata={
                "source": "telegram_manager_task",
                "dispatch_id": dispatch.dispatch_id,
                "status": final_status.value,
                "issue_reference": issue_reference,
            },
        ),
    )
    openclaw_service.set_status(
        session_id=session_id,
        status=JobStatus.COMPLETED if final_status == JobStatus.COMPLETED else JobStatus.FAILED,
        metadata_updates={"latest_manager_dispatch_status": final_status.value},
    )

    if notifier.enabled:
        notifier.send_message(
            chat_id=chat_id,
            text=_build_manager_dispatch_result_message(
                dispatch,
                issue_reference=issue_reference,
                issue_url=issue_url,
            ),
        )

    if not issue_reference:
        return

    approval = approval_service.create_request(
        ApprovalRequestCreateRequest(
            title=f"Reply to GitHub issue {issue_reference}",
            summary=f"Review and post the automated execution update for {issue_reference}.",
            risk=ApprovalRisk.EXTERNAL,
            source="github_issue_task",
            telegram_uid=approval_uid,
            session_id=session_id,
            assistant_scope=assistant_scope,
            metadata={
                "action_type": "github_issue_comment",
                "issue_reference": issue_reference,
                "issue_url": issue_url,
                "issue_title": issue_title,
                "dispatch_id": dispatch.dispatch_id,
                "comment_body": _build_github_issue_comment_body(
                    dispatch,
                    issue_reference=issue_reference,
                    issue_url=issue_url,
                ),
            },
        )
    )
    openclaw_service.append_event(
        session_id=session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"github issue reply approval queued: {approval.approval_id}",
            metadata={
                "source": "telegram_manager_task",
                "approval_id": approval.approval_id,
                "dispatch_id": dispatch.dispatch_id,
                "issue_reference": issue_reference,
            },
        ),
    )
    if notifier.enabled:
        notifier.send_message(
            chat_id=chat_id,
            text=_build_github_issue_reply_approval_message(
                approval_id=approval.approval_id,
                issue_reference=issue_reference,
                issue_url=issue_url,
            ),
        )


def _build_manager_dispatch_queued_message(
    dispatch: ManagerDispatchRead,
    *,
    issue_reference: str | None,
) -> str:
    task_count = len(dispatch.execution_plan.tasks) if dispatch.execution_plan is not None else 0
    lines = [
        "[Manager Task]",
        f"dispatch: {dispatch.dispatch_id}",
        f"strategy: {dispatch.execution_plan.strategy.value if dispatch.execution_plan is not None else 'single_task'}",
        f"tasks: {task_count}",
    ]
    if issue_reference:
        lines.append(f"issue: {issue_reference}")
    lines.append("已接收，开始拆解并执行。")
    return _truncate_telegram_text("\n".join(lines))


def _build_manager_dispatch_result_message(
    dispatch: ManagerDispatchRead,
    *,
    issue_reference: str | None,
    issue_url: str | None,
) -> str:
    task_count = len(dispatch.execution_plan.tasks) if dispatch.execution_plan is not None else 0
    completed_count = (
        sum(1 for item in dispatch.execution_plan.tasks if item.status == JobStatus.COMPLETED)
        if dispatch.execution_plan is not None
        else 0
    )
    lines = [
        "[Manager Task]",
        f"dispatch: {dispatch.dispatch_id}",
        f"status: {dispatch.status.value}",
        f"tasks: {completed_count}/{task_count}",
    ]
    if issue_reference:
        lines.append(f"issue: {issue_reference}")
    if issue_url:
        lines.append(f"url: {issue_url}")
    if dispatch.summary:
        lines.extend(["", dispatch.summary])

    promotion = dispatch.run_summary.promotion if dispatch.run_summary is not None else None
    if promotion is not None and promotion.pr_url:
        lines.append(f"draft_pr: {promotion.pr_url}")
    elif dispatch.run_summary is not None and dispatch.run_summary.promotion_patch_uri:
        lines.append(f"patch: {dispatch.run_summary.promotion_patch_uri}")

    error_text = (
        dispatch.error
        or (
            dispatch.run_summary.driver_result.error
            if dispatch.run_summary is not None and dispatch.run_summary.driver_result.error
            else None
        )
    )
    if error_text:
        lines.extend(["", "error:", error_text.strip()])
    return _truncate_telegram_text("\n".join(lines))


def _build_github_issue_comment_body(
    dispatch: ManagerDispatchRead,
    *,
    issue_reference: str,
    issue_url: str | None,
) -> str:
    lines = [
        "Automated progress update from the local autonomous agent stack.",
        "",
        f"- Issue: {issue_reference}",
        f"- Dispatch: {dispatch.dispatch_id}",
        f"- Status: {dispatch.status.value}",
    ]
    if issue_url:
        lines.append(f"- Issue URL: {issue_url}")
    if dispatch.summary:
        lines.append(f"- Summary: {dispatch.summary}")
    promotion = dispatch.run_summary.promotion if dispatch.run_summary is not None else None
    if promotion is not None and promotion.pr_url:
        lines.append(f"- Draft PR: {promotion.pr_url}")
    error_text = (
        dispatch.error
        or (
            dispatch.run_summary.driver_result.error
            if dispatch.run_summary is not None and dispatch.run_summary.driver_result.error
            else None
        )
    )
    if error_text:
        lines.append(f"- Error: {error_text.strip()}")
    lines.extend(
        [
            "",
            "This update was prepared automatically from Telegram `/task issue` and still expects human review before merge.",
        ]
    )
    return "\n".join(lines).strip()


def _build_github_issue_reply_approval_message(
    *,
    approval_id: str,
    issue_reference: str,
    issue_url: str | None,
) -> str:
    lines = [
        "[GitHub Reply Pending]",
        f"approval: {approval_id}",
        f"issue: {issue_reference}",
    ]
    if issue_url:
        lines.append(f"url: {issue_url}")
    lines.extend(
        [
            "",
            f"/approve {approval_id} approve  发布执行结果到 GitHub issue",
            f"/approve {approval_id} reject  保留结果，仅在 Telegram 查看",
        ]
    )
    return _truncate_telegram_text("\n".join(lines))


def _build_github_issue_comment_posted_message(
    *,
    approval_id: str,
    issue_reference: str,
    output: str | None,
) -> str:
    lines = [
        "[GitHub Reply Posted]",
        f"approval: {approval_id}",
        f"issue: {issue_reference}",
    ]
    if output:
        lines.extend(["", output.strip()])
    return _truncate_telegram_text("\n".join(lines))


def _truncate_telegram_text(text: str) -> str:
    normalized = text.strip()
    if len(normalized) > 3900:
        return normalized[:3900] + "\n...[truncated]"
    return normalized


def _handle_status_query(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    agent_service: ClaudeAgentService,
    memory_service: OpenClawMemoryService,
    capability_registry: CapabilityProviderRegistry,
    panel_access_service: PanelAccessService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
    worker_registry: WorkerRegistryService,
) -> TelegramWebhookAck:
    runtime_identity = get_runtime_identity()
    session = _find_existing_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
    )
    runs = []
    if session is not None:
        session = _sync_session_runtime_identity(
            openclaw_service=openclaw_service,
            session=session,
            background_tasks=background_tasks,
            notifier=notifier,
            chat_id=chat_id,
        )
        runs = [run for run in agent_service.list() if run.session_id == session.session_id]
        runs.sort(key=lambda item: item.updated_at, reverse=True)
    memory_bundle = memory_service.bundle_for_session(session.session_id) if session is not None else None
    workers = worker_registry.list_workers()

    summary_lines = _build_status_summary_lines(
        chat_id=chat_id,
        session=session,
        runs=runs,
        session_identity=session_identity,
        memory_bundle=memory_bundle,
        capability_registry=capability_registry,
        runtime_identity=runtime_identity,
        workers=workers,
    )

    # Initialize GroupAccessManager for whitelist groups
    group_access_manager = GroupAccessManager()
    magic_link_url: str | None = None
    expires_at_iso: str | None = None
    is_group_link = False

    # Check if this is an internal group
    try:
        chat_id_int = int(chat_id)
        if group_access_manager.is_internal_group(chat_id_int):
            # Generate group-scoped magic link
            user_id = (
                extracted.get("from_user_id")
                or extracted.get("from_id")
                or update.get("message", {}).get("from", {}).get("id")
            )
            if user_id:
                group_link = group_access_manager.create_group_magic_link(
                    chat_id=chat_id_int,
                    user_id=int(user_id),
                )
                if group_link:
                    magic_link_url = group_link.url
                    expires_at_iso = group_link.expires_at.isoformat()
                    is_group_link = True
    except (ValueError, TypeError):
        pass

    # Fall back to regular magic link if not in whitelist
    if not magic_link_url and panel_access_service.enabled:
        try:
            magic_link = panel_access_service.create_magic_link(chat_id)
            magic_link_url = magic_link.url
            expires_at_iso = magic_link.expires_at.isoformat()
        except (RuntimeError, ValueError, PermissionError):
            magic_link_url = None
            expires_at_iso = None

    mini_app_url = _resolve_mini_app_url(
        magic_link_url=magic_link_url,
        is_group_link=is_group_link,
    )

    if notifier.enabled:
        background_tasks.add_task(
            _notify_status_magic_link_compat,
            notifier=notifier,
            chat_id=chat_id,
            summary_lines=summary_lines,
            magic_link_url=magic_link_url,
            expires_at_iso=expires_at_iso,
            is_group_link=is_group_link,
            mini_app_url=mini_app_url,
        )

    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id if session is not None else None,
        metadata={
            "source": "telegram_status_query",
            "update_type": extracted.get("raw_type"),
            "magic_link_url": magic_link_url,
            "magic_link_expires_at": expires_at_iso,
            "active_runs": len(runs),
            "provider_count": len(capability_registry.list_descriptors()),
            "is_group_link": is_group_link,
            "mini_app_url": mini_app_url,
            "scope": session_identity.scope.value,
            "session_key": session_identity.session_key,
        },
    )


def _is_status_query(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized.startswith("/status"):
        return True
    if normalized.startswith("/panel"):
        return True
    if normalized in {
        "status",
        "task status",
        "任务状态",
        "状态",
        "查询状态",
        "查看状态",
        "进度",
        "面板",
        "在哪",
        "在哪儿",
        "你在哪",
        "你在哪儿",
    }:
        return True
    return any(
        phrase in normalized
        for phrase in (
            "在哪台电脑",
            "在哪个电脑",
            "在哪台机器",
            "在哪个机器",
            "在哪台主机",
            "在哪个主机",
            "在哪里运行",
            "在哪运行",
            "mac还是linux",
            "mac 还是 linux",
            "which computer",
            "what host",
            "where are you running",
        )
    )


def _is_help_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized in {"/help", "/start", "help", "帮助"}


def _is_task_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized == "/task" or normalized.startswith("/task ")


def _is_approve_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized == "/approve" or normalized.startswith("/approve ")


def _is_mode_command(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized == "/mode" or normalized.startswith("/mode ")


def _is_memory_command(text: str) -> bool:
    normalized = text.strip()
    lowered = normalized.lower()
    return (
        lowered == "/memory"
        or lowered.startswith("/memory ")
        or normalized.startswith("记住")
        or lowered.startswith("remember ")
        or lowered.startswith("remember this:")
    )


def _is_skills_command(text: str) -> bool:
    normalized = text.strip()
    lowered = normalized.lower()
    return lowered == "/skills" or lowered.startswith("/skills ")


def _is_reset_command(text: str) -> bool:
    normalized = text.strip()
    lowered = normalized.lower()
    return lowered == "/reset" or normalized == "重置会话"


def _extract_mode_target(text: str) -> AssistantScope | None:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/mode":
        return None
    if not lowered.startswith("/mode "):
        return None
    target = normalized.split(" ", 1)[1].strip().lower()
    if target == "personal":
        return AssistantScope.PERSONAL
    if target == "shared":
        return AssistantScope.SHARED
    return None


def _extract_memory_content(text: str) -> str:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/memory":
        return ""
    if lowered.startswith("/memory "):
        return normalized.split(" ", 1)[1].strip()
    if normalized.startswith("记住"):
        return normalized[2:].lstrip(" ：:").strip()
    if lowered.startswith("remember this:"):
        return normalized[len("remember this:") :].strip()
    if lowered.startswith("remember "):
        return normalized[len("remember ") :].strip()
    return ""


def _extract_approve_query(text: str) -> str:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/approve":
        return ""
    if lowered.startswith("/approve "):
        return normalized.split(" ", 1)[1].strip()
    return ""


def _extract_task_query(text: str) -> str:
    return _parse_task_command(text)[0]


def _parse_task_command(text: str) -> tuple[str, bool]:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/task":
        return "", False
    if lowered.startswith("/task "):
        payload = normalized.split(" ", 1)[1].strip()
        approval_requested = False
        if payload.startswith("--approve"):
            approval_requested = True
            payload = payload[len("--approve") :].strip()
        return payload, approval_requested
    return "", False


def _can_telegram_task_self_approve(
    *,
    session_identity: TelegramSessionIdentityRead,
) -> bool:
    return session_identity.actor.role in {ActorRole.OWNER, ActorRole.PARTNER}


def _extract_issue_task_parts(task_query: str) -> tuple[str, str]:
    normalized = task_query.strip()
    if not normalized.casefold().startswith("issue "):
        raise ValueError("issue task must start with `issue `")
    remainder = normalized[6:].strip()
    if not remainder:
        raise ValueError("missing GitHub issue reference")
    issue_reference, _, operator_note = remainder.partition(" ")
    return issue_reference.strip(), operator_note.strip()


def _parse_approve_query(query: str) -> tuple[str, str | None, str]:
    normalized = query.strip()
    if not normalized:
        return "", None, ""
    parts = normalized.split(None, 2)
    approval_id = parts[0].strip()
    if len(parts) < 2:
        return approval_id, None, ""
    action = parts[1].strip().lower()
    if action not in {"approve", "reject"}:
        return approval_id, None, ""
    note = parts[2].strip() if len(parts) > 2 else ""
    return approval_id, action, note


def _extract_skill_query(text: str) -> str:
    normalized = text.strip()
    lowered = normalized.lower()
    if lowered == "/skills":
        return ""
    if lowered.startswith("/skills "):
        return normalized.split(" ", 1)[1].strip()
    return ""


def _resolve_telegram_session_identity(
    *,
    extracted: dict[str, Any],
    telegram_settings,
    openclaw_service: OpenClawCompatService,
) -> TelegramSessionIdentityRead:
    base_identity = build_telegram_session_identity(extracted, telegram_settings)
    if base_identity.chat_context.chat_type != ChatType.PRIVATE:
        return base_identity
    preferred_scope = _resolve_private_scope_preference(
        openclaw_service=openclaw_service,
        chat_id=base_identity.chat_context.chat_id,
        actor_user_id=base_identity.actor.user_id,
    )
    if preferred_scope is None or preferred_scope == base_identity.scope:
        return base_identity
    return build_telegram_session_identity(
        extracted,
        telegram_settings,
        scope_override=preferred_scope,
    )


def _resolve_private_scope_preference(
    *,
    openclaw_service: OpenClawCompatService,
    chat_id: str | None,
    actor_user_id: str | None,
) -> AssistantScope | None:
    candidates: list[OpenClawSessionRead] = []
    for session in openclaw_service.list_sessions():
        if session.channel != "telegram":
            continue
        chat_context = session.chat_context
        if chat_context is None or chat_context.chat_type != ChatType.PRIVATE:
            continue
        if chat_id and session.external_id != chat_id:
            continue
        if actor_user_id and session.actor is not None and session.actor.user_id not in {None, actor_user_id}:
            continue
        preference = str(session.metadata.get("telegram_mode_preference") or "").strip().lower()
        if preference not in {AssistantScope.PERSONAL.value, AssistantScope.SHARED.value}:
            continue
        candidates.append(session)
    if not candidates:
        return None
    candidates.sort(key=lambda item: item.updated_at, reverse=True)
    return AssistantScope(str(candidates[0].metadata["telegram_mode_preference"]))


def _session_matches_identity(
    session: OpenClawSessionRead,
    session_identity: TelegramSessionIdentityRead,
) -> bool:
    if session.scope != session_identity.scope:
        return False
    if session.assistant_id and session.assistant_id != session_identity.assistant_id:
        return False
    if session.session_key and session.session_key != session_identity.session_key:
        return False
    return True


def _find_existing_telegram_session(
    *,
    openclaw_service: OpenClawCompatService,
    chat_id: str,
    session_identity: TelegramSessionIdentityRead,
) -> OpenClawSessionRead | None:
    session = openclaw_service.find_session_by_key(channel="telegram", session_key=session_identity.session_key)
    if session is not None:
        return session
    legacy_session = openclaw_service.find_session(channel="telegram", external_id=chat_id)
    if legacy_session is not None and _session_matches_identity(legacy_session, session_identity):
        return legacy_session
    return None


def _resolve_mini_app_url(
    *,
    magic_link_url: str | None,
    is_group_link: bool,
) -> str | None:
    if is_group_link:
        return None
    configured = (load_panel_settings().mini_app_url or "").strip()
    if configured:
        return configured
    if magic_link_url and magic_link_url.startswith("https://"):
        return magic_link_url
    return None


def _notify_status_magic_link_compat(
    *,
    notifier: TelegramNotifierService,
    chat_id: str,
    summary_lines: list[str],
    magic_link_url: str | None,
    expires_at_iso: str | None,
    is_group_link: bool,
    mini_app_url: str | None,
) -> bool:
    """Call notifier with backward-compatible kwargs for tests/stubs."""
    kwargs: dict[str, Any] = {
        "chat_id": chat_id,
        "summary_lines": summary_lines,
        "magic_link_url": magic_link_url,
        "expires_at_iso": expires_at_iso,
        "mini_app_url": mini_app_url,
    }

    try:
        signature = inspect.signature(notifier.notify_status_magic_link)
    except (TypeError, ValueError):
        signature = None

    if signature and "is_group_link" in signature.parameters:
        kwargs["is_group_link"] = is_group_link

    try:
        return bool(notifier.notify_status_magic_link(**kwargs))
    except TypeError:
        kwargs.pop("is_group_link", None)
        kwargs.pop("mini_app_url", None)
        return bool(notifier.notify_status_magic_link(**kwargs))


def _build_status_summary_lines(
    *,
    chat_id: str,
    session: OpenClawSessionRead | None,
    runs: list[Any],
    session_identity: TelegramSessionIdentityRead,
    memory_bundle: OpenClawMemoryBundleRead | None,
    capability_registry: CapabilityProviderRegistry,
    runtime_identity: dict[str, str],
    workers: list[Any],
) -> list[str]:
    descriptors = capability_registry.list_descriptors()
    skill_provider_count = len([item for item in descriptors if item.domain == CapabilityDomain.SKILL])
    runtime_display = runtime_identity["runtime_display"]
    runtime_host = runtime_identity["runtime_host"]
    runtime_platform = runtime_identity["runtime_platform"]
    if session is None:
        lines = [
            f"chat_id: {chat_id}",
            f"runtime: {runtime_display}",
            f"runtime_host: {runtime_host}",
            f"runtime_platform: {runtime_platform}",
            f"scope: {session_identity.scope.value}",
            f"session_key: {session_identity.session_key}",
            f"providers: {len(descriptors)}",
            f"skill_providers: {skill_provider_count}",
            "当前没有历史会话。",
            "发送任务文本后系统会自动创建会话并执行。",
        ]
        _append_worker_summary_lines(lines, workers)
        return lines

    runtime_display = str(session.metadata.get("runtime_display") or runtime_display)
    runtime_host = str(session.metadata.get("runtime_host") or runtime_host)
    runtime_platform = str(session.metadata.get("runtime_platform") or runtime_platform)
    lines = [
        f"chat_id: {chat_id}",
        f"runtime: {runtime_display}",
        f"runtime_host: {runtime_host}",
        f"runtime_platform: {runtime_platform}",
        f"scope: {session.scope.value}",
        f"session_key: {session.session_key or session_identity.session_key}",
        f"session: {session.session_id}",
        f"session_status: {session.status.value}",
        f"active_runs: {sum(1 for run in runs if run.status.value in {'queued', 'running'})}",
        f"providers: {len(descriptors)}",
        f"skill_providers: {skill_provider_count}",
    ]
    previous_runtime = str(session.metadata.get("runtime_previous_display") or "").strip()
    switched_at = str(session.metadata.get("runtime_switched_at") or "").strip()
    if previous_runtime and switched_at:
        lines.append(f"runtime_switched: {previous_runtime} -> {runtime_display} @ {switched_at}")
    if memory_bundle is not None:
        lines.append(f"personal_memories: {len(memory_bundle.personal_memories)}")
        lines.append(f"shared_memories: {len(memory_bundle.shared_memories)}")
    if session.actor is not None:
        lines.append(f"actor_role: {session.actor.role.value}")
    _append_worker_summary_lines(lines, workers)
    if not runs:
        lines.append("最近任务: 暂无")
        return lines

    lines.append("最近任务:")
    for run in runs[:3]:
        lines.append(f"- {run.agent_run_id} | {run.status.value} | {run.task_name}")
    return lines


def _append_worker_summary_lines(lines: list[str], workers: list[Any]) -> None:
    online_workers = [
        worker
        for worker in workers
        if not getattr(worker, "is_stale", False)
        and getattr(getattr(worker, "mode", None), "value", getattr(worker, "mode", None)) != WorkerMode.OFFLINE.value
    ]
    lines.append(f"workers_online: {len(online_workers)}")
    for worker in online_workers[:3]:
        metadata = getattr(worker, "metadata", {}) or {}
        host = getattr(worker, "host", None) or str(metadata.get("runtime_host_short") or metadata.get("runtime_host") or "unknown")
        worker_type = getattr(getattr(worker, "worker_type", None), "value", getattr(worker, "worker_type", "unknown"))
        mode = getattr(getattr(worker, "mode", None), "value", getattr(worker, "mode", "unknown"))
        health = getattr(getattr(worker, "health", None), "value", getattr(worker, "health", "unknown"))
        lines.append(f"- worker {worker.worker_id} | {worker_type}/{mode} | {host} | {health}")


def _build_help_message(*, session_identity: TelegramSessionIdentityRead) -> str:
    chat_type = session_identity.chat_context.chat_type
    lines = [
        "[Telegram Commands]",
        "/start 查看欢迎信息和命令列表",
        "/status 查看当前会话、任务和能力摘要",
        "/task <需求> 走 Manager Agent DAG 执行任务",
        "/task --approve <需求> owner/partner 直通 Draft PR 审批上下文",
        "/task issue <issue_ref> [补充说明] 读取 GitHub issue 后派发修复",
        "/approve 查看待审批列表",
        "/approve <approval_id> 查看待审批详情",
        "/approve <approval_id> approve [备注] 批准待审批事项",
        "/approve <approval_id> reject [备注] 拒绝待审批事项",
        "/memory 查看长期记忆摘要",
        "/memory <内容> 写入长期记忆",
        "/skills 查看可用 skills",
        "/skills <skill_key> 查看 skill 详情",
        "/reset 重置当前会话",
    ]
    if chat_type == ChatType.PRIVATE:
        lines.extend(
            [
                "/mode 查看当前模式",
                "/mode personal 切到 personal",
                "/mode shared 切到 shared",
            ]
        )
    else:
        lines.append("/mode 群组固定为 shared，仅用于查看说明")
    lines.append("/help 查看本帮助")
    return "\n".join(lines)


def _post_github_issue_comment_for_approval(
    *,
    approval: Any,
    approval_service: ApprovalStoreService,
    github_issue_service: GitHubIssueService,
    chat_id: str,
    scope: str,
) -> str:
    issue_reference = str(approval.metadata.get("issue_reference") or "").strip()
    comment_body = str(approval.metadata.get("comment_body") or "").strip()
    if not issue_reference or not comment_body:
        raise RuntimeError("approval is missing GitHub issue comment payload")
    output = github_issue_service.post_comment(issue_reference, comment_body)
    approval_service.update_request_metadata(
        approval.approval_id,
        {
            "comment_posted": True,
            "comment_posted_at": _utc_now(),
            "comment_post_result": output,
            "resolved_via_chat_id": chat_id,
            "resolved_scope": scope,
        },
    )
    return output


def _build_approval_list_message(approvals: list[Any]) -> str:
    if not approvals:
        return "当前没有待审批事项。"
    lines = [
        "[Pending Approvals]",
        f"count: {len(approvals)}",
        "",
    ]
    for item in approvals[:10]:
        lines.append(f"- {item.approval_id} | {item.risk.value} | {item.title}")
    lines.extend(
        [
            "",
            "发送 /approve <approval_id> 查看详情。",
            "发送 /approve <approval_id> approve [备注] 或 /approve <approval_id> reject [备注] 执行决策。",
        ]
    )
    return "\n".join(lines).strip()


def _build_approval_detail_message(approval: Any) -> str:
    lines = [
        "[Approval Detail]",
        f"id: {approval.approval_id}",
        f"status: {approval.status.value}",
        f"risk: {approval.risk.value}",
        f"title: {approval.title}",
        f"source: {approval.source}",
    ]
    if approval.summary:
        lines.append(f"summary: {approval.summary}")
    if approval.session_id:
        lines.append(f"session: {approval.session_id}")
    if approval.agent_run_id:
        lines.append(f"agent_run: {approval.agent_run_id}")
    if approval.expires_at is not None:
        lines.append(f"expires_at: {approval.expires_at.isoformat()}")
    if approval.status == ApprovalStatus.PENDING:
        lines.extend(
            [
                "",
                f"/approve {approval.approval_id} approve [备注]",
                f"/approve {approval.approval_id} reject [备注]",
            ]
        )
    return "\n".join(lines).strip()


def _build_approval_decision_message(approval: Any) -> str:
    lines = [
        "[Approval Decision]",
        f"id: {approval.approval_id}",
        f"status: {approval.status.value}",
        f"title: {approval.title}",
    ]
    if approval.decided_by:
        lines.append(f"decided_by: {approval.decided_by}")
    if approval.decision_note:
        lines.append(f"note: {approval.decision_note}")
    return "\n".join(lines).strip()


def _list_skill_providers(
    capability_registry: CapabilityProviderRegistry,
) -> list[tuple[str, SkillProvider]]:
    providers: list[tuple[str, SkillProvider]] = []
    for descriptor in capability_registry.list_descriptors(domain=CapabilityDomain.SKILL):
        provider = capability_registry.get(descriptor.provider_id)
        if provider is not None and isinstance(provider, SkillProvider):
            providers.append((descriptor.provider_id, provider))
    return providers


def _find_skill_detail(
    *,
    skill_query: str,
    skill_providers: list[tuple[str, SkillProvider]],
):
    normalized = skill_query.strip().lower()
    if not normalized:
        return None
    for provider_id, provider in skill_providers:
        detail = provider.get_skill(skill_query)
        if detail is not None:
            return provider_id, detail
        catalog = provider.list_skills()
        for skill in catalog.skills:
            if skill.skill_key.lower() == normalized or skill.name.lower() == normalized:
                detail = provider.get_skill(skill.skill_key) or provider.get_skill(skill.name)
                if detail is not None:
                    return provider_id, detail
    return None


def _build_skills_catalog_message(catalogs: list[tuple[str, Any]]) -> str:
    skill_lines: list[str] = []
    total_skills = 0
    for provider_id, catalog in catalogs:
        skill_count = len(catalog.skills)
        total_skills += skill_count
        skill_lines.append(f"[{provider_id}] {skill_count} skills")
        for skill in catalog.skills[:8]:
            skill_lines.append(f"- {skill.skill_key} | {skill.name}")
    if not skill_lines:
        return "当前没有可用 skills。"
    lines = [
        "[Skills]",
        f"providers: {len(catalogs)}",
        f"total_skills: {total_skills}",
        "",
        *skill_lines[:30],
        "",
        "发送 /skills <skill_key> 查看详情。",
    ]
    return "\n".join(lines).strip()


def _build_skill_detail_message(*, provider_id: str, skill: Any) -> str:
    lines = [
        "[Skill Detail]",
        f"provider: {provider_id}",
        f"name: {skill.name}",
        f"skill_key: {skill.skill_key}",
        f"source: {skill.source}",
        f"file: {skill.file_path}",
    ]
    if skill.description:
        lines.append(f"description: {skill.description}")
    content = (getattr(skill, "content", "") or "").strip()
    if content:
        preview = content[:1200]
        if len(content) > 1200:
            preview += "\n...[truncated]"
        lines.extend(["", preview])
    return "\n".join(lines).strip()


def _build_memory_summary_lines(bundle: OpenClawMemoryBundleRead) -> list[str]:
    lines = [
        f"session: {bundle.session_id}",
        f"scope: {bundle.session_scope.value}",
        f"session_events: {len(bundle.session_events)}",
        f"personal_memories: {len(bundle.personal_memories)}",
        f"shared_memories: {len(bundle.shared_memories)}",
    ]
    if bundle.personal_memories:
        lines.append("最近 personal:")
        for item in bundle.personal_memories[:3]:
            lines.append(f"- {item.content[:80]}")
    if bundle.shared_memories:
        lines.append("最近 shared:")
        for item in bundle.shared_memories[:3]:
            lines.append(f"- {item.content[:80]}")
    return lines


def _build_task_name(chat_id: str, update: dict[str, Any], extracted: dict[str, Any]) -> str:
    message_id = extracted.get("message_id")
    update_id = _safe_int(update.get("update_id"))
    suffix = message_id if message_id is not None else update_id
    if suffix is None:
        suffix = _utc_now().replace("-", "").replace(":", "").replace(".", "")
    return f"tg_{chat_id}_{suffix}"


def _build_session_title(*, chat_id: str, session_identity: TelegramSessionIdentityRead) -> str:
    scope = session_identity.scope
    if scope == AssistantScope.PERSONAL and session_identity.actor.user_id:
        return f"telegram-personal-{session_identity.actor.user_id}"
    if scope == AssistantScope.SHARED:
        return f"telegram-shared-{chat_id}"
    return f"telegram-{chat_id}"


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
