from __future__ import annotations

from fastapi.testclient import TestClient

from autoresearch.api import dependencies as api_dependencies
from autoresearch.api.main import app
from autoresearch.api.dependencies import get_telegram_notifier_service
from autoresearch.api.settings import clear_settings_caches
from tests.test_gateway_telegram import _StubTelegramNotifier, telegram_client  # noqa: F401


def test_telegram_today_disabled_does_not_create_control_plane_task(
    telegram_client: TestClient,
) -> None:
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 9101,
                "message": {
                    "message_id": 901,
                    "text": "/today",
                    "chat": {"id": 88091, "type": "private"},
                },
            },
        )
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is False
    assert payload["metadata"]["status"] == "package_disabled"
    assert payload["metadata"]["personal_package_id"] == "personal.life_companion"
    assert telegram_client._control_plane_service.list_tasks() == []  # type: ignore[attr-defined]


def test_telegram_open_study_remote_disabled_does_not_create_task(
    telegram_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_ENABLED_PERSONAL_PACKAGES",
        "personal.study_workspace,personal.entertainment_curator,personal.life_companion",
    )
    monkeypatch.setenv("AUTORESEARCH_PERSONAL_REMOTE_ENABLED", "false")
    clear_settings_caches()
    api_dependencies.get_life_companion_service.cache_clear()
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 9102,
                "message": {
                    "message_id": 902,
                    "text": "/open-study",
                    "from": {"id": 88092, "is_bot": False, "first_name": "Tester"},
                    "chat": {"id": 88092, "type": "private"},
                },
            },
        )
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is False
    assert payload["metadata"]["status"] == "remote_disabled"
    assert telegram_client._control_plane_service.list_tasks() == []  # type: ignore[attr-defined]
    assert "remote entry is disabled" in notifier.messages[0]["text"]


def test_telegram_life_returns_tokenized_study_link(
    telegram_client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_ENABLED_PERSONAL_PACKAGES",
        "personal.study_workspace,personal.entertainment_curator,personal.life_companion",
    )
    monkeypatch.setenv("AUTORESEARCH_PERSONAL_REMOTE_ENABLED", "true")
    monkeypatch.setenv("AUTORESEARCH_PANEL_JWT_SECRET", "life-panel-secret")
    monkeypatch.setenv("AUTORESEARCH_TELEGRAM_ALLOWED_UIDS", "88092")
    monkeypatch.setenv("AUTORESEARCH_PERSONAL_REMOTE_BASE_URL", "https://life.example/study")
    clear_settings_caches()
    api_dependencies.get_life_companion_service.cache_clear()
    api_dependencies.get_panel_access_service.cache_clear()
    notifier = _StubTelegramNotifier()
    app.dependency_overrides[get_telegram_notifier_service] = lambda: notifier
    try:
        response = telegram_client.post(
            "/api/v1/gateway/telegram/webhook",
            json={
                "update_id": 9103,
                "message": {
                    "message_id": 903,
                    "text": "/life",
                    "from": {"id": 88092, "is_bot": False, "first_name": "Tester"},
                    "chat": {"id": 88092, "type": "private"},
                },
            },
        )
    finally:
        app.dependency_overrides.pop(get_telegram_notifier_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted"] is True
    assert payload["metadata"]["status"] == "magic_link_created"
    assert telegram_client._control_plane_service.list_tasks() == []  # type: ignore[attr-defined]
    assert "https://life.example/study?token=" in notifier.messages[0]["text"]
