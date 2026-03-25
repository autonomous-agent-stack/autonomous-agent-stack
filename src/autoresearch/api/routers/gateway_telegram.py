from __future__ import annotations

from datetime import datetime, timezone
import os
import shlex
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from autoresearch.api.dependencies import get_claude_agent_service, get_openclaw_compat_service
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import (
    ClaudeAgentCreateRequest,
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
        env={},
        metadata={
            "source": "telegram_webhook",
            "chat_id": chat_id,
            "update_id": _safe_int(update.get("update_id")),
            "message_id": extracted.get("message_id"),
            "username": extracted.get("username"),
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

    background_tasks.add_task(agent_service.execute, agent_run.agent_run_id, request_payload)
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
        return {
            "chat_id": _safe_str(chat.get("id")),
            "text": (message.get("text") or message.get("caption") or "").strip(),
            "message_id": message.get("message_id"),
            "username": from_user.get("username"),
            "raw_type": "message",
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
