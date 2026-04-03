from __future__ import annotations

import json
from pathlib import Path

import pytest

from autoresearch.core.services import telegram_controller_handoff
from autoresearch.core.services.telegram_controller_handoff import TelegramControllerHandoffService


def test_linux_probe_success_routes_to_linux_without_persisting_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(telegram_controller_handoff.platform, "system", lambda: "Darwin")
    state_path = tmp_path / "telegram-controller.json"
    service = TelegramControllerHandoffService(
        linux_control_base_url="http://linux.example",
        state_path=state_path,
    )
    monkeypatch.setattr(service, "_probe_linux_controller", lambda: True)

    decision = service.evaluate(chat_id="9527", text="hello")

    assert decision.route == "forward_to_linux"
    assert decision.mode == "linux_active"
    assert decision.linux_online is True
    assert decision.notices == []
    assert not state_path.exists()


def test_linux_probe_failure_enters_mac_active_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(telegram_controller_handoff.platform, "system", lambda: "Darwin")
    state_path = tmp_path / "telegram-controller.json"
    service = TelegramControllerHandoffService(
        linux_control_base_url="http://linux.example",
        state_path=state_path,
    )
    monkeypatch.setattr(service, "_probe_linux_controller", lambda: False)

    first = service.evaluate(chat_id="9527", text="/task short note")
    assert first.route == "local"
    assert first.mode == "mac_active"
    assert first.linux_online is False
    assert len(first.notices) == 1
    assert first.notices[0].kind == "takeover"

    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    assert persisted["mode"] == "mac_active"
    assert persisted["lease_expires_at"] is not None

    second = service.evaluate(chat_id="9527", text="/task another short note")
    assert second.route == "local"
    assert second.mode == "mac_active"
    assert second.notices == []


def test_linux_recovery_clears_takeover_state_and_emits_release_notice(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(telegram_controller_handoff.platform, "system", lambda: "Darwin")
    state_path = tmp_path / "telegram-controller.json"
    service = TelegramControllerHandoffService(
        linux_control_base_url="http://linux.example",
        state_path=state_path,
    )

    monkeypatch.setattr(service, "_probe_linux_controller", lambda: False)
    service.evaluate(chat_id="9527", text="/task short note")
    assert state_path.exists()

    monkeypatch.setattr(service, "_probe_linux_controller", lambda: True)
    recovered = service.evaluate(chat_id="9527", text="/status")

    assert recovered.route == "forward_to_linux"
    assert recovered.mode == "linux_active"
    assert recovered.linux_online is True
    assert len(recovered.notices) == 1
    assert recovered.notices[0].kind == "release"
    assert not state_path.exists()


def test_linux_runtime_bypasses_handoff_and_stays_local(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(telegram_controller_handoff.platform, "system", lambda: "Linux")
    state_path = tmp_path / "telegram-controller.json"
    service = TelegramControllerHandoffService(
        linux_control_base_url="http://linux.example",
        state_path=state_path,
    )
    monkeypatch.setattr(service, "_probe_linux_controller", lambda: False)

    decision = service.evaluate(chat_id="9527", text="hello")

    assert decision.route == "local"
    assert decision.mode == "linux_active"
    assert decision.linux_online is True
    assert decision.notices == []
    assert not state_path.exists()
