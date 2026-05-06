from __future__ import annotations

from datetime import UTC, datetime
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from autoresearch.agent_protocol.models import JobSpec
from autoresearch.agent_protocol.runtime_models import (
    RuntimeCancelRead,
    RuntimeCancelRequest,
    RuntimeDoctorRead,
    RuntimeRunRead,
    RuntimeRunRequest,
    RuntimeSessionCreateRequest,
    RuntimeSessionRead,
    RuntimeStatusRead,
    RuntimeStatusRequest,
    RuntimeStreamEvent,
    RuntimeStreamRequest,
)
from autoresearch.core.services.runtime_adapter_contract import RuntimeAdapterContract
from autoresearch.executions.runner import AgentExecutionRunner
from autoresearch.shared.models import JobStatus
from autoresearch.shared.store import create_resource_id


class AepProcessRuntimeAdapterService(RuntimeAdapterContract):
    """Expose an AEP process driver as a RuntimeAdapter v1 implementation."""

    def __init__(
        self,
        *,
        repo_root: Path,
        runtime_id: str,
        agent_id: str,
        display_name: str,
        optional_dependencies: list[str] | None = None,
    ) -> None:
        self._repo_root = repo_root
        self._runtime_id = runtime_id
        self._agent_id = agent_id
        self._display_name = display_name
        self._optional_dependencies = list(optional_dependencies or [])
        self._sessions: dict[str, RuntimeSessionRead] = {}
        self._runs: dict[str, RuntimeRunRead] = {}
        self._events: dict[str, list[RuntimeStreamEvent]] = {}

    def create_session(self, request: RuntimeSessionCreateRequest) -> RuntimeSessionRead:
        now = datetime.now(UTC)
        session_id = request.session_key or create_resource_id("runtime_session")
        session = RuntimeSessionRead(
            runtime_id=self._runtime_id,
            session_id=session_id,
            channel=request.channel,
            external_id=request.external_id,
            title=request.title,
            scope=request.scope,
            session_key=request.session_key,
            assistant_id=request.assistant_id,
            status=JobStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata={
                **request.metadata,
                "runtime_adapter": self._runtime_id,
                "agent_id": self._agent_id,
            },
        )
        self._sessions[session.session_id] = session
        self._events.setdefault(session.session_id, [])
        self._append_event(session.session_id, None, "run.progress", "status", "Runtime session created.")
        return session

    def run(self, request: RuntimeRunRequest) -> RuntimeRunRead:
        session_id = request.session_id
        if not session_id:
            session = self.create_session(
                RuntimeSessionCreateRequest(
                    runtime_id=self._runtime_id,
                    channel="runtime",
                    title=request.task_name,
                    metadata={"source": "aep_process_runtime"},
                )
            )
            session_id = session.session_id
        elif session_id not in self._sessions:
            self.create_session(
                RuntimeSessionCreateRequest(
                    runtime_id=self._runtime_id,
                    channel="runtime",
                    title=request.task_name,
                    session_key=session_id,
                    metadata={"source": "aep_process_runtime"},
                )
            )

        run_id = create_resource_id("runtime_run")
        self._append_event(session_id, run_id, "run.started", "status", f"{self._display_name} started.")
        job = JobSpec(
            run_id=run_id,
            agent_id=self._agent_id,
            mode="apply_in_workspace",
            task=request.prompt,
            metadata={
                **request.metadata,
                "runtime_id": self._runtime_id,
                "runtime_session_id": session_id,
                "runtime_task_name": request.task_name,
            },
            policy={
                "timeout_sec": request.timeout_seconds,
                "allowed_paths": ["apps/**", "docs/**", "tests/**"],
                "forbidden_paths": [
                    ".git/**",
                    "logs/**",
                    ".masfactory_runtime/**",
                    "memory/**",
                    "**/*.key",
                    "**/*.pem",
                ],
                "max_changed_files": 8,
                "max_patch_lines": 2000,
            },
        )
        runner = AgentExecutionRunner(
            repo_root=self._repo_root,
            runtime_root=self._repo_root / ".masfactory_runtime",
            manifests_dir=self._repo_root / "configs" / "agents",
        )
        summary = runner.run_job(job)
        status = _runtime_status_from_final(summary.final_status)
        terminal_event = "run.succeeded" if status == JobStatus.COMPLETED else "run.failed"
        run = RuntimeRunRead(
            runtime_id=self._runtime_id,
            run_id=run_id,
            session_id=session_id,
            task_name=request.task_name,
            status=status,
            summary=summary.driver_result.summary,
            changed_paths=list(summary.driver_result.changed_paths),
            output_artifacts=list(summary.driver_result.output_artifacts),
            metrics=summary.driver_result.metrics,
            command=[self._agent_id],
            timeout_seconds=request.timeout_seconds,
            work_dir=str(self._repo_root),
            stdout_preview=summary.driver_result.summary[:2000],
            stderr_preview=None,
            returncode=0 if status == JobStatus.COMPLETED else 1,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            metadata={
                **request.metadata,
                "aep_run_id": run_id,
                "aep_agent_id": self._agent_id,
                "aep_final_status": summary.final_status,
                "validation": summary.validation.model_dump(mode="json"),
            },
            error=summary.driver_result.error,
        )
        self._runs[run_id] = run
        self._append_event(session_id, run_id, terminal_event, "status", run.summary)
        return run

    def stream(self, request: RuntimeStreamRequest) -> list[RuntimeStreamEvent]:
        events = list(self._events.get(request.session_id, []))
        if request.after_event_id:
            for idx, event in enumerate(events):
                if event.event_id == request.after_event_id:
                    events = events[idx + 1 :]
                    break
        return events[-request.limit :]

    def cancel(self, request: RuntimeCancelRequest) -> RuntimeCancelRead:
        run = self._runs.get(request.run_id)
        if run is None:
            raise KeyError(f"run not found: {request.run_id}")
        cancelled = run.model_copy(
            update={
                "status": JobStatus.CANCELLED,
                "error": request.reason,
                "updated_at": datetime.now(UTC),
            }
        )
        self._runs[request.run_id] = cancelled
        if cancelled.session_id:
            self._append_event(cancelled.session_id, request.run_id, "run.cancelled", "status", request.reason)
        return RuntimeCancelRead(
            runtime_id=self._runtime_id,
            run_id=request.run_id,
            session_id=cancelled.session_id,
            status=JobStatus.CANCELLED,
            error=request.reason,
            metadata={"source": "aep_process_runtime"},
        )

    def status(self, request: RuntimeStatusRequest) -> RuntimeStatusRead:
        run = self._runs.get(request.run_id or "") if request.run_id else None
        if request.run_id and run is None:
            raise KeyError(f"run not found: {request.run_id}")
        session = self._sessions.get(request.session_id or (run.session_id if run else "") or "")
        if request.session_id and session is None:
            raise KeyError(f"session not found: {request.session_id}")
        latest_events: list[RuntimeStreamEvent] = []
        if session is not None and request.event_limit > 0:
            latest_events = self.stream(
                RuntimeStreamRequest(
                    runtime_id=self._runtime_id,
                    session_id=session.session_id,
                    limit=request.event_limit,
                )
            )
        return RuntimeStatusRead(
            runtime_id=self._runtime_id,
            session=session,
            run=run,
            latest_events=latest_events,
            error=run.error if run is not None else None,
            metadata={"source": "aep_process_runtime"},
        )

    def doctor(self) -> RuntimeDoctorRead:
        missing = [item for item in self._optional_dependencies if find_spec(item) is None]
        manifest_path = self._repo_root / "configs" / "agents" / f"{self._agent_id}.yaml"
        if not manifest_path.exists():
            return RuntimeDoctorRead(
                runtime_id=self._runtime_id,
                status="failed",
                detail=f"AEP agent manifest not found: {manifest_path}",
                missing_dependencies=missing,
            )
        return RuntimeDoctorRead(
            runtime_id=self._runtime_id,
            status="degraded" if missing else "ok",
            detail=(
                "runtime adapter is wired; optional dependencies are missing"
                if missing
                else "runtime adapter is wired"
            ),
            missing_dependencies=missing,
            checks={"agent_id": self._agent_id, "manifest_path": str(manifest_path)},
        )

    def _append_event(
        self,
        session_id: str,
        run_id: str | None,
        event_type: str,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = RuntimeStreamEvent(
            runtime_id=self._runtime_id,
            session_id=session_id,
            run_id=run_id,
            event_id=create_resource_id("runtime_event"),
            event_type=event_type,
            role=role,  # type: ignore[arg-type]
            content=content,
            created_at=datetime.now(UTC).isoformat(),
            metadata=dict(metadata or {}),
        )
        self._events.setdefault(session_id, []).append(event)


def _runtime_status_from_final(final_status: str) -> JobStatus:
    if final_status in {"ready_for_promotion", "completed", "promoted"}:
        return JobStatus.COMPLETED
    if final_status == "human_review":
        return JobStatus.INTERRUPTED
    return JobStatus.FAILED
