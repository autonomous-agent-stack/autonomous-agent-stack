from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks

from autoresearch.api.settings import load_telegram_settings
from autoresearch.core.adapters import CapabilityDomain, CapabilityProviderRegistry, SkillProvider
from autoresearch.core.services.admin_config import AdminConfigService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.telegram_identity import (
    TelegramSessionIdentityRead,
)
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.models import (
    AdminChannelConfigCreateRequest,
    AdminChannelConfigUpdateRequest,
    AssistantScope,
    JobStatus,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    OpenClawSessionRead,
)

from ._extract import _safe_int, _safe_str
from ._messages import _truncate_telegram_text, _utc_now


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


def _sync_session_runtime_identity(
    *,
    openclaw_service: OpenClawCompatService,
    session: OpenClawSessionRead,
    background_tasks: BackgroundTasks,
    notifier: TelegramNotifierService,
    chat_id: str,
) -> OpenClawSessionRead:
    from autoresearch.api.routers import gateway_telegram

    runtime = gateway_telegram.get_runtime_identity()
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


def _build_session_title(*, chat_id: str, session_identity: TelegramSessionIdentityRead) -> str:
    scope = session_identity.scope
    if scope == AssistantScope.PERSONAL and session_identity.actor.user_id:
        return f"telegram-personal-{session_identity.actor.user_id}"
    if scope == AssistantScope.SHARED:
        return f"telegram-shared-{chat_id}"
    return f"telegram-{chat_id}"


def _build_task_name(chat_id: str, update: dict[str, Any], extracted: dict[str, Any]) -> str:
    message_id = extracted.get("message_id")
    update_id = _safe_int(update.get("update_id"))
    suffix = message_id if message_id is not None else update_id
    if suffix is None:
        suffix = _utc_now().replace("-", "").replace(":", "").replace(".", "")
    return f"tg_{chat_id}_{suffix}"


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
    from ._extract import _SHORT_AFFIRMATIVE_RE, _YOUTUBE_PROCESS_CONFIRM_RE

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
