from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "telegram_self_check.py"


def load_module():
    spec = importlib.util.spec_from_file_location("telegram_self_check", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_offline_mode_runs_local_webhook_checks_without_token_or_allowlist(monkeypatch, capsys) -> None:
    module = load_module()

    monkeypatch.setattr(module, "load_default_env", lambda: None)
    monkeypatch.setattr(module, "find_api_pid", lambda port: 4242)
    monkeypatch.setattr(module, "parse_env_from_pid", lambda pid: {})
    monkeypatch.setattr(module, "tail_lines", lambda path, max_lines=60: [])

    def fake_http_json(url: str, *, method: str = "GET", headers=None, body=None, timeout: float = 10.0):
        if url.endswith("/health"):
            return 200, {"status": "ok"}, '{"status": "ok"}'
        if url.endswith("/webhook"):
            assert method == "POST"
            assert body is not None
            assert body["message"]["chat"]["id"] == 999999
            assert body["message"]["text"] in {"/help", "/status"}
            return 200, {"accepted": True, "chat_id": "999999"}, '{"accepted": true}'
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(module, "http_json", fake_http_json)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH), "--port", "8000", "--offline"])

    assert module.main() == 0

    output = capsys.readouterr().out
    assert "[SKIP] bot_token_env: not required in offline mode" in output
    assert "[PASS] gateway_health: status=200 body={'status': 'ok'}" in output
    assert "[PASS] local_webhook_help:" in output
    assert "[PASS] local_webhook_status:" in output
    assert "Offline core path looks healthy." in output
