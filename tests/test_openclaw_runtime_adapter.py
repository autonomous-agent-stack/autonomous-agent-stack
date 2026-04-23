from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from autoresearch.agent_protocol.models import JobSpec
from autoresearch.agent_protocol.runtime_registry import RuntimeAdapterRegistry
from autoresearch.agent_protocol.runtime_models import (
    RuntimeCancelRequest,
    RuntimeRunRequest,
    RuntimeSessionCreateRequest,
    RuntimeStatusRequest,
    RuntimeStreamRequest,
)
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.hermes_runtime_adapter import HermesRuntimeAdapterService
from autoresearch.core.services.hermes_runtime_errors import HermesRuntimeErrorKind
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_runtime_adapter import OpenClawRuntimeAdapterService
from autoresearch.shared.models import ClaudeAgentRunRead, JobStatus, OpenClawSessionRead
from autoresearch.shared.store import SQLiteModelRepository


def _hermes_stub_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "hermes_sleep_stub.py"


def _configure_hermes_stub(monkeypatch, **env: str) -> Path:
    stub_path = _hermes_stub_path()
    monkeypatch.setenv("AUTORESEARCH_HERMES_COMMAND", f"{sys.executable} {stub_path}")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return stub_path


def _build_runtime_adapter(tmp_path: Path) -> OpenClawRuntimeAdapterService:
    db_path = tmp_path / "openclaw-runtime.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_runtime_adapter_it",
            model_cls=OpenClawSessionRead,
        )
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_runtime_adapter_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        repo_root=tmp_path,
        max_agents=10,
        max_depth=3,
    )
    return OpenClawRuntimeAdapterService(
        openclaw_service=openclaw_service,
        claude_service=claude_service,
    )


def _build_hermes_runtime_adapter(tmp_path: Path) -> HermesRuntimeAdapterService:
    db_path = tmp_path / "hermes-runtime.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_hermes_runtime_it",
            model_cls=OpenClawSessionRead,
        )
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_hermes_runtime_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        repo_root=tmp_path,
        max_agents=10,
        max_depth=3,
    )
    return HermesRuntimeAdapterService(
        openclaw_service=openclaw_service,
        claude_service=claude_service,
    )


def _wait_runtime_terminal(
    service: OpenClawRuntimeAdapterService,
    run_id: str,
    *,
    attempts: int = 40,
) -> tuple[object | None, object | None]:
    latest_status = None
    for _ in range(attempts):
        latest_status = service.status(RuntimeStatusRequest(run_id=run_id, event_limit=50))
        if latest_status.run is not None and latest_status.run.status in {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.INTERRUPTED,
            JobStatus.CANCELLED,
        }:
            return latest_status, latest_status.run
        time.sleep(0.05)
    return latest_status, latest_status.run if latest_status is not None else None


def test_runtime_registry_loads_openclaw_manifest() -> None:
    registry = RuntimeAdapterRegistry(Path("configs/runtime_agents"))
    manifest = registry.load("openclaw")

    assert manifest.id == "openclaw"
    assert manifest.kind == "runtime"
    assert manifest.service.endswith(":OpenClawRuntimeAdapterService")
    assert manifest.capabilities == ["create_session", "run", "stream", "cancel", "status"]
    assert "policy.timeout_sec" in manifest.aep_bridge.jobspec_inputs


def test_runtime_registry_loads_hermes_manifest() -> None:
    registry = RuntimeAdapterRegistry(Path("configs/runtime_agents"))
    manifest = registry.load("hermes")

    assert manifest.id == "hermes"
    assert manifest.kind == "runtime"
    assert manifest.version == "1.0"
    assert manifest.service.endswith(":HermesRuntimeAdapterService")
    assert manifest.capabilities == ["create_session", "run", "stream", "cancel", "status"]
    assert "metadata.hermes" in manifest.aep_bridge.jobspec_inputs
    assert manifest.aep_bridge.result_fields[:5] == [
        "status",
        "summary",
        "stdout_preview",
        "stderr_preview",
        "returncode",
    ]


def test_openclaw_runtime_adapter_runs_job_and_maps_aep_bridge(tmp_path: Path) -> None:
    adapter = _build_runtime_adapter(tmp_path)
    work_dir = tmp_path / "workspace"
    work_dir.mkdir(parents=True, exist_ok=True)

    job = JobSpec(
        run_id="aep-openclaw-runtime-1",
        agent_id="openclaw",
        role="executor",
        mode="apply_in_workspace",
        task="Create src/runtime_note.txt with hello.",
        metadata={
            "openclaw": {
                "task_name": "runtime-smoke",
                "work_dir": str(work_dir),
                "command_override": [
                    sys.executable,
                    "-c",
                    (
                        "from pathlib import Path; "
                        "Path('src').mkdir(exist_ok=True); "
                        "Path('src/runtime_note.txt').write_text('hello\\n', encoding='utf-8'); "
                        "print('runtime-ok')"
                    ),
                ],
                "append_prompt": False,
            }
        },
    )

    session = adapter.create_session_from_job(job)
    runtime_run = adapter.run_from_job(job, session_id=session.session_id)
    runtime_status, finalized_run = _wait_runtime_terminal(adapter, runtime_run.run_id)

    assert runtime_status is not None
    assert finalized_run is not None
    assert finalized_run.status == JobStatus.COMPLETED
    assert "runtime-ok" in finalized_run.summary
    assert finalized_run.stdout_preview == "runtime-ok"
    assert finalized_run.stderr_preview is None
    assert (work_dir / "src" / "runtime_note.txt").read_text(encoding="utf-8") == "hello\n"

    stream = adapter.stream(RuntimeStreamRequest(session_id=session.session_id, limit=50))
    assert any("agent queued" in event.content for event in stream)
    assert any("agent completed" in event.content for event in stream)

    driver_result = adapter.to_driver_result(job, runtime_status)
    assert driver_result.run_id == job.run_id
    assert driver_result.agent_id == "openclaw"
    assert driver_result.status == "succeeded"
    assert driver_result.recommended_action == "human_review"
    assert any(artifact.name == "openclaw_session_events" for artifact in driver_result.output_artifacts)
    assert any(artifact.name == "openclaw_workspace" for artifact in driver_result.output_artifacts)


def test_openclaw_runtime_adapter_cancel_interrupts_run(tmp_path: Path) -> None:
    adapter = _build_runtime_adapter(tmp_path)
    session = adapter.create_session(
        RuntimeSessionCreateRequest(
            title="runtime-cancel",
            metadata={"source": "test"},
        )
    )
    runtime_run = adapter.run(
        RuntimeRunRequest(
            session_id=session.session_id,
            task_name="runtime-cancel",
            prompt="cancel this run",
            timeout_seconds=20,
            command_override=[
                sys.executable,
                "-c",
                "import time; time.sleep(3); print('late-output')",
            ],
            append_prompt=False,
        )
    )
    time.sleep(0.1)

    cancelled = adapter.cancel(
        RuntimeCancelRequest(
            run_id=runtime_run.run_id,
            reason="stop-now",
        )
    )
    assert cancelled.status == JobStatus.CANCELLED

    runtime_status, finalized_run = _wait_runtime_terminal(adapter, runtime_run.run_id, attempts=60)
    assert runtime_status is not None
    assert finalized_run is not None
    assert finalized_run.status == JobStatus.CANCELLED
    assert finalized_run.error == "stop-now"
    assert any("agent cancelled" in event.content for event in runtime_status.latest_events)
    driver_result = adapter.to_driver_result(
        JobSpec(run_id="cancel-run", agent_id="openclaw", task="cancel", role="executor"),
        runtime_status,
    )
    assert driver_result.recommended_action == "retry"


def test_hermes_runtime_adapter_uses_real_cli_contract_with_hermes_namespace(
    tmp_path: Path,
    monkeypatch,
) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)
    work_dir = tmp_path / "hermes-workspace"
    work_dir.mkdir(parents=True, exist_ok=True)
    hermes_stub = _configure_hermes_stub(monkeypatch)
    job = JobSpec(
        run_id="aep-hermes-runtime-1",
        agent_id="hermes",
        role="executor",
        mode="runtime_only",
        task="Write hermes runtime marker.",
        metadata={
            "hermes": {
                "task_name": "hermes-runtime-smoke",
                "work_dir": str(work_dir),
                "cli_args": ["--model", "local-small"],
                "profile": " local-profile ",
                "toolsets": ["shell", "shell", "git", " "],
                "session_mode": "oneshot",
            }
        },
    )

    session = adapter.create_session_from_job(job)
    runtime_run = adapter.run_from_job(job, session_id=session.session_id)
    runtime_status, finalized_run = _wait_runtime_terminal(adapter, runtime_run.run_id)

    assert runtime_status is not None
    assert finalized_run is not None
    assert runtime_status.run is not None
    assert runtime_status.run.runtime_id == "hermes"
    assert finalized_run.status == JobStatus.COMPLETED
    assert finalized_run.stdout_preview is not None
    assert finalized_run.stderr_preview is None
    assert runtime_status.run.command == [
        sys.executable,
        str(hermes_stub),
        "--profile",
        "local-profile",
        "chat",
        "-Q",
        "-q",
        "Write hermes runtime marker.",
        "--toolsets",
        "shell,git",
        "--model",
        "local-small",
    ]
    assert finalized_run.summary.startswith("Hermes completed:")
    hermes_metadata = runtime_status.run.metadata["hermes"]
    assert hermes_metadata["requested"] == {
        "profile": "local-profile",
        "toolsets": ["shell", "git"],
        "session_mode": "oneshot",
    }
    assert hermes_metadata["effective"] == {
        "provider": None,
        "model": None,
        "profile": "local-profile",
        "toolsets": ["shell", "git"],
        "approval_mode": None,
        "session_mode": "oneshot",
    }
    assert hermes_metadata["command_projection"] == {
        "argv": [
            sys.executable,
            str(hermes_stub),
            "--profile",
            "local-profile",
            "chat",
            "-Q",
            "-q",
            "Write hermes runtime marker.",
            "--toolsets",
            "shell,git",
            "--model",
            "local-small",
        ],
        "cwd": str(work_dir),
        "timeout_seconds": 900,
        "mapped_fields": ["profile", "toolsets"],
        "unmapped_fields": ["session_mode"],
        "blocked_cli_args": [],
    }
    assert hermes_metadata["safety_flags"]["cli_args_escape_hatch_used"] is True
    assert (work_dir / "notes" / "hermes.txt").read_text(encoding="utf-8") == "hermes\n"
    assert any(artifact.name == "hermes_session_events" for artifact in runtime_status.run.output_artifacts)
    assert any(artifact.name == "hermes_workspace" for artifact in runtime_status.run.output_artifacts)


def test_hermes_runtime_adapter_fails_preflight_without_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)
    work_dir = tmp_path / "hermes-missing-workspace"
    work_dir.mkdir(parents=True, exist_ok=True)
    missing_command = "definitely-missing-hermes-binary"
    monkeypatch.setenv("AUTORESEARCH_HERMES_COMMAND", missing_command)

    runtime_run = adapter.run(
        RuntimeRunRequest(
            task_name="hermes-missing",
            prompt="hello from hermes",
            work_dir=str(work_dir),
        )
    )

    assert runtime_run.runtime_id == "hermes"
    assert runtime_run.status == JobStatus.FAILED
    assert runtime_run.stdout_preview is None
    assert runtime_run.stderr_preview == f"Hermes executable not found in PATH: {missing_command}"
    assert runtime_run.returncode == -1
    assert runtime_run.command == [missing_command, "chat", "-Q", "-q", "hello from hermes"]
    assert runtime_run.error == f"Hermes executable not found in PATH: {missing_command}"
    assert runtime_run.summary == "Hermes executable is unavailable."
    assert runtime_run.metadata["error_kind"] == HermesRuntimeErrorKind.BINARY_MISSING.value
    assert runtime_run.metadata["failed_stage"] == "preflight"
    assert any(artifact.name == "hermes_session_events" for artifact in runtime_run.output_artifacts)
    assert any(artifact.name == "hermes_stderr_preview" for artifact in runtime_run.output_artifacts)
    assert any(artifact.name == "hermes_workspace" for artifact in runtime_run.output_artifacts)

    runtime_status = adapter.status(RuntimeStatusRequest(run_id=runtime_run.run_id, event_limit=50))
    assert runtime_status.run is not None
    assert runtime_status.run.status == JobStatus.FAILED
    assert runtime_status.run.metadata.get("preflight_failed") is True
    assert runtime_status.run.metadata["error_kind"] == HermesRuntimeErrorKind.BINARY_MISSING.value
    assert any("agent failed" in event.content for event in runtime_status.latest_events)
    assert not (work_dir / "notes" / "hermes.txt").exists()


@pytest.mark.parametrize(
    ("field_name", "field_value"),
    [
        ("images", ["proof.png"]),
        ("skill_names", ["shell"]),
        ("command_override", [sys.executable, "-c", "print('override')"]),
    ],
)
def test_hermes_runtime_adapter_rejects_unsupported_request_fields(
    tmp_path: Path,
    field_name: str,
    field_value: object,
) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)
    request = RuntimeRunRequest(
        task_name="hermes-unsupported",
        prompt="hello from hermes",
    ).model_copy(update={field_name: field_value})

    with pytest.raises(ValueError, match=f"Hermes runtime v1 does not support: {field_name}"):
        adapter.run(request)


def test_hermes_runtime_adapter_rejects_invalid_structured_metadata(tmp_path: Path) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)

    with pytest.raises(ValueError, match="invalid metadata.hermes"):
        adapter.run(
            RuntimeRunRequest(
                task_name="hermes-invalid-metadata",
                prompt="hello from hermes",
                metadata={
                    "hermes": {
                        "approval_mode": "always_yes",
                    }
                },
            )
        )


def test_hermes_runtime_adapter_rejects_blocked_cli_args(tmp_path: Path) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)

    with pytest.raises(ValueError, match="does not support cli_args: --yolo"):
        adapter.run(
            RuntimeRunRequest(
                task_name="hermes-yolo",
                prompt="hello from hermes",
                cli_args=["--yolo"],
            )
        )


def test_hermes_runtime_adapter_rejects_approval_mode_off(tmp_path: Path) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)

    with pytest.raises(ValueError, match="approval_mode=off"):
        adapter.run(
            RuntimeRunRequest(
                task_name="hermes-off",
                prompt="hello from hermes",
                metadata={"hermes": {"approval_mode": "off"}},
            )
        )


def test_hermes_runtime_adapter_marks_command_build_failed(tmp_path: Path, monkeypatch) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)
    monkeypatch.setenv("AUTORESEARCH_HERMES_COMMAND", "'")

    runtime_run = adapter.run(
        RuntimeRunRequest(
            task_name="hermes-build-failed",
            prompt="hello from hermes",
        )
    )

    assert runtime_run.status == JobStatus.FAILED
    assert runtime_run.metadata["error_kind"] == HermesRuntimeErrorKind.COMMAND_BUILD_FAILED.value
    assert runtime_run.metadata["failed_stage"] == "command_build"
    assert runtime_run.summary == "Hermes command construction failed."


def test_hermes_runtime_adapter_marks_nonzero_exit(tmp_path: Path, monkeypatch) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)
    work_dir = tmp_path / "hermes-nonzero"
    work_dir.mkdir(parents=True, exist_ok=True)
    _configure_hermes_stub(
        monkeypatch,
        HERMES_STUB_MODE="nonzero",
        HERMES_STUB_EXIT_CODE="2",
    )

    runtime_run = adapter.run(
        RuntimeRunRequest(
            task_name="hermes-nonzero",
            prompt="hello from hermes",
            work_dir=str(work_dir),
        )
    )
    runtime_status, finalized_run = _wait_runtime_terminal(adapter, runtime_run.run_id)

    assert runtime_status is not None
    assert finalized_run is not None
    assert finalized_run.status == JobStatus.FAILED
    assert finalized_run.returncode == 2
    assert finalized_run.metadata["error_kind"] == HermesRuntimeErrorKind.NONZERO_EXIT.value
    assert finalized_run.summary == "Hermes exited with code 2."


def test_hermes_runtime_adapter_marks_timeout(tmp_path: Path, monkeypatch) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)
    work_dir = tmp_path / "hermes-timeout"
    work_dir.mkdir(parents=True, exist_ok=True)
    _configure_hermes_stub(
        monkeypatch,
        HERMES_STUB_SLEEP_SECONDS="2",
    )

    runtime_run = adapter.run(
        RuntimeRunRequest(
            task_name="hermes-timeout",
            prompt="hello from hermes",
            work_dir=str(work_dir),
            timeout_seconds=1,
        )
    )
    runtime_status, finalized_run = _wait_runtime_terminal(adapter, runtime_run.run_id, attempts=80)

    assert runtime_status is not None
    assert finalized_run is not None
    assert finalized_run.status == JobStatus.FAILED
    assert finalized_run.returncode == -1
    assert finalized_run.metadata["error_kind"] == HermesRuntimeErrorKind.TIMEOUT.value
    assert finalized_run.summary == "Hermes timed out after 1s."


def test_hermes_runtime_adapter_marks_launch_failed(tmp_path: Path, monkeypatch) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)
    work_dir = tmp_path / "hermes-launch"
    work_dir.mkdir(parents=True, exist_ok=True)
    _configure_hermes_stub(monkeypatch)

    def _boom(*args, **kwargs):
        raise PermissionError("launch denied")

    monkeypatch.setattr("autoresearch.core.services.claude_agents.subprocess.Popen", _boom)
    runtime_run = adapter.run(
        RuntimeRunRequest(
            task_name="hermes-launch",
            prompt="hello from hermes",
            work_dir=str(work_dir),
        )
    )
    runtime_status, finalized_run = _wait_runtime_terminal(adapter, runtime_run.run_id, attempts=80)

    assert runtime_status is not None
    assert finalized_run is not None
    assert finalized_run.status == JobStatus.FAILED
    assert finalized_run.metadata["error_kind"] == HermesRuntimeErrorKind.LAUNCH_FAILED.value
    assert finalized_run.summary == "Hermes failed to launch."


def test_hermes_runtime_adapter_marks_internal_error(tmp_path: Path, monkeypatch) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)
    work_dir = tmp_path / "hermes-internal"
    work_dir.mkdir(parents=True, exist_ok=True)
    _configure_hermes_stub(monkeypatch)

    class _BrokenProcess:
        returncode = 0

        def communicate(self, timeout=None):  # noqa: ANN001
            raise RuntimeError("broken-process")

        def terminate(self) -> None:
            return None

        def wait(self, timeout=None):  # noqa: ANN001
            return 0

        def kill(self) -> None:
            return None

    monkeypatch.setattr(
        "autoresearch.core.services.claude_agents.subprocess.Popen",
        lambda *args, **kwargs: _BrokenProcess(),
    )
    runtime_run = adapter.run(
        RuntimeRunRequest(
            task_name="hermes-internal",
            prompt="hello from hermes",
            work_dir=str(work_dir),
        )
    )
    runtime_status, finalized_run = _wait_runtime_terminal(adapter, runtime_run.run_id, attempts=80)

    assert runtime_status is not None
    assert finalized_run is not None
    assert finalized_run.status == JobStatus.FAILED
    assert finalized_run.metadata["error_kind"] == HermesRuntimeErrorKind.INTERNAL_ERROR.value
    assert finalized_run.summary == "Hermes runtime failed with an internal error."


def test_hermes_runtime_adapter_cancel_preserves_partial_output(tmp_path: Path, monkeypatch) -> None:
    adapter = _build_hermes_runtime_adapter(tmp_path)
    work_dir = tmp_path / "hermes-cancel"
    work_dir.mkdir(parents=True, exist_ok=True)
    _configure_hermes_stub(
        monkeypatch,
        HERMES_STUB_SLEEP_SECONDS="3",
    )

    runtime_run = adapter.run(
        RuntimeRunRequest(
            task_name="hermes-cancel",
            prompt="cancel hermes",
            work_dir=str(work_dir),
            timeout_seconds=20,
        )
    )
    time.sleep(0.1)

    cancelled = adapter.cancel(RuntimeCancelRequest(run_id=runtime_run.run_id, reason="stop-hermes"))
    runtime_status, finalized_run = _wait_runtime_terminal(adapter, runtime_run.run_id, attempts=80)

    assert cancelled.status == JobStatus.CANCELLED
    assert runtime_status is not None
    assert finalized_run is not None
    assert finalized_run.status == JobStatus.CANCELLED
    assert finalized_run.metadata["error_kind"] == HermesRuntimeErrorKind.CANCELLED.value
    assert finalized_run.stdout_preview is not None
    assert "argv" in finalized_run.stdout_preview
    assert any("agent cancelled" in event.content for event in runtime_status.latest_events)
    repeated = adapter.cancel(RuntimeCancelRequest(run_id=runtime_run.run_id, reason="stop-hermes"))
    assert repeated.status == JobStatus.CANCELLED
