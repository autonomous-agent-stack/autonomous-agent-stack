from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol

from autoresearch.core.services.approval_actions import HERMES_INTERACTIVE_APPROVAL_ACTION
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.claude_runtime_service import ClaudeRuntimeExecutionResult
from autoresearch.shared.models import (
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ApprovalRisk,
    AssistantScope,
    HermesInteractiveSessionRead,
    JobStatus,
    utc_now,
)
from autoresearch.shared.store import Repository


class HermesGatewayBridge(Protocol):
    """Interactive Hermes bridge contract for worker runtime dispatch."""

    def execute_interactive(self, payload: dict[str, Any]) -> ClaudeRuntimeExecutionResult:
        """Execute a Hermes task via interactive bridge transport."""


@dataclass(slots=True)
class HermesGatewayEvent:
    event_id: str
    event_type: str
    timestamp: datetime
    payload: dict[str, Any]


@dataclass(slots=True)
class HermesGatewaySession:
    gateway_session_id: str
    cursor: str | None = None


class HermesGatewayTransport(Protocol):
    def health_check(self) -> bool:
        """Return whether the gateway is reachable."""

    def open_or_resume_session(
        self,
        *,
        aas_session_id: str,
        gateway_session_id: str | None,
        prompt: str,
        payload: dict[str, Any],
    ) -> HermesGatewaySession:
        """Create or resume a gateway session."""

    def stream_events(
        self,
        *,
        gateway_session_id: str,
        cursor: str | None,
    ) -> list[HermesGatewayEvent]:
        """Return events after cursor."""

    def submit_approval_decision(
        self,
        *,
        gateway_session_id: str,
        event_id: str,
        decision: str,
        decided_by: str,
        note: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Deliver a human approval decision to the gateway."""


class HermesGatewayTransportError(RuntimeError):
    """Raised when the Hermes gateway transport cannot complete a request."""


@dataclass(slots=True)
class HttpHermesGatewayTransport:
    base_url: str
    health_path: str = "/health"
    timeout_seconds: float = 10.0

    def health_check(self) -> bool:
        try:
            with urllib.request.urlopen(self._url(self.health_path), timeout=self.timeout_seconds) as response:
                return 200 <= int(response.status) < 300
        except (OSError, urllib.error.URLError):
            return False

    def open_or_resume_session(
        self,
        *,
        aas_session_id: str,
        gateway_session_id: str | None,
        prompt: str,
        payload: dict[str, Any],
    ) -> HermesGatewaySession:
        data = self._post_json(
            "/sessions",
            {
                "aas_session_id": aas_session_id,
                "gateway_session_id": gateway_session_id,
                "prompt": prompt,
                "payload": payload,
            },
        )
        session_id = str(data.get("gateway_session_id") or data.get("session_id") or gateway_session_id or "").strip()
        if not session_id:
            raise HermesGatewayTransportError("Hermes gateway did not return a session id")
        cursor_raw = data.get("cursor")
        return HermesGatewaySession(
            gateway_session_id=session_id,
            cursor=str(cursor_raw) if cursor_raw is not None else None,
        )

    def stream_events(
        self,
        *,
        gateway_session_id: str,
        cursor: str | None,
    ) -> list[HermesGatewayEvent]:
        query = f"?cursor={urllib.parse.quote(cursor)}" if cursor else ""
        data = self._get_json(f"/sessions/{urllib.parse.quote(gateway_session_id)}/events{query}")
        raw_events = data.get("events") if isinstance(data, dict) else data
        if not isinstance(raw_events, list):
            raise HermesGatewayTransportError("Hermes gateway events response is not a list")
        return [_event_from_mapping(item) for item in raw_events if isinstance(item, dict)]

    def submit_approval_decision(
        self,
        *,
        gateway_session_id: str,
        event_id: str,
        decision: str,
        decided_by: str,
        note: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        path = (
            f"/sessions/{urllib.parse.quote(gateway_session_id)}"
            f"/approvals/{urllib.parse.quote(event_id)}/decision"
        )
        self._post_json(
            path,
            {
                "decision": decision,
                "decided_by": decided_by,
                "note": note,
                "metadata": dict(metadata or {}),
            },
        )

    def _url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        suffix = path if path.startswith("/") else f"/{path}"
        return f"{base}{suffix}"

    def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            self._url(path),
            data=json.dumps(body).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        data = self._read_json(request)
        if not isinstance(data, dict):
            raise HermesGatewayTransportError("Hermes gateway session response is not an object")
        return data

    def _get_json(self, path: str) -> Any:
        return self._read_json(urllib.request.Request(self._url(path), method="GET"))

    def _read_json(self, request: urllib.request.Request) -> Any:
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except (OSError, urllib.error.URLError) as exc:
            raise HermesGatewayTransportError(str(exc)) from exc
        try:
            return json.loads(payload) if payload else {}
        except json.JSONDecodeError as exc:
            raise HermesGatewayTransportError("Hermes gateway returned invalid JSON") from exc


@dataclass(slots=True)
class InMemoryHermesGatewayTransport:
    gateway_session_id: str
    events: list[HermesGatewayEvent]
    open_calls: list[dict[str, Any]] = field(default_factory=list, init=False)
    stream_calls: list[dict[str, Any]] = field(default_factory=list, init=False)
    approval_decisions: list[dict[str, Any]] = field(default_factory=list, init=False)
    approval_error: str | None = None

    def health_check(self) -> bool:
        return True

    def open_or_resume_session(
        self,
        *,
        aas_session_id: str,
        gateway_session_id: str | None,
        prompt: str,
        payload: dict[str, Any],
    ) -> HermesGatewaySession:
        self.open_calls.append(
            {
                "aas_session_id": aas_session_id,
                "gateway_session_id": gateway_session_id,
                "prompt": prompt,
                "payload": payload,
            }
        )
        return HermesGatewaySession(gateway_session_id=gateway_session_id or self.gateway_session_id)

    def stream_events(
        self,
        *,
        gateway_session_id: str,
        cursor: str | None,
    ) -> list[HermesGatewayEvent]:
        self.stream_calls.append({"gateway_session_id": gateway_session_id, "cursor": cursor})
        if cursor is None:
            return list(self.events)
        return [event for event in self.events if event.event_id > cursor]

    def submit_approval_decision(
        self,
        *,
        gateway_session_id: str,
        event_id: str,
        decision: str,
        decided_by: str,
        note: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self.approval_error:
            raise HermesGatewayTransportError(self.approval_error)
        self.approval_decisions.append(
            {
                "gateway_session_id": gateway_session_id,
                "event_id": event_id,
                "decision": decision,
                "decided_by": decided_by,
                "note": note,
                "metadata": dict(metadata or {}),
            }
        )


class PersistedHermesGatewayBridge:
    """Persist Hermes interactive session bindings and stream cursors."""

    def __init__(
        self,
        *,
        repository: Repository[HermesInteractiveSessionRead],
        transport: HermesGatewayTransport,
        approval_store: ApprovalStoreService | None = None,
    ) -> None:
        self._repository = repository
        self._transport = transport
        self._approval_store = approval_store

    def execute_interactive(self, payload: dict[str, Any]) -> ClaudeRuntimeExecutionResult:
        runtime_id = str(payload.get("runtime_id") or "hermes").strip().lower() or "hermes"
        session_id = str(payload.get("session_id") or payload.get("session_key") or "").strip()
        if not session_id:
            return self._failure(runtime_id=runtime_id, error="interactive payload missing session_id")
        prompt = str(payload.get("prompt") or "").strip()
        if not prompt:
            return self._failure(runtime_id=runtime_id, error="interactive payload missing prompt")
        if not self._transport.health_check():
            return self._failure(runtime_id=runtime_id, error="Hermes gateway health check failed")

        now = utc_now()
        existing = self._repository.get(session_id)
        try:
            gateway_session = self._transport.open_or_resume_session(
                aas_session_id=session_id,
                gateway_session_id=existing.hermes_gateway_session_id if existing else None,
                prompt=prompt,
                payload=payload,
            )
            cursor = existing.gateway_stream_cursor if existing else gateway_session.cursor
            events = self._transport.stream_events(
                gateway_session_id=gateway_session.gateway_session_id,
                cursor=cursor,
            )
        except HermesGatewayTransportError as exc:
            return self._failure(
                runtime_id=runtime_id,
                error=str(exc),
                gateway_session_id=existing.hermes_gateway_session_id if existing else None,
            )

        latest = existing
        status = JobStatus.RUNNING
        summary = "hermes interactive running"
        stdout_preview: str | None = None
        error: str | None = None
        cursor_out = cursor
        pending_approval: ApprovalRequestRead | None = None
        for event in events:
            cursor_out = event.event_id
            if event.payload.get("summary"):
                summary = str(event.payload["summary"])
            if event.payload.get("stdout_preview") is not None:
                stdout_preview = str(event.payload["stdout_preview"])
            if event.event_type == "interactive.completed":
                status = JobStatus.COMPLETED
            elif event.event_type == "interactive.failed":
                status = JobStatus.FAILED
                error = str(event.payload.get("error") or "hermes interactive failed")
            elif event.event_type == "interactive.approval_required":
                pending_approval = self._create_or_reuse_approval(
                    event=event,
                    payload=payload,
                    session_id=session_id,
                    gateway_session_id=gateway_session.gateway_session_id,
                )
                status = JobStatus.RUNNING
                summary = _approval_waiting_summary(pending_approval)
            latest = HermesInteractiveSessionRead(
                aas_session_id=session_id,
                hermes_gateway_session_id=gateway_session.gateway_session_id,
                run_id=str(payload.get("run_id") or "") or None,
                gateway_stream_cursor=cursor_out,
                worker_id=str(payload.get("worker_id") or "") or None,
                last_event=_event_to_mapping(event),
                created_at=existing.created_at if existing else now,
                updated_at=utc_now(),
                metadata={
                    **(existing.metadata if existing else {}),
                    "runtime_id": runtime_id,
                    "task_name": str(payload.get("task_name") or "hermes_interactive"),
                    **(
                        {
                            "pending_approval_id": pending_approval.approval_id,
                            "pending_approval_event_id": event.event_id,
                        }
                        if pending_approval is not None
                        else {}
                    ),
                },
            )
            self._repository.save(session_id, latest)

        if latest is None:
            latest = HermesInteractiveSessionRead(
                aas_session_id=session_id,
                hermes_gateway_session_id=gateway_session.gateway_session_id,
                run_id=str(payload.get("run_id") or "") or None,
                gateway_stream_cursor=cursor_out,
                worker_id=str(payload.get("worker_id") or "") or None,
                created_at=now,
                updated_at=now,
                metadata={"runtime_id": runtime_id, "task_name": str(payload.get("task_name") or "hermes_interactive")},
            )
            self._repository.save(session_id, latest)

        result = {
            "runtime_id": runtime_id,
            "execution_mode": "interactive",
            "aas_session_id": session_id,
            "hermes_gateway_session_id": latest.hermes_gateway_session_id,
            "gateway_stream_cursor": latest.gateway_stream_cursor,
        }
        if latest.last_event:
            result["last_event"] = latest.last_event
        if pending_approval is not None:
            result["approval_id"] = pending_approval.approval_id
            result["approval_status"] = pending_approval.status.value
        return ClaudeRuntimeExecutionResult(
            message=summary,
            status=status,
            error=error,
            stdout_preview=stdout_preview,
            result=result,
            metrics={
                "dispatch_runtime": runtime_id,
                "execution_mode": "interactive",
                "events_seen": len(events),
                "exit_reason": status.value,
                **(
                    {
                        "telegram_live_phase": "running",
                        "telegram_live_card_title": "Hermes 等待审批 / Hermes waiting for approval",
                        "telegram_live_stdout_tail": _approval_waiting_body(pending_approval),
                        "worker_pause_reason": HERMES_INTERACTIVE_APPROVAL_ACTION,
                        "hermes_interactive_waiting_for_approval": True,
                    }
                    if pending_approval is not None
                    else {}
                ),
            },
        )

    def _create_or_reuse_approval(
        self,
        *,
        event: HermesGatewayEvent,
        payload: dict[str, Any],
        session_id: str,
        gateway_session_id: str,
    ) -> ApprovalRequestRead:
        if self._approval_store is None:
            raise HermesGatewayTransportError("approval store is not configured")
        event_id = event.event_id.strip()
        if not event_id:
            raise HermesGatewayTransportError("approval_required event is missing event_id")
        existing = self._approval_store.find_by_metadata(
            {
                "action_type": HERMES_INTERACTIVE_APPROVAL_ACTION,
                "gateway_session_id": gateway_session_id,
                "gateway_event_id": event_id,
            },
            limit=1,
        )
        if existing:
            return existing[0]
        event_payload = dict(event.payload)
        title = str(event_payload.get("title") or "Hermes interactive approval required").strip()
        summary = str(
            event_payload.get("summary")
            or event_payload.get("message")
            or event_payload.get("reason")
            or "Hermes requested human approval before continuing."
        ).strip()
        return self._approval_store.create_request(
            ApprovalRequestCreateRequest(
                title=title,
                summary=summary,
                risk=_approval_risk_from_event(event_payload),
                source=HERMES_INTERACTIVE_APPROVAL_ACTION,
                telegram_uid=_approval_telegram_uid(payload),
                session_id=session_id,
                agent_run_id=str(payload.get("run_id") or "").strip() or None,
                assistant_scope=_assistant_scope_from_payload(payload),
                metadata={
                    "action_type": HERMES_INTERACTIVE_APPROVAL_ACTION,
                    "run_id": str(payload.get("run_id") or "").strip(),
                    "aas_session_id": session_id,
                    "gateway_session_id": gateway_session_id,
                    "gateway_event_id": event_id,
                    "worker_id": str(payload.get("worker_id") or "").strip(),
                    "task_name": str(payload.get("task_name") or "hermes_interactive").strip(),
                    "runtime_id": str(payload.get("runtime_id") or "hermes").strip().lower() or "hermes",
                    "event_payload": event_payload,
                },
            )
        )

    @staticmethod
    def _failure(
        *,
        runtime_id: str,
        error: str,
        gateway_session_id: str | None = None,
    ) -> ClaudeRuntimeExecutionResult:
        result: dict[str, Any] = {
            "runtime_id": runtime_id,
            "execution_mode": "interactive",
            "error_kind": "interactive_bridge_unavailable",
        }
        if gateway_session_id:
            result["hermes_gateway_session_id"] = gateway_session_id
        return ClaudeRuntimeExecutionResult(
            message="hermes_interactive unavailable",
            status=JobStatus.FAILED,
            error=error,
            result=result,
            metrics={
                "dispatch_runtime": runtime_id,
                "execution_mode": "interactive",
                "error_kind": "interactive_bridge_unavailable",
                "exit_reason": "interactive_bridge_unavailable",
            },
        )


@dataclass(slots=True)
class HermesGatewayDisabledBridge:
    """Explicit disabled bridge used when interactive mode is requested."""

    reason: str = "Hermes interactive bridge is not configured on this worker."

    def execute_interactive(self, payload: dict[str, Any]) -> ClaudeRuntimeExecutionResult:
        runtime_id = str(payload.get("runtime_id") or "hermes").strip().lower() or "hermes"
        return ClaudeRuntimeExecutionResult(
            message="hermes_interactive unavailable",
            status=JobStatus.FAILED,
            error=self.reason,
            result={
                "runtime_id": runtime_id,
                "execution_mode": "interactive",
                "error_kind": "interactive_bridge_unavailable",
                "telegram_hint": (
                    "当前 worker 未启用 Hermes interactive bridge。"
                    " / Hermes interactive bridge is not enabled on this worker."
                ),
            },
            metrics={
                "dispatch_runtime": runtime_id,
                "execution_mode": "interactive",
                "error_kind": "interactive_bridge_unavailable",
                "exit_reason": "interactive_bridge_unavailable",
            },
        )


def _event_from_mapping(item: dict[str, Any]) -> HermesGatewayEvent:
    timestamp_raw = item.get("timestamp")
    if isinstance(timestamp_raw, datetime):
        timestamp = timestamp_raw
    else:
        try:
            timestamp = datetime.fromisoformat(str(timestamp_raw))
        except (TypeError, ValueError):
            timestamp = utc_now()
    payload = item.get("payload")
    return HermesGatewayEvent(
        event_id=str(item.get("event_id") or item.get("id") or ""),
        event_type=str(item.get("event_type") or item.get("type") or "interactive.progress"),
        timestamp=timestamp,
        payload=dict(payload) if isinstance(payload, dict) else {},
    )


def _event_to_mapping(event: HermesGatewayEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "timestamp": event.timestamp.isoformat(),
        "payload": dict(event.payload),
    }


def _approval_telegram_uid(payload: dict[str, Any]) -> str | None:
    for key in ("actor_user_id", "chat_id"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return None


def _assistant_scope_from_payload(payload: dict[str, Any]) -> AssistantScope | None:
    raw = str(payload.get("scope") or "").strip().lower()
    if not raw:
        return None
    try:
        return AssistantScope(raw)
    except ValueError:
        return None


def _approval_risk_from_event(payload: dict[str, Any]) -> ApprovalRisk:
    raw = str(payload.get("risk") or "").strip().lower()
    if raw:
        try:
            return ApprovalRisk(raw)
        except ValueError:
            pass
    return ApprovalRisk.WRITE


def _approval_waiting_summary(approval: ApprovalRequestRead | None) -> str:
    if approval is None:
        return "hermes interactive approval required"
    return f"hermes interactive waiting for approval {approval.approval_id}"


def _approval_waiting_body(approval: ApprovalRequestRead | None) -> str:
    if approval is None:
        return "Hermes requested approval."
    return "\n".join(
        [
            "Hermes 请求人工审批后继续。 / Hermes requested approval before continuing.",
            f"approval_id: {approval.approval_id}",
            f"title: {approval.title}",
            f"summary: {approval.summary}",
            f"approve: /approve {approval.approval_id} approve",
            f"reject: /approve {approval.approval_id} reject",
        ]
    )
