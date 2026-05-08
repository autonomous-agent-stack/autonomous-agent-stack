from __future__ import annotations

from fastapi.testclient import TestClient

from autoresearch.api.main import app
from autoresearch.api.dependencies import get_telegram_notifier_service
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
