from __future__ import annotations

from typing import Any

from pydantic import Field

from autoresearch.api.settings import TelegramSettings
from autoresearch.shared.models import (
    ActorRole,
    AssistantScope,
    ChatType,
    OpenClawSessionActorRead,
    OpenClawSessionChatContextRead,
    StrictModel,
)


class TelegramSessionIdentityRead(StrictModel):
    scope: AssistantScope = AssistantScope.PERSONAL
    session_key: str = Field(..., min_length=1)
    assistant_id: str = Field(..., min_length=1)
    actor: OpenClawSessionActorRead
    chat_context: OpenClawSessionChatContextRead


def build_telegram_session_identity(
    extracted: dict[str, Any],
    settings: TelegramSettings,
    *,
    scope_override: AssistantScope | None = None,
) -> TelegramSessionIdentityRead:
    chat_id = _safe_str(extracted.get("chat_id"))
    user_id = _safe_str(extracted.get("from_user_id") or extracted.get("from_id"))
    username = _safe_str(extracted.get("username"))
    chat_type = _coerce_chat_type(extracted.get("chat_type"))
    message_id = _safe_str(extracted.get("message_id"))

    scope = scope_override or (AssistantScope.PERSONAL if chat_type == ChatType.PRIVATE else AssistantScope.SHARED)
    role = _resolve_actor_role(user_id=user_id, settings=settings)

    if scope == AssistantScope.PERSONAL:
        identity_target = user_id or chat_id or "unknown"
        session_key = (
            f"telegram:personal:user:{identity_target}"
            if user_id
            else f"telegram:personal:chat:{identity_target}"
        )
        assistant_id = f"telegram-user:{identity_target}"
    else:
        identity_target = chat_id or user_id or "unknown"
        session_key = (
            f"telegram:shared:chat:{identity_target}"
            if chat_id
            else f"telegram:shared:user:{identity_target}"
        )
        assistant_id = (settings.shared_assistant_id or "").strip() or "telegram-shared"

    return TelegramSessionIdentityRead(
        scope=scope,
        session_key=session_key,
        assistant_id=assistant_id,
        actor=OpenClawSessionActorRead(
            user_id=user_id,
            username=username,
            role=role,
        ),
        chat_context=OpenClawSessionChatContextRead(
            chat_id=chat_id,
            chat_type=chat_type,
            user_id=user_id,
            message_id=message_id,
        ),
    )


def _resolve_actor_role(*, user_id: str | None, settings: TelegramSettings) -> ActorRole:
    if not user_id:
        return ActorRole.UNKNOWN
    if user_id in settings.owner_uids:
        return ActorRole.OWNER
    if user_id in settings.partner_uids:
        return ActorRole.PARTNER
    if user_id in settings.allowed_uids:
        return ActorRole.MEMBER
    return ActorRole.UNKNOWN


def _coerce_chat_type(raw_value: Any) -> ChatType:
    normalized = _safe_str(raw_value)
    if normalized is None:
        return ChatType.UNKNOWN
    try:
        return ChatType(normalized.strip().lower())
    except ValueError:
        return ChatType.UNKNOWN


def _safe_str(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
