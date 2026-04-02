from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import time


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


def test_resolve_local_api_host_maps_wildcard_bind_to_loopback(monkeypatch) -> None:
    module = load_module()

    monkeypatch.setenv("AUTORESEARCH_API_HOST", "0.0.0.0")

    assert module.resolve_local_api_host() == "127.0.0.1"


def test_is_poll_conflict_error_detects_getupdates_conflict() -> None:
    module = load_module()

    assert module.is_poll_conflict_error(RuntimeError("telegram getUpdates http 409: Conflict: terminated by other getUpdates request"))
    assert module.is_poll_conflict_error(RuntimeError("HTTP Error 409: Conflict"))
    assert module.is_poll_conflict_error(RuntimeError("Conflict: can't use getUpdates method while webhook is active"))
    assert module.is_poll_conflict_error(RuntimeError("terminated by other getUpdates request"))
    assert module.is_poll_conflict_error(RuntimeError("409: Conflict"))
    assert module.is_poll_conflict_error(ValueError("HTTP 409 conflict"))
    assert module.is_poll_conflict_error(RuntimeError("other getUpdates request in progress"))
    assert module.is_poll_conflict_error(RuntimeError("telegram getUpdates http 409"))
    assert not module.is_poll_conflict_error(RuntimeError("telegram getUpdates http 500"))


def test_decide_active_controller_keeps_linux_primary_active_when_local_health_ok() -> None:
    module = load_module()
    identity = module.ControllerIdentity(runtime_host="linux", execution_role="primary", controller_name="linux")

    decision = module.decide_active_controller(
        identity=identity,
        previous_active_controller=None,
        local_controller_online=True,
        primary_controller_online=None,
        primary_probe_configured=False,
    )

    assert decision.active_controller == "linux"
    assert decision.should_poll is True
    assert decision.reason == "local_primary_online"
    assert decision.notification_text is None


def test_decide_active_controller_promotes_mac_backup_only_when_linux_unreachable() -> None:
    module = load_module()
    identity = module.ControllerIdentity(runtime_host="macos", execution_role="backup", controller_name="macos")

    decision = module.decide_active_controller(
        identity=identity,
        previous_active_controller="linux",
        local_controller_online=True,
        primary_controller_online=False,
        primary_probe_configured=True,
    )

    assert decision.active_controller == "macos"
    assert decision.should_poll is True
    assert decision.reason == "linux_primary_unreachable"
    assert decision.notification_text is not None
    assert "Mac 备用控制台开始接管" in decision.notification_text


def test_decide_active_controller_releases_mac_backup_when_linux_recovers() -> None:
    module = load_module()
    identity = module.ControllerIdentity(runtime_host="macos", execution_role="backup", controller_name="macos")

    decision = module.decide_active_controller(
        identity=identity,
        previous_active_controller="macos",
        local_controller_online=True,
        primary_controller_online=True,
        primary_probe_configured=True,
    )

    assert decision.active_controller == "linux"
    assert decision.should_poll is False
    assert decision.reason == "linux_primary_online"
    assert decision.notification_text is not None
    assert "Linux 已恢复在线" in decision.notification_text


def test_main_backup_skips_polling_when_linux_primary_is_online(monkeypatch, tmp_path: Path, capsys) -> None:
    module = load_module()
    controller_state_path = tmp_path / "active_controller.json"

    monkeypatch.setattr(module, "load_default_env", lambda: None)
    monkeypatch.setattr(module, "resolve_bot_token", lambda: "bot-token")
    monkeypatch.setattr(module, "resolve_webhook_url", lambda: "http://127.0.0.1:8001/api/v1/gateway/telegram/webhook")
    monkeypatch.setattr(module, "resolve_offset_file", lambda: tmp_path / "offset.txt")
    monkeypatch.setattr(module, "resolve_controller_state_file", lambda: controller_state_path)
    monkeypatch.setattr(module, "resolve_controller_identity", lambda: module.ControllerIdentity("macos", "backup", "macos"))
    monkeypatch.setattr(module, "resolve_primary_probe_urls", lambda: ["http://linux-primary:8001/healthz"])
    monkeypatch.setattr(module, "resolve_controller_notify_chat_id", lambda: None)
    monkeypatch.setattr(module, "telegram_call", lambda token, method_name, params: {"ok": True, "result": {"username": "bota"}} if method_name == "getMe" else {"ok": True, "result": []})
    monkeypatch.setattr(
        module,
        "controller_target_online",
        lambda urls, timeout_seconds=5.0: True,
    )

    called = {"poll_once": False}

    def fake_poll_once(**kwargs):
        called["poll_once"] = True
        return module.PollResult(offset=0, processed_updates=0)

    monkeypatch.setattr(module, "poll_once", fake_poll_once)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH), "--once"])

    assert module.main() == 0
    assert called["poll_once"] is False
    state = module.read_controller_state(controller_state_path)
    assert state["active_controller"] == "linux"
    assert state["should_poll"] is False
    assert state["reason"] == "linux_primary_online"
    assert "standby active=linux" in capsys.readouterr().out


def test_controller_target_online_rejects_stale_primary_lease(monkeypatch) -> None:
    module = load_module()
    stale_payload = {
        "status": "ok",
        "controller_status": "stale",
        "active_controller": "linux",
    }
    monkeypatch.setattr(module, "http_json", lambda **kwargs: (200, stale_payload))

    assert module.controller_target_online(["http://linux-primary:8001/api/v1/cluster/health"]) is False


def test_main_primary_reclaims_active_controller_and_emits_recovered_signal(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    module = load_module()
    controller_state_path = tmp_path / "active_controller.json"
    previous_updated_at = int(time.time()) - 120
    module.write_controller_state(
        controller_state_path,
        {
            "active_controller": "linux",
            "controller_name": "linux",
            "execution_role": "primary",
            "runtime_host": "linux",
            "should_poll": False,
            "reason": "local_primary_unhealthy",
            "lease_ttl_seconds": 30,
            "updated_at": previous_updated_at,
        },
    )

    monkeypatch.setattr(module, "load_default_env", lambda: None)
    monkeypatch.setattr(module, "resolve_bot_token", lambda: "bot-token")
    monkeypatch.setattr(module, "resolve_webhook_url", lambda: "http://127.0.0.1:8001/api/v1/gateway/telegram/webhook")
    monkeypatch.setattr(module, "resolve_offset_file", lambda: tmp_path / "offset.txt")
    monkeypatch.setattr(module, "resolve_controller_state_file", lambda: controller_state_path)
    monkeypatch.setattr(module, "resolve_controller_identity", lambda: module.ControllerIdentity("linux", "primary", "linux"))
    monkeypatch.setattr(module, "resolve_primary_probe_urls", lambda: [])
    monkeypatch.setattr(module, "resolve_controller_notify_chat_id", lambda: None)
    monkeypatch.setattr(module, "resolve_local_health_urls", lambda: ["http://127.0.0.1:8001/healthz"])
    monkeypatch.setattr(
        module,
        "telegram_call",
        lambda token, method_name, params: {"ok": True, "result": {"username": "bota"}} if method_name == "getMe" else {"ok": True, "result": []},
    )
    monkeypatch.setattr(module, "controller_target_online", lambda urls, timeout_seconds=5.0: True)
    monkeypatch.setattr(module, "poll_once", lambda **kwargs: module.PollResult(offset=0, processed_updates=0))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH), "--once"])

    assert module.main() == 0
    state = module.read_controller_state(controller_state_path)
    assert state["active_controller"] == "linux"
    assert state["controller_status"] == "online"
    assert state["status_signal"] == "recovered"
    assert state["lease_ttl_seconds"] == 30
    assert state["lease_expires_at"] >= state["updated_at"]
    assert "controller identity name=linux role=primary" in capsys.readouterr().out


def test_main_once_surfaces_poll_conflict_without_retry_spam(monkeypatch, tmp_path: Path, capsys) -> None:
    module = load_module()

    monkeypatch.setattr(module, "load_default_env", lambda: None)
    monkeypatch.setattr(module, "resolve_bot_token", lambda: "bot-token")
    monkeypatch.setattr(module, "resolve_webhook_url", lambda: "http://127.0.0.1:8001/api/v1/gateway/telegram/webhook")
    monkeypatch.setattr(module, "resolve_offset_file", lambda: tmp_path / "offset.txt")
    monkeypatch.setattr(module, "resolve_controller_state_file", lambda: tmp_path / "active_controller.json")
    monkeypatch.setattr(module, "resolve_controller_identity", lambda: module.ControllerIdentity("linux", "primary", "linux"))
    monkeypatch.setattr(module, "resolve_primary_probe_urls", lambda: [])
    monkeypatch.setattr(module, "resolve_controller_notify_chat_id", lambda: None)
    monkeypatch.setattr(module, "resolve_local_health_urls", lambda: ["http://127.0.0.1:8001/healthz"])
    monkeypatch.setattr(
        module,
        "telegram_call",
        lambda token, method_name, params: {"ok": True, "result": {"username": "bota"}} if method_name == "getMe" else {"ok": True, "result": []},
    )
    monkeypatch.setattr(module, "controller_target_online", lambda urls, timeout_seconds=5.0: True)
    monkeypatch.setattr(
        module,
        "poll_once",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("telegram getUpdates http 409: Conflict: terminated by other getUpdates request")),
    )
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH), "--once"])

    assert module.main() == 1
    assert "getUpdates conflict detected" in capsys.readouterr().out
