from __future__ import annotations

import os
from dataclasses import dataclass

from autoresearch.control_plane.contracts import ControlPlaneCapabilityRead, ControlPlaneTaskRead
from autoresearch.shared.models import WorkerQueueItemCreateRequest, WorkerTaskType


@dataclass(frozen=True)
class CapabilityDispatch:
    worker_request: WorkerQueueItemCreateRequest | None = None
    immediate_result: dict[str, object] | None = None


class CapabilityAdapter:
    descriptor: ControlPlaneCapabilityRead

    def dispatch(self, task: ControlPlaneTaskRead) -> CapabilityDispatch:
        return CapabilityDispatch(worker_request=self.build_worker_request(task))

    def build_worker_request(self, task: ControlPlaneTaskRead) -> WorkerQueueItemCreateRequest:
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.NOOP,
            payload={
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "parameters": task.parameters,
                "intent": task.intent,
            },
            requested_by=task.requested_by,
            priority=0,
            metadata={
                "aas_session_id": task.session_id,
                "control_plane_task_id": task.task_id,
                "capability_id": task.capability_id,
                "control_plane_v2": True,
            },
        )


class EchoCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="echo",
        name="Echo deterministic runner",
        type="local",
        enabled=True,
        dispatch_mode="worker_queue",
        description="Local smoke capability represented as a worker-queue NOOP task.",
        risk_tags=[],
        requires_approval=False,
        external_calls_enabled=False,
        metadata={"worker_task_type": WorkerTaskType.NOOP.value},
    )


class WorkerQueueCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="worker_queue",
        name="Generic worker queue",
        type="worker",
        enabled=True,
        dispatch_mode="worker_queue",
        description="Dispatches a generic task onto the existing worker claim/report backbone.",
        risk_tags=[],
        requires_approval=False,
        external_calls_enabled=False,
        metadata={"worker_task_type": WorkerTaskType.NOOP.value},
    )


class GitHubAssistantCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="github_assistant",
        name="GitHub assistant",
        type="github",
        enabled=True,
        dispatch_mode="worker_queue",
        description="Routes GitHub assistant intent through the existing GitHub worker task type.",
        risk_tags=["external_api"],
        requires_approval=True,
        external_calls_enabled=True,
        metadata={"worker_task_type": WorkerTaskType.GITHUB_OPS.value},
    )

    def build_worker_request(self, task: ControlPlaneTaskRead) -> WorkerQueueItemCreateRequest:
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.GITHUB_OPS,
            payload={
                **task.parameters,
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
            },
            requested_by=task.requested_by,
            priority=task.metadata.get("priority", 8),
            metadata={
                "aas_session_id": task.session_id,
                "control_plane_task_id": task.task_id,
                "capability_id": task.capability_id,
                "control_plane_v2": True,
            },
        )


class ExcelAuditCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="excel_audit",
        name="Excel audit and commission",
        type="excel",
        enabled=True,
        dispatch_mode="worker_queue",
        description="Routes spreadsheet audit and commission work through the Excel audit worker.",
        risk_tags=[],
        requires_approval=False,
        external_calls_enabled=False,
        metadata={"worker_task_type": WorkerTaskType.EXCEL_AUDIT.value},
    )

    def build_worker_request(self, task: ControlPlaneTaskRead) -> WorkerQueueItemCreateRequest:
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.EXCEL_AUDIT,
            payload={
                **task.parameters,
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "task_brief": task.intent or task.name,
            },
            requested_by=task.requested_by,
            priority=_priority_from_task(task, default=3),
            metadata={
                "aas_session_id": task.session_id,
                "control_plane_task_id": task.task_id,
                "capability_id": task.capability_id,
                "control_plane_v2": True,
            },
        )


class YouTubeAutoflowCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="youtube_autoflow",
        name="YouTube autoflow",
        type="youtube",
        enabled=True,
        dispatch_mode="worker_queue",
        description="Routes YouTube transcript and digest requests through the YouTube autoflow worker.",
        risk_tags=["external_api"],
        requires_approval=True,
        external_calls_enabled=True,
        metadata={"worker_task_type": WorkerTaskType.YOUTUBE_AUTOFLOW.value},
    )

    def build_worker_request(self, task: ControlPlaneTaskRead) -> WorkerQueueItemCreateRequest:
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.YOUTUBE_AUTOFLOW,
            payload={
                **task.parameters,
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "request_text": task.intent or task.name,
            },
            requested_by=task.requested_by,
            priority=_priority_from_task(task, default=5),
            metadata={
                "aas_session_id": task.session_id,
                "control_plane_task_id": task.task_id,
                "capability_id": task.capability_id,
                "control_plane_v2": True,
            },
        )


class ContentKBCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="content_kb",
        name="Content knowledge base",
        type="content_kb",
        enabled=True,
        dispatch_mode="worker_queue",
        description="Routes content ingestion, bookmark organization, and knowledge-base updates.",
        risk_tags=["filesystem_write"],
        requires_approval=True,
        external_calls_enabled=False,
        metadata={"worker_task_type": WorkerTaskType.CONTENT_KB_INGEST.value},
    )

    def build_worker_request(self, task: ControlPlaneTaskRead) -> WorkerQueueItemCreateRequest:
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={
                **task.parameters,
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "request_text": task.intent or task.name,
            },
            requested_by=task.requested_by,
            priority=_priority_from_task(task, default=4),
            metadata={
                "aas_session_id": task.session_id,
                "control_plane_task_id": task.task_id,
                "capability_id": task.capability_id,
                "control_plane_v2": True,
            },
        )


class HermesOpenClawCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="hermes_openclaw",
        name="Hermes/OpenClaw runtime",
        type="runtime",
        enabled=True,
        dispatch_mode="worker_queue",
        description="Routes runtime prompts through the existing Claude/Hermes worker task type.",
        risk_tags=[],
        requires_approval=False,
        external_calls_enabled=False,
        metadata={"worker_task_type": WorkerTaskType.CLAUDE_RUNTIME.value},
    )

    def build_worker_request(self, task: ControlPlaneTaskRead) -> WorkerQueueItemCreateRequest:
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.CLAUDE_RUNTIME,
            payload={
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "prompt": task.intent or task.name,
                "parameters": task.parameters,
            },
            requested_by=task.requested_by,
            priority=task.metadata.get("priority", 5),
            metadata={
                "aas_session_id": task.session_id,
                "control_plane_task_id": task.task_id,
                "capability_id": task.capability_id,
                "control_plane_v2": True,
            },
        )


class BoundaryCapabilityAdapter(CapabilityAdapter):
    def __init__(self, *, capability_id: str, name: str, protocol_type: str, env_prefix: str) -> None:
        enabled = os.getenv(f"{env_prefix}_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
        endpoint = os.getenv(f"{env_prefix}_ENDPOINT", "").strip()
        self.descriptor = ControlPlaneCapabilityRead(
            capability_id=capability_id,
            name=name,
            type=protocol_type,
            enabled=enabled and bool(endpoint),
            dispatch_mode="external_boundary",
            description=f"{name} protocol boundary. External calls are disabled unless explicitly configured.",
            risk_tags=["external_api"],
            requires_approval=True,
            external_calls_enabled=enabled and bool(endpoint),
            metadata={"endpoint_configured": bool(endpoint)},
        )

    def dispatch(self, task: ControlPlaneTaskRead) -> CapabilityDispatch:
        if not self.descriptor.enabled:
            return CapabilityDispatch(
                immediate_result={
                    "status": "disabled",
                    "capability_id": self.descriptor.capability_id,
                    "reason": "Protocol boundary is configured but external calls are disabled.",
                    "task_id": task.task_id,
                }
            )
        return super().dispatch(task)


class FutureCapabilityAdapter(CapabilityAdapter):
    def __init__(self) -> None:
        self.descriptor = ControlPlaneCapabilityRead(
            capability_id="adk_workflow",
            name="ADK workflow agent",
            type="adk",
            enabled=False,
            dispatch_mode="future",
            description="Future ADK workflow boundary; not a scheduler in v2 core.",
            risk_tags=["external_api"],
            requires_approval=True,
            external_calls_enabled=False,
        )

    def dispatch(self, task: ControlPlaneTaskRead) -> CapabilityDispatch:
        return CapabilityDispatch(
            immediate_result={
                "status": "disabled",
                "capability_id": self.descriptor.capability_id,
                "reason": "ADK workflow support is reserved for a later adapter.",
                "task_id": task.task_id,
            }
        )


class ControlPlaneCapabilityRegistry:
    def __init__(self, adapters: list[CapabilityAdapter] | None = None) -> None:
        configured = adapters or [
            EchoCapabilityAdapter(),
            WorkerQueueCapabilityAdapter(),
            GitHubAssistantCapabilityAdapter(),
            ExcelAuditCapabilityAdapter(),
            YouTubeAutoflowCapabilityAdapter(),
            ContentKBCapabilityAdapter(),
            HermesOpenClawCapabilityAdapter(),
            BoundaryCapabilityAdapter(
                capability_id="mcp",
                name="MCP tool boundary",
                protocol_type="mcp",
                env_prefix="AUTORESEARCH_MCP",
            ),
            BoundaryCapabilityAdapter(
                capability_id="a2a",
                name="A2A remote agent boundary",
                protocol_type="a2a",
                env_prefix="AUTORESEARCH_A2A",
            ),
            FutureCapabilityAdapter(),
        ]
        self._adapters = {adapter.descriptor.capability_id: adapter for adapter in configured}

    def list_descriptors(self) -> list[ControlPlaneCapabilityRead]:
        return sorted(
            (adapter.descriptor for adapter in self._adapters.values()),
            key=lambda item: item.capability_id,
        )

    def get(self, capability_id: str) -> CapabilityAdapter:
        adapter = self._adapters.get(capability_id)
        if adapter is None:
            raise KeyError(capability_id)
        return adapter


def _priority_from_task(task: ControlPlaneTaskRead, *, default: int) -> int:
    raw = task.metadata.get("priority", default)
    try:
        return max(0, min(int(raw), 100))
    except (TypeError, ValueError):
        return default
