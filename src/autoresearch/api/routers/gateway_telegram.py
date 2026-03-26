from __future__ import annotations

from datetime import datetime, timezone
import os
import shlex
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from autoresearch.api.dependencies import (
    get_claude_agent_service,
    get_openclaw_compat_service,
    get_panel_access_service,
    get_telegram_notifier_service,
)
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.group_access import GroupAccessManager
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.models import (
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSessionRead,
    TelegramWebhookAck,
)


router = APIRouter(prefix="/api/v1/gateway/telegram", tags=["gateway", "telegram"])


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
) -> TelegramWebhookAck:
    _validate_secret_token(raw_request)

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
        )

    session = openclaw_service.find_session(channel="telegram", external_id=chat_id)
    if session is None:
        session = openclaw_service.create_session(
            OpenClawSessionCreateRequest(
                channel="telegram",
                external_id=chat_id,
                title=f"telegram-{chat_id}",
                metadata={
                    "source": "telegram_webhook",
                    "created_at": _utc_now(),
                },
            )
        )

    _append_user_event(
        openclaw_service=openclaw_service,
        session=session,
        text=text,
        update=update,
        extracted=extracted,
    )

    request_payload = ClaudeAgentCreateRequest(
        task_name=_build_task_name(chat_id, update, extracted),
        prompt=text,
        session_id=session.session_id,
        agent_name=os.getenv("AUTORESEARCH_TELEGRAM_AGENT_NAME"),
        generation_depth=_bounded_env_int("AUTORESEARCH_TELEGRAM_GENERATION_DEPTH", 1, 1, 10),
        timeout_seconds=_bounded_env_int("AUTORESEARCH_TELEGRAM_TIMEOUT_SECONDS", 900, 1, 7200),
        work_dir=os.getenv("AUTORESEARCH_TELEGRAM_WORK_DIR"),
        cli_args=_env_cli_args("AUTORESEARCH_TELEGRAM_CLAUDE_ARGS"),
        command_override=_env_command_override("AUTORESEARCH_TELEGRAM_CLAUDE_COMMAND_OVERRIDE"),
        append_prompt=_env_bool("AUTORESEARCH_TELEGRAM_APPEND_PROMPT", default=True),
        images=extracted.get("images", []),  # 新增图片字段
        env={},
        metadata={
            "source": "telegram_webhook",
            "chat_id": chat_id,
            "update_id": _safe_int(update.get("update_id")),
            "message_id": extracted.get("message_id"),
            "username": extracted.get("username"),
            "has_images": len(extracted.get("images", [])) > 0,  # 标记是否有图片
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
    expected = os.getenv("AUTORESEARCH_TELEGRAM_SECRET_TOKEN", "").strip()
    if not expected:
        return
    provided = raw_request.headers.get("x-telegram-bot-api-secret-token", "").strip()
    if provided != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid telegram secret token")


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
                    bot_token = os.getenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "")
                    if bot_token:
                        image_urls.append(f"telegram://{file_id}")
        
        return {
            "chat_id": _safe_str(chat.get("id")),
            "text": (message.get("text") or message.get("caption") or "").strip(),
            "message_id": message.get("message_id"),
            "username": from_user.get("username"),
            "from_user_id": _safe_int(from_user.get("id")),
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
            "text": (callback.get("data") or "").strip(),
            "message_id": callback_message.get("message_id"),
            "username": from_user.get("username"),
            "from_user_id": _safe_int(from_user.get("id")),
            "raw_type": "callback_query",
        }
    return None


def _append_user_event(
    openclaw_service: OpenClawCompatService,
    session: OpenClawSessionRead,
    text: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
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
            },
        ),
    )


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
) -> TelegramWebhookAck:
    session = openclaw_service.find_session(channel="telegram", external_id=chat_id)
    runs = []
    if session is not None:
        runs = [run for run in agent_service.list() if run.session_id == session.session_id]
        runs.sort(key=lambda item: item.updated_at, reverse=True)

    summary_lines = _build_status_summary_lines(chat_id=chat_id, session=session, runs=runs)

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
            user_id = extracted.get("from_user_id")
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
            notifier.notify_status_magic_link,
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
    configured = os.getenv("AUTORESEARCH_TELEGRAM_MINI_APP_URL", "").strip()
    if configured:
        return configured
    if magic_link_url and magic_link_url.startswith("https://"):
        return magic_link_url
    return None


def _build_status_summary_lines(
    *,
    chat_id: str,
    session: OpenClawSessionRead | None,
    runs: list[Any],
) -> list[str]:
    if session is None:
        return [
            f"chat_id: {chat_id}",
            "当前没有历史会话。",
            "发送任务文本后系统会自动创建会话并执行。",
        ]

    lines = [
        f"chat_id: {chat_id}",
        f"session: {session.session_id}",
        f"session_status: {session.status.value}",
        f"active_runs: {sum(1 for run in runs if run.status.value in {'queued', 'running'})}",
    ]
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


def _env_command_override(name: str) -> list[str] | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    return shlex.split(raw)


def _env_cli_args(name: str) -> list[str]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return []
    return shlex.split(raw)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


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
