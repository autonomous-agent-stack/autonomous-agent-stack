from __future__ import annotations

from typing import Any

from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.telegram_identity import (
    TelegramSessionIdentityRead,
    build_telegram_session_identity,
)
from autoresearch.shared.models import AssistantScope, ChatType


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
    from autoresearch.shared.models import OpenClawSessionRead

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
