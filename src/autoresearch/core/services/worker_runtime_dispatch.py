"""Dispatch worker CLAUDE_RUNTIME payloads to claude CLI or Hermes runtime adapter."""

from __future__ import annotations

import logging
from typing import Any

from autoresearch.agent_protocol.runtime_models import RuntimeRunRead, RuntimeRunRequest
from autoresearch.core.services.claude_runtime_service import (
    ClaudeRuntimeExecutionResult,
    ClaudeRuntimeService,
)
from autoresearch.core.services.runtime_adapter_registry import RuntimeAdapterServiceRegistry
from autoresearch.shared.models import JobStatus

logger = logging.getLogger(__name__)


def build_runtime_run_request_for_telegram_hermes(payload: dict[str, Any]) -> RuntimeRunRequest:
    """Map Telegram worker payload to RuntimeRunRequest for Hermes (v1-safe surface)."""
    task_name = str(payload.get("task_name") or "telegram_hermes").strip() or "telegram_hermes"
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("empty prompt")

    timeout_seconds = max(30, min(int(payload.get("timeout_seconds", 900)), 7200))
    work_dir = payload.get("work_dir")
    work_dir_str = str(work_dir).strip() if work_dir else None

    raw_meta = payload.get("metadata")
    meta: dict[str, Any] = dict(raw_meta) if isinstance(raw_meta, dict) else {}
    hermes_overlay = meta.get("hermes")
    hermes_block: dict[str, Any] = dict(hermes_overlay) if isinstance(hermes_overlay, dict) else {}

    meta_out = dict(meta)
    if hermes_block:
        meta_out["hermes"] = hermes_block

    cli_args = list(payload.get("cli_args") or []) if isinstance(payload.get("cli_args"), list) else []

    env_raw = payload.get("env")
    env: dict[str, str] = {}
    if isinstance(env_raw, dict):
        env = {str(k): str(v) for k, v in env_raw.items()}

    return RuntimeRunRequest(
        runtime_id="hermes",
        session_id=str(payload.get("session_id")).strip() if payload.get("session_id") else None,
        task_name=task_name,
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        work_dir=work_dir_str,
        cli_args=cli_args,
        command_override=None,
        append_prompt=True,
        skill_names=[],
        images=[],
        env=env,
        metadata=meta_out,
    )


def runtime_run_read_to_claude_execution_result(read: RuntimeRunRead) -> ClaudeRuntimeExecutionResult:
    """Align Hermes RuntimeRunRead with ClaudeRuntimeExecutionResult for worker / Telegram."""
    meta = read.metadata if isinstance(read.metadata, dict) else {}
    error_kind = meta.get("error_kind")
    result: dict[str, Any] = {
        "runtime_run_id": read.run_id,
        "session_id": read.session_id,
        "returncode": read.returncode,
        "stdout_preview": read.stdout_preview,
        "stderr_preview": read.stderr_preview,
        "summary": read.summary,
        "runtime_id": read.runtime_id,
    }
    if error_kind is not None:
        result["error_kind"] = error_kind
    hint = _telegram_hint_for_hermes_failure(read)
    if hint:
        result["telegram_hint"] = hint

    metrics = dict(read.metrics.model_dump(mode="json"))
    metrics.setdefault("duration_seconds", (read.metrics.duration_ms or 0) / 1000.0)

    return ClaudeRuntimeExecutionResult(
        message=f"hermes_runtime {read.status.value}",
        status=read.status,
        error=read.error,
        agent_run_id=None,
        stdout_preview=read.stdout_preview,
        result=result,
        metrics=metrics,
    )


def _telegram_hint_for_hermes_failure(read: RuntimeRunRead) -> str | None:
    meta = read.metadata if isinstance(read.metadata, dict) else {}
    if meta.get("error_kind") != "invalid_request":
        return None
    return (
        "当前 Hermes 模式不支持该请求（例如图片、技能列表或 command_override）。"
        " / This Hermes mode does not support that request (e.g. images, skill lists, or command_override)."
    )


class WorkerRuntimeDispatchService:
    """Route CLAUDE_RUNTIME queue payloads to Claude CLI or Hermes runtime adapter."""

    def __init__(
        self,
        *,
        claude_runtime: ClaudeRuntimeService | None,
        registry: RuntimeAdapterServiceRegistry | None,
    ) -> None:
        self._claude_runtime = claude_runtime
        self._registry = registry

    def execute_payload(
        self,
        payload: dict[str, Any],
        *,
        worker_id: str | None = None,
        queue_metadata: dict[str, Any] | None = None,
    ) -> ClaudeRuntimeExecutionResult:
        runtime_id = str(payload.get("runtime_id") or "claude").strip().lower()
        if runtime_id == "claude":
            if self._claude_runtime is None:
                return ClaudeRuntimeExecutionResult(
                    message="claude_runtime not available",
                    status=JobStatus.FAILED,
                    error="ClaudeRuntimeService not configured on this worker",
                )
            return self._claude_runtime.execute_payload(
                payload,
                worker_id=worker_id,
                queue_metadata=queue_metadata,
            )

        if runtime_id == "hermes":
            return self._execute_hermes(payload, worker_id=worker_id, queue_metadata=queue_metadata)

        return ClaudeRuntimeExecutionResult(
            message=f"unsupported runtime_id {runtime_id}",
            status=JobStatus.FAILED,
            error=f"unsupported runtime_id: {runtime_id}",
        )

    def _execute_hermes(
        self,
        payload: dict[str, Any],
        *,
        worker_id: str | None,
        queue_metadata: dict[str, Any] | None,
    ) -> ClaudeRuntimeExecutionResult:
        if self._registry is None:
            return ClaudeRuntimeExecutionResult(
                message="hermes_runtime not available",
                status=JobStatus.FAILED,
                error="RuntimeAdapterServiceRegistry not configured on this worker",
            )
        if self._claude_runtime is None:
            return ClaudeRuntimeExecutionResult(
                message="hermes_runtime not available",
                status=JobStatus.FAILED,
                error="ClaudeRuntimeService not configured on this worker",
            )

        session_key = str(payload.get("session_key") or "")
        work_dir = payload.get("work_dir")

        if worker_id and session_key:
            try:
                self._claude_runtime.session_record_service.bind_session_to_worker(
                    session_key=session_key,
                    worker_id=worker_id,
                    project_dir=str(work_dir) if work_dir else None,
                )
            except Exception:
                logger.warning("Failed to bind sticky session for hermes %s", session_key, exc_info=True)

        try:
            request = build_runtime_run_request_for_telegram_hermes(payload)
        except ValueError as exc:
            self._update_sticky_hermes(session_key, JobStatus.FAILED, str(exc))
            return ClaudeRuntimeExecutionResult(
                message="hermes_runtime invalid request",
                status=JobStatus.FAILED,
                error=str(exc),
                result={"error_kind": "invalid_request", "telegram_hint": _telegram_hint_for_value_error()},
            )

        try:
            read = self._registry.get("hermes").run(request)
        except KeyError as exc:
            logger.warning("Hermes adapter missing: %s", exc)
            self._update_sticky_hermes(session_key, JobStatus.FAILED, str(exc))
            return ClaudeRuntimeExecutionResult(
                message="hermes_runtime not wired",
                status=JobStatus.FAILED,
                error=str(exc),
            )
        except ValueError as exc:
            logger.info("Hermes runtime rejected request: %s", exc)
            self._update_sticky_hermes(session_key, JobStatus.FAILED, str(exc))
            return ClaudeRuntimeExecutionResult(
                message="hermes_runtime invalid request",
                status=JobStatus.FAILED,
                error=str(exc),
                result={"error_kind": "invalid_request", "telegram_hint": _telegram_hint_for_value_error()},
            )
        except Exception as exc:
            logger.exception("Hermes runtime execute failed")
            self._update_sticky_hermes(session_key, JobStatus.FAILED, str(exc))
            return ClaudeRuntimeExecutionResult(
                message="hermes_runtime failed",
                status=JobStatus.FAILED,
                error=str(exc),
            )

        outcome = runtime_run_read_to_claude_execution_result(read)
        summary = (read.summary or read.stdout_preview or "")[:500]
        if read.status != JobStatus.COMPLETED:
            summary = (read.error or read.summary or "unknown")[:500]
        self._update_sticky_hermes(session_key, read.status, summary)
        return outcome

    def _update_sticky_hermes(self, session_key: str, status: JobStatus, summary: str) -> None:
        if not session_key:
            return
        try:
            self._claude_runtime.session_record_service.update_latest(
                session_key=session_key,
                last_summary=summary[:500],
            )
        except Exception:
            logger.warning("Failed to update sticky session for hermes %s", session_key, exc_info=True)


def _telegram_hint_for_value_error() -> str:
    return (
        "当前 Hermes 模式不支持该请求（例如图片、技能列表或 command_override）。"
        " / This Hermes mode does not support that request (e.g. images, skill lists, or command_override)."
    )
