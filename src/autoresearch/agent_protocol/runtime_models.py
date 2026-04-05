from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from autoresearch.agent_protocol.models import ArtifactRef, DriverMetrics, DriverResult, JobSpec
from autoresearch.shared.models import (
    AssistantScope,
    JobStatus,
    OpenClawSessionActorRead,
    OpenClawSessionChatContextRead,
    StrictModel,
)


class RuntimeAepBridgeSpec(StrictModel):
    jobspec_inputs: list[str] = Field(default_factory=list)
    result_fields: list[str] = Field(default_factory=list)
    workspace_binding: str = ""
    artifact_bindings: list[str] = Field(default_factory=list)


class RuntimeAdapterManifest(StrictModel):
    id: str
    kind: Literal["runtime"] = "runtime"
    service: str
    version: str = "0.1"
    capabilities: list[Literal["create_session", "run", "stream", "cancel", "status"]] = (
        Field(default_factory=list)
    )
    aep_bridge: RuntimeAepBridgeSpec = Field(default_factory=RuntimeAepBridgeSpec)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeSessionCreateRequest(StrictModel):
    runtime_id: str = "openclaw"
    channel: str = "aep"
    external_id: str | None = None
    title: str = "runtime-session"
    scope: AssistantScope = AssistantScope.PERSONAL
    session_key: str | None = None
    assistant_id: str | None = None
    actor: OpenClawSessionActorRead | None = None
    chat_context: OpenClawSessionChatContextRead | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeSessionRead(StrictModel):
    runtime_id: str
    session_id: str
    channel: str
    external_id: str | None = None
    title: str
    scope: AssistantScope = AssistantScope.PERSONAL
    session_key: str | None = None
    assistant_id: str | None = None
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RuntimeRunRequest(StrictModel):
    runtime_id: str = "openclaw"
    session_id: str | None = None
    task_name: str = Field(..., min_length=1)
    prompt: str = Field(..., min_length=1)
    parent_run_id: str | None = None
    timeout_seconds: int = Field(default=900, ge=1, le=7200)
    work_dir: str | None = None
    cli_args: list[str] = Field(default_factory=list)
    command_override: list[str] | None = None
    append_prompt: bool = True
    skill_names: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeRunRead(StrictModel):
    runtime_id: str
    run_id: str
    session_id: str | None = None
    task_name: str
    status: JobStatus
    summary: str
    changed_paths: list[str] = Field(default_factory=list)
    output_artifacts: list[ArtifactRef] = Field(default_factory=list)
    metrics: DriverMetrics = Field(default_factory=DriverMetrics)
    command: list[str] = Field(default_factory=list)
    timeout_seconds: int
    work_dir: str | None = None
    returncode: int | None = None
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RuntimeStreamRequest(StrictModel):
    runtime_id: str = "openclaw"
    session_id: str
    after_event_id: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)


class RuntimeStreamEvent(StrictModel):
    runtime_id: str
    session_id: str
    run_id: str | None = None
    event_id: str
    role: Literal["system", "user", "assistant", "tool", "status"]
    content: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeCancelRequest(StrictModel):
    runtime_id: str = "openclaw"
    run_id: str = Field(..., min_length=1)
    reason: str = "cancelled by runtime adapter"


class RuntimeCancelRead(StrictModel):
    runtime_id: str
    run_id: str
    session_id: str | None = None
    status: JobStatus
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeStatusRequest(StrictModel):
    runtime_id: str = "openclaw"
    session_id: str | None = None
    run_id: str | None = None
    event_limit: int = Field(default=20, ge=1, le=200)


class RuntimeStatusRead(StrictModel):
    runtime_id: str
    session: RuntimeSessionRead | None = None
    run: RuntimeRunRead | None = None
    latest_events: list[RuntimeStreamEvent] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobBackedRuntimeBridge(StrictModel):
    job: JobSpec
    session: RuntimeSessionRead
    run: RuntimeRunRead
    status: RuntimeStatusRead
    driver_result: DriverResult
