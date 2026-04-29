from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from autoresearch.agent_protocol.runtime_models import RuntimeRunRead, RuntimeRunRequest
from autoresearch.core.services.claude_runtime_service import (
    ClaudeRuntimeExecutionResult,
    ClaudeRuntimeService,
)
from autoresearch.core.services.worker_runtime_dispatch import (
    WorkerRuntimeDispatchService,
    build_runtime_run_request_for_telegram_hermes,
    runtime_run_read_to_claude_execution_result,
)
from autoresearch.shared.models import JobStatus


def test_build_runtime_run_request_for_telegram_hermes_minimal() -> None:
    payload = {
        "prompt": "hello",
        "task_name": "tg_task",
        "timeout_seconds": 120,
        "work_dir": "/tmp/ws",
        "metadata": {"hermes": {"profile": "local", "session_mode": "oneshot"}},
    }
    req = build_runtime_run_request_for_telegram_hermes(payload)
    assert req.runtime_id == "hermes"
    assert req.prompt == "hello"
    assert req.task_name == "tg_task"
    assert req.timeout_seconds == 120
    assert req.work_dir == "/tmp/ws"
    assert req.images == []
    assert req.skill_names == []
    assert req.command_override is None
    assert req.metadata.get("hermes", {}).get("profile") == "local"


def test_build_runtime_run_request_rejects_empty_prompt() -> None:
    with pytest.raises(ValueError, match="empty prompt"):
        build_runtime_run_request_for_telegram_hermes({"prompt": "   "})


def test_runtime_run_read_maps_to_execution_result() -> None:
    now = datetime.now(timezone.utc)
    read = RuntimeRunRead(
        runtime_id="hermes",
        run_id="run-1",
        session_id="sess-1",
        task_name="t",
        status=JobStatus.COMPLETED,
        summary="done",
        timeout_seconds=60,
        stdout_preview="out",
        stderr_preview=None,
        returncode=0,
        created_at=now,
        updated_at=now,
        metadata={},
    )
    out = runtime_run_read_to_claude_execution_result(read)
    assert out.status == JobStatus.COMPLETED
    assert out.stdout_preview == "out"
    assert out.result["runtime_run_id"] == "run-1"
    assert out.metrics["dispatch_runtime"] == "hermes"
    assert out.metrics["exit_reason"] == "completed"


def test_dispatch_claude_delegates_to_claude_runtime() -> None:
    claude = MagicMock(spec=ClaudeRuntimeService)
    claude.execute_payload.return_value = ClaudeRuntimeExecutionResult(
        message="ok",
        status=JobStatus.COMPLETED,
        agent_run_id="a1",
    )
    dispatch = WorkerRuntimeDispatchService(claude_runtime=claude, registry=MagicMock())
    payload = {"runtime_id": "claude", "prompt": "x", "session_key": "k"}
    out = dispatch.execute_payload(payload, worker_id="w1", queue_metadata=None)
    assert out.agent_run_id == "a1"
    claude.execute_payload.assert_called_once()


def test_dispatch_hermes_uses_registry() -> None:
    claude_rt = MagicMock(spec=ClaudeRuntimeService)
    claude_rt.session_record_service = MagicMock()
    adapter = MagicMock()
    now = datetime.now(timezone.utc)
    adapter.run.return_value = RuntimeRunRead(
        runtime_id="hermes",
        run_id="run-h",
        session_id=None,
        task_name="tg",
        status=JobStatus.COMPLETED,
        summary="s",
        timeout_seconds=60,
        created_at=now,
        updated_at=now,
        metadata={},
    )
    registry = MagicMock()
    registry.get.return_value = adapter

    dispatch = WorkerRuntimeDispatchService(claude_runtime=claude_rt, registry=registry)
    payload: dict[str, Any] = {
        "runtime_id": "hermes",
        "prompt": "ping",
        "task_name": "tg",
        "session_key": "sk1",
        "timeout_seconds": 60,
        "metadata": {"hermes": {"session_mode": "oneshot"}},
    }
    out = dispatch.execute_payload(payload, worker_id="w1", queue_metadata=None)
    assert out.status == JobStatus.COMPLETED
    registry.get.assert_called_once_with("hermes")
    adapter.run.assert_called_once()
    req = adapter.run.call_args[0][0]
    assert isinstance(req, RuntimeRunRequest)
    assert req.prompt == "ping"


def test_dispatch_hermes_polls_until_terminal_status() -> None:
    claude_rt = MagicMock(spec=ClaudeRuntimeService)
    claude_rt.session_record_service = MagicMock()
    adapter = MagicMock()
    now = datetime.now(timezone.utc)
    adapter.run.return_value = RuntimeRunRead(
        runtime_id="hermes",
        run_id="run-h",
        session_id="sess-h",
        task_name="tg",
        status=JobStatus.QUEUED,
        summary="queued",
        timeout_seconds=60,
        created_at=now,
        updated_at=now,
        metadata={},
    )
    adapter.status.side_effect = [
        MagicMock(
            run=RuntimeRunRead(
                runtime_id="hermes",
                run_id="run-h",
                session_id="sess-h",
                task_name="tg",
                status=JobStatus.RUNNING,
                summary="running",
                timeout_seconds=60,
                created_at=now,
                updated_at=now,
                metadata={},
            )
        ),
        MagicMock(
            run=RuntimeRunRead(
                runtime_id="hermes",
                run_id="run-h",
                session_id="sess-h",
                task_name="tg",
                status=JobStatus.COMPLETED,
                summary="done",
                timeout_seconds=60,
                stdout_preview="final output",
                created_at=now,
                updated_at=now,
                metadata={},
            )
        ),
    ]
    registry = MagicMock()
    registry.get.return_value = adapter

    dispatch = WorkerRuntimeDispatchService(claude_runtime=claude_rt, registry=registry)
    payload: dict[str, Any] = {
        "runtime_id": "hermes",
        "prompt": "ping",
        "task_name": "tg",
        "session_key": "sk1",
        "timeout_seconds": 60,
        "metadata": {"hermes": {"session_mode": "oneshot"}},
    }
    out = dispatch.execute_payload(payload, worker_id="w1", queue_metadata=None)

    assert out.status == JobStatus.COMPLETED
    assert out.stdout_preview == "final output"
    adapter.run.assert_called_once()
    assert adapter.status.call_count == 2


def test_dispatch_unknown_runtime() -> None:
    dispatch = WorkerRuntimeDispatchService(
        claude_runtime=MagicMock(spec=ClaudeRuntimeService),
        registry=MagicMock(),
    )
    out = dispatch.execute_payload({"runtime_id": "unknown", "prompt": "x"}, worker_id=None, queue_metadata=None)
    assert out.status == JobStatus.FAILED
    assert "unsupported" in (out.error or "").lower()
    assert out.result["error_kind"] == "unsupported_runtime"
    assert out.metrics["exit_reason"] == "unsupported_runtime"


def test_dispatch_hermes_interactive_fails_without_bridge() -> None:
    dispatch = WorkerRuntimeDispatchService(
        claude_runtime=MagicMock(spec=ClaudeRuntimeService),
        registry=MagicMock(),
        hermes_gateway_bridge=None,
    )
    out = dispatch.execute_payload(
        {
            "runtime_id": "hermes",
            "execution_mode": "interactive",
            "prompt": "hello",
        },
        worker_id=None,
        queue_metadata=None,
    )
    assert out.status == JobStatus.FAILED
    assert out.result is not None
    assert out.result.get("error_kind") == "interactive_bridge_unavailable"
    assert out.metrics.get("exit_reason") == "interactive_bridge_unavailable"


def test_dispatch_hermes_interactive_uses_bridge() -> None:
    bridge = MagicMock()
    bridge.execute_interactive.return_value = ClaudeRuntimeExecutionResult(
        message="ok",
        status=JobStatus.COMPLETED,
        result={"execution_mode": "interactive"},
    )
    dispatch = WorkerRuntimeDispatchService(
        claude_runtime=MagicMock(spec=ClaudeRuntimeService),
        registry=MagicMock(),
        hermes_gateway_bridge=bridge,
    )
    payload = {"runtime_id": "hermes", "execution_mode": "interactive", "prompt": "hello"}
    out = dispatch.execute_payload(payload, worker_id=None, queue_metadata=None)
    assert out.status == JobStatus.COMPLETED
    bridge.execute_interactive.assert_called_once_with(payload)


def test_telegram_hermes_metadata_default_profile_is_default() -> None:
    from autoresearch.api.settings import TelegramSettings

    s = TelegramSettings(bot_token="t", owner_uids={"1"}, partner_uids=set(), allowed_uids={"1"})
    frag = s.hermes_metadata_fragment_for_worker()
    assert frag["session_mode"] == "oneshot"
    assert frag["profile"] == "default"


def test_telegram_hermes_profile_legacy_butler_maps_to_default() -> None:
    from autoresearch.api.settings import TelegramSettings

    s = TelegramSettings(
        bot_token="t",
        owner_uids={"1"},
        partner_uids=set(),
        allowed_uids={"1"},
        telegram_hermes_profile="butler",
    )
    assert s.telegram_hermes_profile == "default"
    assert s.hermes_metadata_fragment_for_worker()["profile"] == "default"


def test_telegram_hermes_execution_mode_normalized() -> None:
    from autoresearch.api.settings import TelegramSettings

    s = TelegramSettings(
        bot_token="t",
        owner_uids={"1"},
        partner_uids=set(),
        allowed_uids={"1"},
        AUTORESEARCH_TELEGRAM_HERMES_EXECUTION_MODE="INTERACTIVE",
    )
    assert s.telegram_hermes_execution_mode == "interactive"


def test_telegram_ingress_mode_normalized_to_webhook_for_invalid_value() -> None:
    from autoresearch.api.settings import TelegramIngressMode, TelegramSettings

    s = TelegramSettings(
        bot_token="t",
        owner_uids={"1"},
        partner_uids=set(),
        allowed_uids={"1"},
        AUTORESEARCH_TELEGRAM_INGRESS_MODE="invalid-mode",
    )
    assert s.ingress_mode == TelegramIngressMode.WEBHOOK
    assert s.active_ingress_consumer == "webhook"


def test_telegram_ingress_mode_uses_polling_consumer_only_when_enabled() -> None:
    from autoresearch.api.settings import TelegramIngressMode, TelegramSettings

    disabled = TelegramSettings(
        bot_token="t",
        owner_uids={"1"},
        partner_uids=set(),
        allowed_uids={"1"},
        AUTORESEARCH_TELEGRAM_INGRESS_MODE="polling",
        AUTORESEARCH_TELEGRAM_POLLING_ENABLED=False,
    )
    enabled = TelegramSettings(
        bot_token="t",
        owner_uids={"1"},
        partner_uids=set(),
        allowed_uids={"1"},
        AUTORESEARCH_TELEGRAM_INGRESS_MODE="polling",
        AUTORESEARCH_TELEGRAM_POLLING_ENABLED=True,
    )
    assert disabled.ingress_mode == TelegramIngressMode.POLLING
    assert disabled.active_ingress_consumer == "webhook"
    assert enabled.active_ingress_consumer == "polling"


def test_dispatch_hermes_invokes_live_progress_while_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        WorkerRuntimeDispatchService,
        "_RUNTIME_STATUS_POLL_SECONDS",
        0.01,
    )
    claude_rt = MagicMock(spec=ClaudeRuntimeService)
    claude_rt.session_record_service = MagicMock()
    adapter = MagicMock()
    now = datetime.now(timezone.utc)
    adapter.run.return_value = RuntimeRunRead(
        runtime_id="hermes",
        run_id="run-h",
        session_id="sess-h",
        task_name="tg",
        status=JobStatus.RUNNING,
        summary="go",
        timeout_seconds=60,
        created_at=now,
        updated_at=now,
        metadata={},
    )
    clock = {"t": 0.0}

    def mono() -> float:
        clock["t"] += 0.7
        return float(clock["t"])

    monkeypatch.setattr(
        "autoresearch.core.services.worker_runtime_dispatch.time.monotonic",
        mono,
    )
    adapter.status.side_effect = [
        MagicMock(
            run=RuntimeRunRead(
                runtime_id="hermes",
                run_id="run-h",
                session_id="sess-h",
                task_name="tg",
                status=JobStatus.RUNNING,
                summary="still",
                stdout_preview="a\n",
                timeout_seconds=60,
                created_at=now,
                updated_at=now,
                metadata={},
            )
        ),
        MagicMock(
            run=RuntimeRunRead(
                runtime_id="hermes",
                run_id="run-h",
                session_id="sess-h",
                task_name="tg",
                status=JobStatus.COMPLETED,
                summary="done",
                stdout_preview="a\nb",
                timeout_seconds=60,
                created_at=now,
                updated_at=now,
                metadata={},
            )
        ),
    ]
    registry = MagicMock()
    registry.get.return_value = adapter

    ticks: list[tuple[str, int]] = []

    def live_cb(read: RuntimeRunRead, elapsed: int) -> None:
        ticks.append((read.status.value, elapsed))

    dispatch = WorkerRuntimeDispatchService(claude_runtime=claude_rt, registry=registry)
    payload: dict[str, Any] = {
        "runtime_id": "hermes",
        "prompt": "ping",
        "task_name": "tg",
        "session_key": "sk1",
        "timeout_seconds": 60,
        "metadata": {"hermes": {"session_mode": "oneshot"}},
    }
    out = dispatch.execute_payload(
        payload,
        worker_id="w1",
        queue_metadata=None,
        hermes_live_progress=live_cb,
        hermes_live_report_interval_seconds=1.0,
        hermes_live_report_on_newline=False,
    )
    assert out.status == JobStatus.COMPLETED
    assert len(ticks) >= 1


def test_dispatch_hermes_timeout_sets_terminal_timeout_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    claude_rt = MagicMock(spec=ClaudeRuntimeService)
    claude_rt.session_record_service = MagicMock()
    adapter = MagicMock()
    now = datetime.now(timezone.utc)
    adapter.run.return_value = RuntimeRunRead(
        runtime_id="hermes",
        run_id="run-timeout",
        session_id="sess-timeout",
        task_name="tg",
        status=JobStatus.RUNNING,
        summary="running",
        timeout_seconds=30,
        stdout_preview="partial",
        created_at=now,
        updated_at=now,
        metadata={},
    )
    registry = MagicMock()
    registry.get.return_value = adapter

    dispatch = WorkerRuntimeDispatchService(claude_runtime=claude_rt, registry=registry)
    monkeypatch.setattr(
        dispatch,
        "_wait_for_terminal_run",
        lambda **kwargs: (adapter.run.return_value, False),
    )
    out = dispatch.execute_payload(
        {
            "runtime_id": "hermes",
            "prompt": "ping",
            "task_name": "tg",
            "session_key": "sk-timeout",
            "timeout_seconds": 30,
        },
        worker_id="w-timeout",
        queue_metadata=None,
    )
    assert out.status == JobStatus.FAILED
    assert out.result.get("error_kind") == "terminal_timeout"
    assert out.metrics.get("exit_reason") == "terminal_timeout"
