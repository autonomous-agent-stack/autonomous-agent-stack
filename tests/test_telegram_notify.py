from __future__ import annotations

import json
from urllib import error

from autoresearch.core.services.telegram_notify import TelegramNotifierService


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_send_message_retries_once_then_succeeds(monkeypatch) -> None:
    calls = {"count": 0}

    def _fake_urlopen(req, timeout):  # noqa: ANN001
        _ = req, timeout
        calls["count"] += 1
        if calls["count"] == 1:
            raise error.URLError("temporary failure")
        return _FakeResponse({"ok": True})

    monkeypatch.setattr("autoresearch.core.services.telegram_notify.request.urlopen", _fake_urlopen)

    service = TelegramNotifierService(bot_token="token", max_attempts=2)

    assert service.send_message(chat_id="1", text="hello") is True
    assert calls["count"] == 2


def test_send_message_returns_false_after_retries(monkeypatch) -> None:
    calls = {"count": 0}

    def _fake_urlopen(req, timeout):  # noqa: ANN001
        _ = req, timeout
        calls["count"] += 1
        raise error.URLError("still failing")

    monkeypatch.setattr("autoresearch.core.services.telegram_notify.request.urlopen", _fake_urlopen)

    service = TelegramNotifierService(bot_token="token", max_attempts=2)

    assert service.send_message(chat_id="1", text="hello") is False
    assert calls["count"] == 2
