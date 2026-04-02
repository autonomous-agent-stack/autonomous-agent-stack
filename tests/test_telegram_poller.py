from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "telegram_poller.py"


def load_module():
    spec = importlib.util.spec_from_file_location("telegram_poller", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_poll_once_forwards_updates_and_persists_offset(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    offset_path = tmp_path / "offset.txt"
    forwarded: list[tuple[dict[str, object], str, str | None]] = []

    def fake_telegram_call(token: str, method_name: str, params: dict[str, object]):
        assert token == "bot-token"
        assert method_name == "getUpdates"
        assert params["offset"] == 12
        return {
            "ok": True,
            "result": [
                {"update_id": 12, "message": {"text": "/ping"}},
                {"update_id": 13, "message": {"text": "/status"}},
            ],
        }

    def fake_forward_update(update: dict[str, object], webhook_url: str, secret_token: str | None):
        forwarded.append((update, webhook_url, secret_token))
        return 200, {"accepted": True}

    monkeypatch.setattr(module, "telegram_call", fake_telegram_call)
    monkeypatch.setattr(module, "forward_update", fake_forward_update)

    result = module.poll_once(
        bot_token="bot-token",
        webhook_url="http://127.0.0.1:8001/api/v1/gateway/telegram/webhook",
        secret_token="secret",
        offset=12,
        offset_path=offset_path,
        poll_timeout=25,
        allowed_updates=["message"],
    )

    assert result.offset == 14
    assert result.processed_updates == 2
    assert offset_path.read_text(encoding="utf-8") == "14"
    assert len(forwarded) == 2
    assert forwarded[0][1].endswith("/api/v1/gateway/telegram/webhook")
    assert forwarded[0][2] == "secret"


def test_poll_once_keeps_offset_when_no_updates(tmp_path: Path, monkeypatch) -> None:
    module = load_module()
    offset_path = tmp_path / "offset.txt"

    def fake_telegram_call(token: str, method_name: str, params: dict[str, object]):
        return {"ok": True, "result": []}

    monkeypatch.setattr(module, "telegram_call", fake_telegram_call)

    result = module.poll_once(
        bot_token="bot-token",
        webhook_url="http://127.0.0.1:8001/api/v1/gateway/telegram/webhook",
        secret_token=None,
        offset=21,
        offset_path=offset_path,
        poll_timeout=25,
        allowed_updates=["message"],
    )

    assert result.offset == 21
    assert result.processed_updates == 0
    assert not offset_path.exists()


def test_main_returns_2_when_bot_token_missing(monkeypatch, capsys) -> None:
    module = load_module()
    monkeypatch.setattr(module, "load_default_env", lambda: None)
    monkeypatch.setattr(module, "resolve_bot_token", lambda: None)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH)])

    assert module.main() == 2
    output = capsys.readouterr().out
    assert "missing TELEGRAM_BOT_TOKEN" in output
