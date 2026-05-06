from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import Field, field_validator

from autoresearch.control_plane.contracts import (
    ControlPlaneCapabilityRead,
    ControlPlaneTaskCreateRequest,
    ControlPlaneTaskRead,
)
from autoresearch.core.services.butler_dispatch import (
    ButlerDispatchCenter,
    ButlerDispatchDecision,
)
from autoresearch.core.services.butler_router import ButlerCanonicalTaskType
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.shared.models import SessionEventCreateRequest, StrictModel
from autoresearch.shared.store import create_resource_id


class ButlerControlPlaneRouteRequest(StrictModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    requested_by: str = "local-user"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message", mode="before")
    @classmethod
    def _strip_message(cls, value: Any) -> str:
        return " ".join(str(value or "").split())

    @field_validator("requested_by", mode="before")
    @classmethod
    def _strip_requested_by(cls, value: Any) -> str:
        return " ".join(str(value or "local-user").split()) or "local-user"

    @field_validator("session_id", mode="before")
    @classmethod
    def _strip_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None


class ButlerControlPlaneRouteRead(StrictModel):
    dispatch_decision: ButlerDispatchDecision
    task_request: ControlPlaneTaskCreateRequest
    task: ControlPlaneTaskRead | None = None


def route_butler_message(
    request: ButlerControlPlaneRouteRequest,
    *,
    dispatch_center: ButlerDispatchCenter,
    session_events: SessionEventService,
    capabilities: Sequence[ControlPlaneCapabilityRead],
    default_runtime_id: str = "claude",
    hermes_execution_mode: str = "oneshot",
) -> ButlerControlPlaneRouteRead:
    decision = dispatch_center.dispatch(
        request.message,
        default_runtime_id=default_runtime_id,
        hermes_execution_mode=hermes_execution_mode,
    )
    task_request = build_task_request_from_decision(
        request=request,
        decision=decision,
        capabilities=capabilities,
    )
    _record_route_decision(
        request=request,
        decision=decision,
        task_request=task_request,
        session_events=session_events,
    )
    return ButlerControlPlaneRouteRead(
        dispatch_decision=decision,
        task_request=task_request,
    )


def build_task_request_from_decision(
    *,
    request: ButlerControlPlaneRouteRequest,
    decision: ButlerDispatchDecision,
    capabilities: Sequence[ControlPlaneCapabilityRead],
) -> ControlPlaneTaskCreateRequest:
    capability_id = capability_id_for_decision(decision)
    display_message = _task_display_message(request)
    capability_risk_tags = _risk_tags_for_capability(capability_id, capabilities)
    risk_tags = sorted(
        {
            *capability_risk_tags,
            *_heuristic_risk_tags(request.message, capability_id=capability_id),
        }
    )
    extracted_params = dict(decision.extracted_params)
    parameters: dict[str, Any] = {
        **extracted_params,
        "message": request.message,
        "request_text": request.message,
        "display_text": display_message,
        "original_message": request.metadata.get("telegram_original_text") or display_message,
        "contextual_followup": bool(request.metadata.get("telegram_contextual_followup")),
        "extracted_params": extracted_params,
        "task_type": decision.task_type,
        "canonical_task_type": decision.canonical_task_type,
        "worker_task_type": decision.worker_task_type,
        "action": decision.action,
        "target_agent": decision.target_agent,
        "runtime_id": decision.runtime_id,
        "execution_mode": decision.execution_mode,
        "route": decision.route,
        "approval_policy": decision.approval_policy,
        "max_retries": decision.max_retries,
    }
    if decision.model_fill_error:
        parameters["model_fill_error"] = decision.model_fill_error

    return ControlPlaneTaskCreateRequest(
        name=_summarize_message(display_message),
        intent=request.message,
        session_id=request.session_id or create_resource_id("session"),
        capability_id=capability_id,
        parameters=parameters,
        risk_tags=risk_tags,
        requested_by=request.requested_by,
        priority=decision.priority,
        metadata={
            **request.metadata,
            "butler_bridge": True,
            "butler_source": decision.source,
            "butler_confidence": decision.confidence,
            "butler_reason": decision.reason,
            "butler_route": decision.route,
            "butler_task_type": decision.task_type,
            "butler_canonical_task_type": decision.canonical_task_type,
        },
    )


def _task_display_message(request: ButlerControlPlaneRouteRequest) -> str:
    for key in ("telegram_original_text", "display_message", "original_message"):
        value = request.metadata.get(key)
        text = " ".join(str(value or "").split())
        if text:
            return text
    return request.message


def capability_id_for_decision(decision: ButlerDispatchDecision) -> str:
    canonical = str(decision.canonical_task_type or "").strip().lower()
    if canonical in {
        ButlerCanonicalTaskType.GITHUB_ISSUE_OPS,
        ButlerCanonicalTaskType.GITHUB_PR_OPS,
    }:
        return "github_assistant"
    if canonical == ButlerCanonicalTaskType.EXCEL_COMMISSION:
        return "excel_audit"
    if canonical == ButlerCanonicalTaskType.YOUTUBE_AUTOFLOW:
        return "youtube_autoflow"
    if canonical == ButlerCanonicalTaskType.SOURCE_COLLECT:
        return "source_collect"
    if canonical in {
        ButlerCanonicalTaskType.CONTENT_KB_INGEST,
        ButlerCanonicalTaskType.BOOKMARK_ORGANIZE,
    }:
        return "content_kb"

    target_agent = str(decision.target_agent or "").strip().lower()
    if target_agent.startswith("github_ops"):
        return "github_assistant"
    if target_agent == "excel_audit":
        return "excel_audit"
    if target_agent == "youtube_ops":
        return "youtube_autoflow"
    if target_agent == "source_collect":
        return "source_collect"
    if target_agent == "content_kb":
        return "content_kb"
    return "hermes_openclaw"


def _risk_tags_for_capability(
    capability_id: str,
    capabilities: Sequence[ControlPlaneCapabilityRead],
) -> set[str]:
    for capability in capabilities:
        if capability.capability_id == capability_id:
            return {tag.strip().lower() for tag in capability.risk_tags if tag.strip()}
    return set()


def _heuristic_risk_tags(message: str, *, capability_id: str) -> set[str]:
    normalized = message.lower()
    tags: set[str] = set()
    if capability_id in {"github_assistant", "youtube_autoflow", "mcp", "a2a"}:
        tags.add("external_api")
    if _contains_any(
        normalized,
        (
            "github",
            "youtube",
            "youtu.be",
            "mcp",
            "a2a",
            "api",
            "webhook",
            "http://",
            "https://",
        ),
    ):
        tags.add("external_api")
    if _contains_any(
        normalized,
        (
            "write",
            "save",
            "export",
            "file",
            "写入",
            "保存",
            "导出",
            "生成文件",
            "入库",
        ),
    ):
        tags.add("filesystem_write")
    if capability_id != "excel_audit" and _contains_any(normalized, ("xlsx", "csv")):
        tags.add("filesystem_write")
    if _contains_any(
        normalized,
        (
            "shell",
            "command",
            "script",
            "bash",
            "zsh",
            "terminal",
            "命令",
            "脚本",
            "执行脚本",
            "终端",
        ),
    ):
        tags.add("shell")
    return tags


def _record_route_decision(
    *,
    request: ButlerControlPlaneRouteRequest,
    decision: ButlerDispatchDecision,
    task_request: ControlPlaneTaskCreateRequest,
    session_events: SessionEventService,
) -> None:
    event_id = create_resource_id("butler_route")
    session_events.append(
        SessionEventCreateRequest(
            session_id=task_request.session_id or create_resource_id("session"),
            source="butler",
            event_type="butler.route.decided",
            role="status",
            content=f"Butler routed message to {task_request.capability_id}.",
            status="decided",
            runtime_id=decision.runtime_id,
            idempotency_key=f"butler-route:{event_id}",
            metadata={
                "route_event_id": event_id,
                "requested_by": request.requested_by,
                "capability_id": task_request.capability_id,
                "risk_tags": task_request.risk_tags,
                "dispatch_decision": decision.model_dump(mode="json"),
                "task_request": task_request.model_dump(mode="json"),
                "input_metadata": request.metadata,
            },
        )
    )


def _contains_any(text: str, candidates: Sequence[str]) -> bool:
    return any(candidate in text for candidate in candidates)


def _summarize_message(message: str) -> str:
    normalized = " ".join(message.split())
    if len(normalized) <= 86:
        return normalized
    return f"{normalized[:83].rstrip()}..."
