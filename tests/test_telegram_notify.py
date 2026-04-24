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


def test_send_message_get_message_id_returns_message_id(monkeypatch) -> None:
    def _fake_urlopen(req, timeout):  # noqa: ANN001
        _ = req, timeout
        return _FakeResponse({"ok": True, "result": {"message_id": 9001}})

    monkeypatch.setattr("autoresearch.core.services.telegram_notify.request.urlopen", _fake_urlopen)

    service = TelegramNotifierService(bot_token="token", max_attempts=2)
    mid = service.send_message_get_message_id(chat_id="42", text="queued")
    assert mid == 9001


def test_send_message_get_message_id_returns_none_when_not_ok(monkeypatch) -> None:
    def _fake_urlopen(req, timeout):  # noqa: ANN001
        _ = req, timeout
        return _FakeResponse({"ok": False, "description": "bad request"})

    monkeypatch.setattr("autoresearch.core.services.telegram_notify.request.urlopen", _fake_urlopen)

    service = TelegramNotifierService(bot_token="token", max_attempts=2)
    assert service.send_message_get_message_id(chat_id="42", text="queued") is None


def test_notify_status_magic_link_hides_localhost_panel_url(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_send_message(**kwargs):  # noqa: ANN003
        captured.update(kwargs)
        return True

    service = TelegramNotifierService(bot_token="token")
    monkeypatch.setattr(service, "send_message", _fake_send_message)

    result = service.notify_status_magic_link(
        chat_id="1",
        summary_lines=["workers_online: 0"],
        magic_link_url="http://127.0.0.1:8001/api/v1/panel/view?token=secret",
        expires_at_iso="2026-04-23T14:40:50Z",
    )

    assert result is True
    text = str(captured["text"])
    assert text.startswith("[状态查询]")
    assert "Web 面板:" not in text
    assert "仅当前机器可打开" in text
    assert "token=secret" not in text


def test_notify_status_magic_link_prefers_mini_app_button_over_raw_magic_link(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_send_message(**kwargs):  # noqa: ANN003
        captured.update(kwargs)
        return True

    service = TelegramNotifierService(bot_token="token")
    monkeypatch.setattr(service, "send_message", _fake_send_message)

    result = service.notify_status_magic_link(
        chat_id="1",
        summary_lines=["workers_online: 1"],
        magic_link_url="https://panel.example/api/v1/panel/view?token=secret",
        expires_at_iso="2026-04-23T14:40:50Z",
        mini_app_url="https://panel.example/api/v1/panel/view",
    )

    assert result is True
    text = str(captured["text"])
    assert text.startswith("[状态查询]")
    assert "请使用下方按钮打开" in text
    assert "Web 面板:" not in text
    reply_markup = captured["reply_markup"]
    assert isinstance(reply_markup, dict)
    button = reply_markup["inline_keyboard"][0][0]
    assert button["web_app"]["url"] == "https://panel.example/api/v1/panel/view"
