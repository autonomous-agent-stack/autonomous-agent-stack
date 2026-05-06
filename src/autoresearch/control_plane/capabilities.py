from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

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
        primary_agent, agent_names = _agent_attribution_for_task(task)
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.NOOP,
            payload={
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "parameters": task.parameters,
                "intent": task.intent,
                "runtime_id": task.parameters.get("runtime_id") or task.capability_id,
                "agent_name": primary_agent,
                "target_agent": primary_agent,
                "target_agents": agent_names,
            },
            requested_by=task.requested_by,
            priority=0,
            metadata=_base_worker_metadata(task),
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
        action = str(task.parameters.get("action") or "").strip() or "read_issue"
        primary_agent, agent_names = _agent_attribution_for_task(task)
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.GITHUB_OPS,
            payload={
                "action": action,
                "repo": task.parameters.get("repo"),
                "issue_number": task.parameters.get("issue_number"),
                "pr_number": task.parameters.get("pr_number"),
                "comment": task.parameters.get("comment"),
                "labels": task.parameters.get("labels") or [],
                "account_profile": task.parameters.get("account_profile") or "accountA",
                "metadata": {
                    **_base_worker_metadata(task),
                    "source": "control_plane_v2",
                    "request_text": task.intent or task.name,
                    "runtime_id": task.parameters.get("runtime_id") or "claude",
                    "agent_name": primary_agent,
                    "target_agent": primary_agent,
                    "target_agents": agent_names,
                    "canonical_task_type": task.parameters.get("canonical_task_type"),
                },
            },
            requested_by=task.requested_by,
            priority=_priority_from_task(task, default=8),
            metadata=_base_worker_metadata(task),
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
        primary_agent, agent_names = _agent_attribution_for_task(task)
        source_files = _list_param(task.parameters, "source_files") or _list_param(
            task.parameters, "attachments"
        )
        rules = _list_param(task.parameters, "rules")
        sheet_mapping = _dict_param(task.parameters, "sheet_mapping")
        outputs = _dict_param(task.parameters, "outputs") or _dict_param(task.parameters, "options")
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.EXCEL_AUDIT,
            payload={
                "task_brief": task.intent or task.name,
                "source_files": source_files,
                "rules": rules,
                "sheet_mapping": sheet_mapping,
                "outputs": outputs,
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "request_text": task.intent or task.name,
                "runtime_id": task.parameters.get("runtime_id") or task.capability_id,
                "agent_name": primary_agent,
                "target_agent": primary_agent,
                "target_agents": agent_names,
            },
            requested_by=task.requested_by,
            priority=_priority_from_task(task, default=3),
            metadata=_base_worker_metadata(task),
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
        request_text = task.intent or task.name
        source_url = _first_url(task.parameters, request_text, youtube_only=True)
        primary_agent, agent_names = _agent_attribution_for_task(task)
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.YOUTUBE_AUTOFLOW,
            payload={
                "source_url": source_url,
                "input_text": request_text,
                "requested_by": task.requested_by,
                "source": "control_plane_v2",
                "metadata": {
                    **_base_worker_metadata(task),
                    "request_text": request_text,
                    "source_url": source_url,
                    "session_id": task.session_id,
                    "task_id": task.task_id,
                    "capability_id": task.capability_id,
                    "runtime_id": task.parameters.get("runtime_id") or task.capability_id,
                    "agent_name": primary_agent,
                    "target_agent": primary_agent,
                    "target_agents": agent_names,
                },
            },
            requested_by=task.requested_by,
            priority=_priority_from_task(task, default=5),
            metadata=_base_worker_metadata(task),
        )


class SourceCollectCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="source_collect",
        name="Source collector",
        type="source_collect",
        enabled=True,
        dispatch_mode="worker_queue",
        description="Collects X bookmarks or local source fixtures into text artifacts before knowledge-base ingest.",
        risk_tags=["filesystem_write", "external_api"],
        requires_approval=True,
        external_calls_enabled=True,
        metadata={"worker_task_type": WorkerTaskType.SOURCE_COLLECT.value},
    )

    def build_worker_request(self, task: ControlPlaneTaskRead) -> WorkerQueueItemCreateRequest:
        request_text = task.intent or task.name
        source_kind = str(
            task.parameters.get("source_kind")
            or _source_kind_from_text(request_text)
        ).strip() or "bookmarks"
        primary_agent, agent_names = _agent_attribution_for_task(task)
        source_urls = _list_param(task.parameters, "source_urls") or _list_param(task.parameters, "urls")
        source_url = task.parameters.get("source_url") or _first_url(task.parameters, request_text)
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.SOURCE_COLLECT,
            payload={
                "source_kind": source_kind,
                "fixture_path": task.parameters.get("fixture_path")
                or task.parameters.get("source_fixture_path")
                or "",
                "limit": task.parameters.get("limit") or 50,
                "max_pages": task.parameters.get("max_pages", 1),
                "collector": task.parameters.get("collector") or "xreach",
                "title": task.parameters.get("title") or task.name,
                "topic": task.parameters.get("topic") or "",
                "source_url": source_url or "",
                "source_urls": source_urls,
                "owner": task.parameters.get("owner") or "knowledge-base",
                "default_repo": task.parameters.get("default_repo") or "knowledge-base",
                "downstream_capability_id": task.parameters.get("downstream_capability_id") or "content_kb",
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "request_text": request_text,
                "runtime_id": "source_collect",
                "agent_name": primary_agent,
                "target_agent": primary_agent,
                "target_agents": agent_names,
            },
            requested_by=task.requested_by,
            priority=_priority_from_task(task, default=4),
            metadata=_base_worker_metadata(task),
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
        request_text = task.intent or task.name
        subtitle_text_path = str(
            task.parameters.get("subtitle_text_path")
            or task.parameters.get("file_path")
            or _first_text_path(task.parameters)
            or ""
        ).strip()
        primary_agent, agent_names = _agent_attribution_for_task(task)
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={
                "subtitle_text_path": subtitle_text_path,
                "title": task.parameters.get("title") or task.name,
                "topic": task.parameters.get("topic") or "",
                "source_url": task.parameters.get("source_url")
                or _first_url(task.parameters, request_text),
                "speakers": _list_param(task.parameters, "speakers"),
                "created_at": task.parameters.get("created_at") or "",
                "owner": task.parameters.get("owner") or "knowledge-base",
                "default_repo": task.parameters.get("default_repo") or "knowledge-base",
                "open_draft_pr": bool(task.parameters.get("open_draft_pr")),
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "request_text": task.intent or task.name,
                "runtime_id": task.parameters.get("runtime_id") or task.capability_id,
                "agent_name": primary_agent,
                "target_agent": primary_agent,
                "target_agents": agent_names,
            },
            requested_by=task.requested_by,
            priority=_priority_from_task(task, default=4),
            metadata=_base_worker_metadata(task),
        )


class ButlerContextStatusCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="butler_context_status",
        name="Butler context status / 管家上下文状态",
        type="local",
        enabled=True,
        dispatch_mode="worker_queue",
        description=(
            "本地回答上下文状态追问，不进入 worker 队列。 / "
            "Answers contextual status follow-ups locally without entering the worker queue."
        ),
        risk_tags=[],
        requires_approval=False,
        external_calls_enabled=False,
        metadata={"worker_task_type": WorkerTaskType.NOOP.value, "immediate_result": True},
    )

    def dispatch(self, task: ControlPlaneTaskRead) -> CapabilityDispatch:
        params = task.parameters if isinstance(task.parameters, dict) else {}
        answer = str(params.get("context_status_answer") or "").strip()
        if not answer:
            answer = (
                "本地无法确认：当前任务没有可解析的上一轮同步上下文。\n"
                "Unable to confirm locally: this task has no parseable previous sync context."
            )
        return CapabilityDispatch(
            immediate_result={
                "status": "completed",
                "summary": answer,
                "answer": answer,
                "source": "butler_context_status",
                "capability_id": task.capability_id,
                "context_status_kind": params.get("context_status_kind"),
                "context_status_confirmed": bool(params.get("context_status_confirmed")),
                "kb_repo": params.get("kb_repo"),
                "kb_topic": params.get("kb_topic"),
                "kb_files": _list_param(params, "kb_files"),
                "followup_text": params.get("followup_text"),
            }
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
        primary_agent, agent_names = _agent_attribution_for_task(task)
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.CLAUDE_RUNTIME,
            payload={
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "prompt": task.intent or task.name,
                "parameters": task.parameters,
                "runtime_id": task.parameters.get("runtime_id") or "claude",
                "agent_name": primary_agent,
                "target_agent": primary_agent,
                "target_agents": agent_names,
            },
            requested_by=task.requested_by,
            priority=task.metadata.get("priority", 5),
            metadata=_base_worker_metadata(task),
        )


class SecurityAuditCapabilityAdapter(CapabilityAdapter):
    descriptor = ControlPlaneCapabilityRead(
        capability_id="security_audit",
        name="Security audit",
        type="security",
        enabled=True,
        dispatch_mode="worker_queue",
        description="Runs lightweight governance checks, rule candidate audits, and daily security reports.",
        risk_tags=[],
        requires_approval=False,
        external_calls_enabled=False,
        metadata={"worker_task_type": WorkerTaskType.SECURITY_AUDIT.value},
    )

    def build_worker_request(self, task: ControlPlaneTaskRead) -> WorkerQueueItemCreateRequest:
        primary_agent, agent_names = _agent_attribution_for_task(task)
        action = str(task.parameters.get("action") or "quick_scan").strip() or "quick_scan"
        return WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.SECURITY_AUDIT,
            payload={
                "action": action,
                "diff": task.parameters.get("diff"),
                "files": _list_param(task.parameters, "files"),
                "rule_candidate": task.parameters.get("rule_candidate"),
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "request_text": task.intent or task.name,
                "runtime_id": task.parameters.get("runtime_id") or task.capability_id,
                "agent_name": primary_agent,
                "target_agent": primary_agent,
                "target_agents": agent_names,
            },
            requested_by=task.requested_by,
            priority=_priority_from_task(task, default=6),
            metadata=_base_worker_metadata(task),
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
            SourceCollectCapabilityAdapter(),
            ContentKBCapabilityAdapter(),
            ButlerContextStatusCapabilityAdapter(),
            HermesOpenClawCapabilityAdapter(),
            SecurityAuditCapabilityAdapter(),
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


_URL_RE = re.compile(r"https?://[^\s<>()]+")
_TEXT_PATH_SUFFIXES = (".srt", ".vtt", ".txt", ".md")


def _base_worker_metadata(task: ControlPlaneTaskRead) -> dict[str, Any]:
    primary_agent, agent_names = _agent_attribution_for_task(task)
    metadata = {
        "aas_session_id": task.session_id,
        "control_plane_task_id": task.task_id,
        "control_plane_session_id": task.session_id,
        "capability_id": task.capability_id,
        "control_plane_v2": True,
        "target_agent": primary_agent,
        "target_agents": agent_names,
        "telegram_display_primary_agent": primary_agent,
        "telegram_display_agent_names": agent_names,
    }
    tool_grants = task.metadata.get("tool_grants")
    if isinstance(tool_grants, list):
        metadata["tool_grants"] = tool_grants
    tool_broker = task.metadata.get("tool_broker")
    if isinstance(tool_broker, dict):
        metadata["tool_broker"] = tool_broker
    return metadata


def _agent_attribution_for_task(task: ControlPlaneTaskRead) -> tuple[str, list[str]]:
    params = task.parameters or {}
    primary = str(
        params.get("target_agent")
        or params.get("agent_name")
        or _default_agent_for_capability(task.capability_id)
    ).strip()
    if not primary:
        primary = "butler_orchestrator"
    names: list[str] = []
    for key in ("target_agents", "agent_names", "agents"):
        names.extend(str(item).strip() for item in _list_param(params, key) if str(item).strip())
    names.append(primary)
    return primary[:200], _dedupe_agent_names(names)[:8]


def _default_agent_for_capability(capability_id: str) -> str:
    return {
        "github_assistant": "github_ops_accountA",
        "excel_audit": "excel_audit",
        "youtube_autoflow": "youtube_ops",
        "source_collect": "source_collect",
        "content_kb": "content_kb",
        "butler_context_status": "butler_orchestrator",
        "hermes_openclaw": "butler_orchestrator",
        "security_audit": "security_audit",
    }.get(str(capability_id or "").strip(), "butler_orchestrator")


def _dedupe_agent_names(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        name = str(raw or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def _list_param(parameters: dict[str, Any], key: str) -> list[Any]:
    value = parameters.get(key)
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _dict_param(parameters: dict[str, Any], key: str) -> dict[str, Any]:
    value = parameters.get(key)
    return dict(value) if isinstance(value, dict) else {}


def _first_url(
    parameters: dict[str, Any],
    text: str,
    *,
    youtube_only: bool = False,
) -> str | None:
    candidates: list[str] = []
    for raw in _list_param(parameters, "urls"):
        candidates.append(str(raw))
    source_url = parameters.get("source_url")
    if source_url:
        candidates.append(str(source_url))
    candidates.extend(_URL_RE.findall(text or ""))
    for candidate in candidates:
        cleaned = candidate.rstrip(".,)").strip()
        if not cleaned:
            continue
        if youtube_only and "youtu" not in cleaned.lower():
            continue
        return cleaned
    return None


def _first_text_path(parameters: dict[str, Any]) -> str | None:
    for key in ("attachments", "source_files", "paths", "files"):
        for raw in _list_param(parameters, key):
            candidate = str(raw).strip()
            if candidate.lower().endswith(_TEXT_PATH_SUFFIXES):
                return candidate
    return None


def _source_kind_from_text(text: str) -> str:
    normalized = str(text or "").strip().lower()
    if any(
        token in normalized
        for token in (
            "推特书签",
            "twitter bookmark",
            "twitter bookmarks",
            "x 书签",
            "x书签",
            "x bookmark",
            "x bookmarks",
        )
    ):
        return "x_bookmarks"
    return "bookmarks"
