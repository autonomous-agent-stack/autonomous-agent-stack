from __future__ import annotations

from datetime import datetime, timezone
import inspect
import threading
import time
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from autoresearch.api.dependencies import (
    get_admin_config_service,
    get_claude_agent_service,
    get_openclaw_compat_service,
    get_panel_access_service,
    get_telegram_notifier_service,
)
from autoresearch.api.settings import load_panel_settings, load_runtime_settings, load_telegram_settings
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.group_access import GroupAccessManager
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.telegram_identity import (
    TelegramSessionIdentityRead,
    build_telegram_session_identity,
)
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.models import (
    AdminChannelConfigCreateRequest,
    AdminChannelConfigUpdateRequest,
    AssistantScope,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSessionRead,
    TelegramWebhookAck,
)


router = APIRouter(prefix="/api/v1/gateway/telegram", tags=["gateway", "telegram"])
compat_router = APIRouter(tags=["gateway", "telegram", "compat"])
_UPDATE_REPLAY_TTL_SECONDS = 600
_RATE_WINDOW_SECONDS = 60
_RATE_MAX_REQUESTS_PER_CHAT = 30
_SEEN_UPDATES: dict[str, float] = {}
_CHAT_RATE_WINDOWS: dict[str, list[float]] = {}
_GUARD_LOCK = threading.Lock()


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
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
    panel_access_service: PanelAccessService = Depends(get_panel_access_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
    admin_config_service: AdminConfigService = Depends(get_admin_config_service),
) -> TelegramWebhookAck:
    return _handle_telegram_webhook(
        update=update,
        raw_request=raw_request,
        background_tasks=background_tasks,
        openclaw_service=openclaw_service,
        agent_service=agent_service,
        panel_access_service=panel_access_service,
        notifier=notifier,
        admin_config_service=admin_config_service,
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
    agent_service: ClaudeAgentService = Depends(get_claude_agent_service),
    panel_access_service: PanelAccessService = Depends(get_panel_access_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
    admin_config_service: AdminConfigService = Depends(get_admin_config_service),
) -> TelegramWebhookAck:
    return _handle_telegram_webhook(
        update=update,
        raw_request=raw_request,
        background_tasks=background_tasks,
        openclaw_service=openclaw_service,
        agent_service=agent_service,
        panel_access_service=panel_access_service,
        notifier=notifier,
        admin_config_service=admin_config_service,
    )


def _handle_telegram_webhook(
    *,
    update: dict[str, Any],
    raw_request: Request,
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    agent_service: ClaudeAgentService,
    panel_access_service: PanelAccessService,
    notifier: TelegramNotifierService,
    admin_config_service: AdminConfigService,
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
    session_identity = build_telegram_session_identity(extracted, telegram_settings)

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
            panel_access_service=panel_access_service,
            notifier=notifier,
            session_identity=session_identity,
        )

    session = openclaw_service.find_session_by_key(channel="telegram", session_key=session_identity.session_key)
    if session is None:
        session = openclaw_service.find_session(channel="telegram", external_id=chat_id)
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
                },
            )
        )

    _append_user_event(
        openclaw_service=openclaw_service,
        session=session,
        text=text,
        update=update,
        extracted=extracted,
        session_identity=session_identity,
    )

    request_payload = ClaudeAgentCreateRequest(
        task_name=_build_task_name(chat_id, update, extracted),
        prompt=text,
        session_id=session.session_id,
        agent_name=telegram_settings.agent_name,
        generation_depth=max(1, min(telegram_settings.generation_depth, 10)),
        timeout_seconds=max(1, min(telegram_settings.timeout_seconds, 7200)),
        work_dir=str(telegram_settings.work_dir) if telegram_settings.work_dir else None,
        cli_args=telegram_settings.claude_args,
        command_override=telegram_settings.command_override,
        append_prompt=telegram_settings.append_prompt,
        images=extracted.get("images", []),  # 新增图片字段
        env={},
        metadata={
            "source": "telegram_webhook",
            "chat_id": chat_id,
            "update_id": _safe_int(update.get("update_id")),
            "message_id": extracted.get("message_id"),
            "username": extracted.get("username"),
            "has_images": len(extracted.get("images", [])) > 0,  # 标记是否有图片
            "scope": session_identity.scope.value,
            "session_key": session_identity.session_key,
            "assistant_id": session_identity.assistant_id,
            "chat_type": session_identity.chat_context.chat_type.value,
            "actor_role": session_identity.actor.role.value,
            "actor_user_id": session_identity.actor.user_id,
        },
    )

    try:
        agent_run = agent_service.create(request_payload)
    except ValueError as exc:
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            session_id=session.session_id,
            reason=str(exc),
        )
    except RuntimeError as exc:
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            session_id=session.session_id,
            reason=str(exc),
        )

    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=f"已接收，开始处理：{request_payload.task_name}",
        )

    background_tasks.add_task(
        _execute_agent_and_notify,
        agent_service=agent_service,
        notifier=notifier,
        chat_id=chat_id,
        agent_run_id=agent_run.agent_run_id,
        request_payload=request_payload,
    )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        agent_run_id=agent_run.agent_run_id,
        metadata={
            "task_name": request_payload.task_name,
            "generation_depth": request_payload.generation_depth,
            "timeout_seconds": request_payload.timeout_seconds,
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
            "raw_type": "message",
            "images": image_urls,  # 新增图片字段
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


def _handle_status_query(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    agent_service: ClaudeAgentService,
    panel_access_service: PanelAccessService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    session = openclaw_service.find_session_by_key(channel="telegram", session_key=session_identity.session_key)
    if session is None:
        session = openclaw_service.find_session(channel="telegram", external_id=chat_id)
    runs = []
    if session is not None:
        runs = [run for run in agent_service.list() if run.session_id == session.session_id]
        runs.sort(key=lambda item: item.updated_at, reverse=True)

    summary_lines = _build_status_summary_lines(
        chat_id=chat_id,
        session=session,
        runs=runs,
        session_identity=session_identity,
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
    return normalized in {
        "status",
        "task status",
        "任务状态",
        "状态",
        "查询状态",
        "查看状态",
        "进度",
        "面板",
    }


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
) -> list[str]:
    if session is None:
        return [
            f"chat_id: {chat_id}",
            f"scope: {session_identity.scope.value}",
            f"session_key: {session_identity.session_key}",
            "当前没有历史会话。",
            "发送任务文本后系统会自动创建会话并执行。",
        ]

    lines = [
        f"chat_id: {chat_id}",
        f"scope: {session.scope.value}",
        f"session_key: {session.session_key or session_identity.session_key}",
        f"session: {session.session_id}",
        f"session_status: {session.status.value}",
        f"active_runs: {sum(1 for run in runs if run.status.value in {'queued', 'running'})}",
    ]
    if session.actor is not None:
        lines.append(f"actor_role: {session.actor.role.value}")
    if not runs:
        lines.append("最近任务: 暂无")
        return lines

    lines.append("最近任务:")
    for run in runs[:3]:
        lines.append(f"- {run.agent_run_id} | {run.status.value} | {run.task_name}")
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
