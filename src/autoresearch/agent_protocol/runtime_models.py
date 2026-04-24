from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

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
    capabilities: list[Literal["create_session", "run", "stream", "cancel", "status"]] = Field(
        default_factory=list
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


class HermesRuntimeMetadata(StrictModel):
    provider: str | None = None
    model: str | None = None
    profile: str | None = None
    toolsets: list[str] = Field(default_factory=list)
    approval_mode: Literal["manual", "smart", "off"] | None = None
    session_mode: Literal["oneshot"] | None = None

    @field_validator("provider", "model", mode="before")
    @classmethod
    def _normalize_optional_string(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        normalized = value.strip()
        return normalized or None

    @field_validator("profile", mode="before")
    @classmethod
    def _normalize_profile_name(cls, value: Any) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("value must be a string")
        normalized = value.strip()
        if normalized.lower() == "butler":
            return "default"
        return normalized or None

    @field_validator("toolsets", mode="before")
    @classmethod
    def _normalize_toolsets(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("toolsets must be a list of strings")

        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("toolsets must be a list of strings")
            toolset = item.strip()
            if not toolset:
                continue
            lowered = toolset.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(toolset)
        return normalized


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
    stdout_preview: str | None = None
    stderr_preview: str | None = None
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
    # 0 = skip loading stream events (cheap polling for worker Hermes wait loops).
    event_limit: int = Field(default=20, ge=0, le=200)


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
