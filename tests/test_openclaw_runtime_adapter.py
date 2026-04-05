from __future__ import annotations

import sys
import time
from pathlib import Path

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
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_runtime_adapter import OpenClawRuntimeAdapterService
from autoresearch.shared.models import ClaudeAgentRunRead, JobStatus, OpenClawSessionRead
from autoresearch.shared.store import SQLiteModelRepository


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
    assert cancelled.status == JobStatus.INTERRUPTED

    runtime_status, finalized_run = _wait_runtime_terminal(adapter, runtime_run.run_id, attempts=60)
    assert runtime_status is not None
    assert finalized_run is not None
    assert finalized_run.status == JobStatus.INTERRUPTED
    assert finalized_run.error == "stop-now"
    assert any("agent cancelled" in event.content for event in runtime_status.latest_events)
