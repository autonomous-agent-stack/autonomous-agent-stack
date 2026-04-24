from __future__ import annotations

import sys

import pytest

from autoresearch.agent_protocol.runtime_models import HermesRuntimeMetadata, RuntimeRunRequest
from autoresearch.core.services.hermes_command_builder import build_hermes_command_plan
from autoresearch.core.services.hermes_runtime_contract import reject_unsupported_cli_args
from autoresearch.core.services.hermes_runtime_errors import HermesRuntimeErrorKind, HermesRuntimeFailure


def test_build_hermes_command_plan_maps_structured_fields(monkeypatch) -> None:
    monkeypatch.setenv("AUTORESEARCH_HERMES_COMMAND", f"{sys.executable} /tmp/hermes_stub.py")
    request = RuntimeRunRequest(
        task_name="builder",
        prompt="Summarize this task for Hermes.",
        work_dir="/tmp/work",
        timeout_seconds=12,
        cli_args=["--model", "escape-hatch-model"],
        env={"FOO": "bar"},
    )
    hermes_meta = HermesRuntimeMetadata(
        provider="anthropic",
        profile="local-profile",
        toolsets=["shell", "git"],
        approval_mode="smart",
        session_mode="oneshot",
    )

    plan = build_hermes_command_plan(request, hermes_meta)

    assert plan.argv == [
        sys.executable,
        "/tmp/hermes_stub.py",
        "--profile",
        "local-profile",
        "chat",
        "-Q",
        "-q",
        "Summarize this task for Hermes.",
        "--provider",
        "anthropic",
        "--toolsets",
        "shell,git",
        "--model",
        "escape-hatch-model",
    ]
    assert plan.cwd == "/tmp/work"
    assert plan.env == {"FOO": "bar"}
    assert plan.timeout_seconds == 12
    assert plan.summary_inputs == {
        "prompt_head": "Summarize this task for Hermes.",
        "profile": "local-profile",
        "provider": "anthropic",
        "model": None,
        "timeout_seconds": 12,
    }
    assert plan.to_command_projection() == {
        "argv": plan.argv,
        "cwd": "/tmp/work",
        "timeout_seconds": 12,
        "mapped_fields": ["profile", "provider", "toolsets"],
        "unmapped_fields": ["approval_mode", "session_mode"],
        "blocked_cli_args": [],
    }


def test_reject_unsupported_cli_args_blocks_yolo() -> None:
    with pytest.raises(ValueError, match="does not support cli_args: --yolo"):
        reject_unsupported_cli_args(["--yolo"])


def test_build_hermes_command_plan_remaps_legacy_butler_in_cli_args(monkeypatch) -> None:
    monkeypatch.setenv("AUTORESEARCH_HERMES_COMMAND", f"{sys.executable} /tmp/hermes_stub.py")
    request = RuntimeRunRequest(
        task_name="t",
        prompt="hi",
        work_dir="/tmp/w",
        timeout_seconds=30,
        cli_args=["--profile", "butler", "--verbose"],
    )
    meta = HermesRuntimeMetadata(session_mode="oneshot")
    plan = build_hermes_command_plan(request, meta)
    assert plan.argv[-3:] == ["--profile", "default", "--verbose"]
    assert "butler" not in plan.argv


def test_build_hermes_command_plan_removes_legacy_butler_from_base_command(monkeypatch) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_HERMES_COMMAND",
        f"{sys.executable} /tmp/hermes_stub.py --profile butler",
    )
    request = RuntimeRunRequest(task_name="t", prompt="hi", work_dir="/tmp/w", timeout_seconds=30)
    meta = HermesRuntimeMetadata(session_mode="oneshot")
    plan = build_hermes_command_plan(request, meta)
    assert "--profile" in plan.argv
    idx = plan.argv.index("--profile")
    assert plan.argv[idx + 1] == "default"


def test_build_hermes_command_plan_raises_on_unparseable_command(monkeypatch) -> None:
    monkeypatch.setenv("AUTORESEARCH_HERMES_COMMAND", "'")
    request = RuntimeRunRequest(task_name="builder-fail", prompt="hello")
    hermes_meta = HermesRuntimeMetadata(session_mode="oneshot")

    with pytest.raises(HermesRuntimeFailure) as excinfo:
        build_hermes_command_plan(request, hermes_meta)

    assert excinfo.value.kind is HermesRuntimeErrorKind.COMMAND_BUILD_FAILED
    assert excinfo.value.failed_stage == "command_build"
