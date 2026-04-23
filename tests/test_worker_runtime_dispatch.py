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


def test_dispatch_unknown_runtime() -> None:
    dispatch = WorkerRuntimeDispatchService(
        claude_runtime=MagicMock(spec=ClaudeRuntimeService),
        registry=MagicMock(),
    )
    out = dispatch.execute_payload({"runtime_id": "unknown", "prompt": "x"}, worker_id=None, queue_metadata=None)
    assert out.status == JobStatus.FAILED
    assert "unsupported" in (out.error or "").lower()
