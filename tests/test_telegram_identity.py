from __future__ import annotations

import pytest

from autoresearch.api.settings import load_telegram_settings
from autoresearch.core.services.telegram_identity import build_telegram_session_identity


def test_private_chat_routes_to_personal_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_OWNER_UIDS", "42")
    settings = load_telegram_settings()

    identity = build_telegram_session_identity(
        {
            "chat_id": "42",
            "chat_type": "private",
            "from_user_id": 42,
            "username": "owner",
            "message_id": 100,
        },
        settings,
    )

    assert identity.scope.value == "personal"
    assert identity.session_key == "telegram:personal:user:42"
    assert identity.assistant_id == "telegram-user:42"
    assert identity.actor.role.value == "owner"
    assert identity.chat_context.chat_type.value == "private"


def test_group_chat_routes_to_shared_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_PARTNER_UIDS", "99")
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_SHARED_ASSISTANT_ID", "household-main")
    settings = load_telegram_settings()

    identity = build_telegram_session_identity(
        {
            "chat_id": "-100555",
            "chat_type": "supergroup",
            "from_user_id": 99,
            "username": "partner",
            "message_id": 200,
        },
        settings,
    )

    assert identity.scope.value == "shared"
    assert identity.session_key == "telegram:shared:chat:-100555"
    assert identity.assistant_id == "household-main"
    assert identity.actor.role.value == "partner"
    assert identity.chat_context.chat_type.value == "supergroup"
