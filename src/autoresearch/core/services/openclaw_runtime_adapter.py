from __future__ import annotations

import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from autoresearch.agent_protocol.models import ArtifactRef, DriverMetrics, DriverResult, JobSpec
from autoresearch.agent_protocol.runtime_models import (
    JobBackedRuntimeBridge,
    RuntimeCancelRead,
    RuntimeCancelRequest,
    RuntimeRunRead,
    RuntimeRunRequest,
    RuntimeSessionCreateRequest,
    RuntimeSessionRead,
    RuntimeStatusRead,
    RuntimeStatusRequest,
    RuntimeStreamEvent,
    RuntimeStreamRequest,
)
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import (
    ClaudeAgentCancelRequest,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    JobStatus,
    OpenClawSessionCreateRequest,
    OpenClawSessionRead,
)


class OpenClawRuntimeAdapterService:
    """Bridge OpenClaw sessions and Claude agent runs into a runtime-style contract."""

    def __init__(
        self,
        openclaw_service: OpenClawCompatService,
        claude_service: ClaudeAgentService,
        runtime_id: str = "openclaw",
    ) -> None:
        self._openclaw_service = openclaw_service
        self._claude_service = claude_service
        self._runtime_id = runtime_id

    def create_session(self, request: RuntimeSessionCreateRequest) -> RuntimeSessionRead:
        session = self._openclaw_service.create_session(
            OpenClawSessionCreateRequest(
                channel=request.channel,
                external_id=request.external_id,
                title=request.title,
                scope=request.scope,
                session_key=request.session_key,
                assistant_id=request.assistant_id,
                actor=request.actor,
                chat_context=request.chat_context,
                metadata={
                    **request.metadata,
                    "runtime_adapter": self._runtime_id,
                },
            )
        )
        return self._map_session(session)

    def create_session_from_job(self, job: JobSpec) -> RuntimeSessionRead:
        openclaw_metadata = self._openclaw_metadata(job.metadata)
        title = self._string_value(openclaw_metadata.get("session_title")) or job.run_id
        return self.create_session(
            RuntimeSessionCreateRequest(
                runtime_id=self._runtime_id,
                channel=self._string_value(openclaw_metadata.get("channel")) or "aep",
                external_id=job.run_id,
                title=title,
                session_key=self._string_value(openclaw_metadata.get("session_key")),
                assistant_id=self._string_value(openclaw_metadata.get("assistant_id")),
                metadata={
                    "source": "openclaw_runtime_adapter",
                    "aep_run_id": job.run_id,
                    "aep_agent_id": job.agent_id,
                    "aep_mode": job.mode,
                    "input_artifact_count": len(job.input_artifacts),
                },
            )
        )

    def run(self, request: RuntimeRunRequest) -> RuntimeRunRead:
        session_id = request.session_id
        if session_id is None:
            session = self.create_session(
                RuntimeSessionCreateRequest(
                    runtime_id=self._runtime_id,
                    channel="runtime",
                    title=request.task_name,
                    metadata={
                        "source": "openclaw_runtime_adapter",
                    },
                )
            )
            session_id = session.session_id
        else:
            self._require_session(session_id)

        create_request = ClaudeAgentCreateRequest(
            task_name=request.task_name,
            prompt=request.prompt,
            session_id=session_id,
            parent_agent_id=request.parent_run_id,
            generation_depth=1,
            timeout_seconds=request.timeout_seconds,
            work_dir=request.work_dir,
            cli_args=request.cli_args,
            command_override=request.command_override,
            append_prompt=request.append_prompt,
            skill_names=request.skill_names,
            images=request.images,
            env=request.env,
            metadata={
                **request.metadata,
                "runtime_adapter": self._runtime_id,
            },
        )
        created = self._claude_service.create(create_request)
        worker = threading.Thread(
            target=self._claude_service.execute,
            args=(created.agent_run_id, create_request),
            daemon=True,
            name=f"{self._runtime_id}-run-{created.agent_run_id}",
        )
        worker.start()
        return self._map_run(created)

    def run_from_job(self, job: JobSpec, session_id: str | None = None) -> RuntimeRunRead:
        openclaw_metadata = self._openclaw_metadata(job.metadata)
        bound_session_id = session_id or self._string_value(openclaw_metadata.get("session_id"))
        request = RuntimeRunRequest(
            runtime_id=self._runtime_id,
            session_id=bound_session_id,
            task_name=self._string_value(openclaw_metadata.get("task_name")) or job.run_id,
            prompt=job.task,
            timeout_seconds=job.policy.timeout_sec,
            work_dir=self._string_value(openclaw_metadata.get("work_dir")),
            cli_args=self._string_list(openclaw_metadata.get("cli_args")),
            command_override=self._string_list_or_none(openclaw_metadata.get("command_override")),
            append_prompt=self._bool_value(openclaw_metadata.get("append_prompt"), default=True),
            skill_names=self._string_list(openclaw_metadata.get("skill_names")),
            images=self._string_list(openclaw_metadata.get("images")),
            env=self._string_mapping(openclaw_metadata.get("env")),
            metadata={
                "source": "job_spec",
                "aep_run_id": job.run_id,
                "aep_agent_id": job.agent_id,
                "aep_mode": job.mode,
                "aep_input_artifacts": [artifact.model_dump(mode="json") for artifact in job.input_artifacts],
                "aep_allowed_paths": list(job.policy.allowed_paths),
                "aep_max_changed_files": job.policy.max_changed_files,
            },
        )
        return self.run(request)

    def stream(self, request: RuntimeStreamRequest) -> list[RuntimeStreamEvent]:
        session = self._require_session(request.session_id)
        events = list(session.events)
        if request.after_event_id:
            after_index = next(
                (
                    idx
                    for idx, item in enumerate(events)
                    if str(item.get("event_id") or "") == request.after_event_id
                ),
                None,
            )
            if after_index is not None:
                events = events[after_index + 1 :]
        if request.limit and len(events) > request.limit:
            events = events[-request.limit :]

        latest_run_id = self._string_value(session.metadata.get("latest_agent_run_id"))
        return [self._map_event(session_id=session.session_id, run_id=latest_run_id, payload=event) for event in events]

    def cancel(self, request: RuntimeCancelRequest) -> RuntimeCancelRead:
        cancelled = self._claude_service.cancel(
            request.run_id,
            ClaudeAgentCancelRequest(reason=request.reason),
        )
        return RuntimeCancelRead(
            runtime_id=self._runtime_id,
            run_id=cancelled.agent_run_id,
            session_id=cancelled.session_id,
            status=cancelled.status,
            error=cancelled.error,
            metadata=dict(cancelled.metadata),
        )

    def status(self, request: RuntimeStatusRequest) -> RuntimeStatusRead:
        if request.run_id is None and request.session_id is None:
            raise ValueError("status requires run_id or session_id")

        run = self._claude_service.get(request.run_id) if request.run_id else None
        if request.run_id and run is None:
            raise KeyError(f"run not found: {request.run_id}")

        session_id = request.session_id or (run.session_id if run is not None else None)
        session = self._openclaw_service.get_session(session_id) if session_id else None
        if session_id and session is None:
            raise KeyError(f"session not found: {session_id}")

        if run is None and session is not None:
            latest_run_id = self._string_value(session.metadata.get("latest_agent_run_id"))
            if latest_run_id:
                run = self._claude_service.get(latest_run_id)

        stream_events: list[RuntimeStreamEvent] = []
        if session is not None:
            stream_events = self.stream(
                RuntimeStreamRequest(
                    runtime_id=self._runtime_id,
                    session_id=session.session_id,
                    limit=request.event_limit,
                )
            )

        artifacts = self._build_artifacts(session=session, run=run)
        mapped_run = self._map_run(run, output_artifacts=artifacts) if run is not None else None
        return RuntimeStatusRead(
            runtime_id=self._runtime_id,
            session=self._map_session(session) if session is not None else None,
            run=mapped_run,
            latest_events=stream_events,
            error=(run.error if run is not None else None) or (session.error if session is not None else None),
            metadata={
                "event_count": len(stream_events),
                "session_bound": session is not None,
                "run_bound": run is not None,
            },
        )

    def to_driver_result(self, job: JobSpec, status: RuntimeStatusRead) -> DriverResult:
        if status.run is None:
            raise ValueError("runtime status is missing run details")

        runtime_run = status.run
        if runtime_run.status is JobStatus.COMPLETED:
            driver_status = "succeeded"
            if runtime_run.changed_paths:
                recommended_action = "promote"
            else:
                recommended_action = "human_review"
        elif runtime_run.status in {JobStatus.CREATED, JobStatus.QUEUED, JobStatus.RUNNING}:
            driver_status = "partial"
            recommended_action = "human_review"
        elif runtime_run.status is JobStatus.INTERRUPTED:
            driver_status = "failed"
            recommended_action = "retry"
        else:
            driver_status = "failed"
            recommended_action = "fallback"

        return DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status=driver_status,
            summary=runtime_run.summary,
            changed_paths=list(runtime_run.changed_paths),
            output_artifacts=list(runtime_run.output_artifacts),
            metrics=runtime_run.metrics,
            recommended_action=recommended_action,
            error=runtime_run.error,
        )

    def run_job(self, job: JobSpec, session_id: str | None = None) -> JobBackedRuntimeBridge:
        session = self.create_session_from_job(job) if session_id is None else self._map_session(
            self._require_session(session_id)
        )
        runtime_run = self.run_from_job(job, session_id=session.session_id)
        runtime_status = self.status(
            RuntimeStatusRequest(runtime_id=self._runtime_id, run_id=runtime_run.run_id)
        )
        driver_result = self.to_driver_result(job, runtime_status)
        return JobBackedRuntimeBridge(
            job=job,
            session=session,
            run=runtime_run,
            status=runtime_status,
            driver_result=driver_result,
        )

    def _require_session(self, session_id: str) -> OpenClawSessionRead:
        session = self._openclaw_service.get_session(session_id)
        if session is None:
            raise KeyError(f"session not found: {session_id}")
        return session

    def _map_session(self, session: OpenClawSessionRead) -> RuntimeSessionRead:
        return RuntimeSessionRead(
            runtime_id=self._runtime_id,
            session_id=session.session_id,
            channel=session.channel,
            external_id=session.external_id,
            title=session.title,
            scope=session.scope,
            session_key=session.session_key,
            assistant_id=session.assistant_id,
            status=session.status,
            created_at=session.created_at,
            updated_at=session.updated_at,
            metadata=dict(session.metadata),
            error=session.error,
        )

    def _map_run(
        self,
        run: ClaudeAgentRunRead | None,
        output_artifacts: list[ArtifactRef] | None = None,
    ) -> RuntimeRunRead:
        if run is None:
            raise ValueError("run is required")

        changed_paths = self._string_list(run.metadata.get("changed_paths"))
        summary = (run.stdout_preview or run.stderr_preview or run.error or f"openclaw runtime {run.status.value}").strip()
        metrics = DriverMetrics(
            duration_ms=int((run.duration_seconds or 0) * 1000),
            steps=max(1, len(run.command)) if run.command else 0,
            commands=1 if run.command else 0,
        )
        return RuntimeRunRead(
            runtime_id=self._runtime_id,
            run_id=run.agent_run_id,
            session_id=run.session_id,
            task_name=run.task_name,
            status=run.status,
            summary=summary,
            changed_paths=changed_paths,
            output_artifacts=list(output_artifacts or []),
            metrics=metrics,
            command=list(run.command),
            timeout_seconds=run.timeout_seconds,
            work_dir=run.work_dir,
            returncode=run.returncode,
            created_at=run.created_at,
            updated_at=run.updated_at,
            metadata=dict(run.metadata),
            error=run.error,
        )

    def _build_artifacts(
        self,
        *,
        session: OpenClawSessionRead | None,
        run: ClaudeAgentRunRead | None,
    ) -> list[ArtifactRef]:
        artifacts: list[ArtifactRef] = []
        if run is not None:
            if run.stdout_preview:
                artifacts.append(
                    ArtifactRef(
                        name="openclaw_stdout_preview",
                        kind="log",
                        uri=f"openclaw://runs/{run.agent_run_id}/stdout-preview",
                    )
                )
            if run.stderr_preview:
                artifacts.append(
                    ArtifactRef(
                        name="openclaw_stderr_preview",
                        kind="log",
                        uri=f"openclaw://runs/{run.agent_run_id}/stderr-preview",
                    )
                )
            if run.work_dir:
                artifacts.append(
                    ArtifactRef(
                        name="openclaw_workspace",
                        kind="custom",
                        uri=Path(run.work_dir).resolve().as_uri(),
                    )
                )
        if session is not None:
            artifacts.append(
                ArtifactRef(
                    name="openclaw_session_events",
                    kind="log",
                    uri=f"openclaw://sessions/{session.session_id}/events",
                )
            )
        return artifacts

    def _map_event(
        self,
        *,
        session_id: str,
        run_id: str | None,
        payload: Mapping[str, Any],
    ) -> RuntimeStreamEvent:
        return RuntimeStreamEvent(
            runtime_id=self._runtime_id,
            session_id=session_id,
            run_id=self._string_value(payload.get("agent_run_id")) or run_id,
            event_id=self._string_value(payload.get("event_id")) or "unknown-event",
            role=self._normalize_event_role(payload.get("role")),
            content=self._string_value(payload.get("content")) or "",
            created_at=self._string_value(payload.get("created_at")) or "",
            metadata=dict(self._mapping_value(payload.get("metadata"))),
        )

    def _openclaw_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return dict(self._mapping_value(metadata.get("openclaw")))

    @staticmethod
    def _mapping_value(value: Any) -> Mapping[str, Any]:
        return value if isinstance(value, Mapping) else {}

    @staticmethod
    def _string_value(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _string_list(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        normalized: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                normalized.append(text)
        return normalized

    @classmethod
    def _string_list_or_none(cls, value: Any) -> list[str] | None:
        normalized = cls._string_list(value)
        return normalized or None

    @staticmethod
    def _string_mapping(value: Any) -> dict[str, str]:
        if not isinstance(value, Mapping):
            return {}
        normalized: dict[str, str] = {}
        for key, item in value.items():
            key_text = str(key).strip()
            value_text = str(item).strip()
            if key_text:
                normalized[key_text] = value_text
        return normalized

    @staticmethod
    def _bool_value(value: Any, *, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return default

    @staticmethod
    def _normalize_event_role(value: Any) -> str:
        role = str(value or "status").strip().lower()
        if role in {"system", "user", "assistant", "tool", "status"}:
            return role
        return "status"
