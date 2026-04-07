"""Claude runtime execution service for worker-queue dispatched tasks.

Handles the execution of CLAUDE_RUNTIME worker tasks:
- Parses the task payload
- Resolves session context
- Executes via ClaudeAgentService (reused from existing flow)
- Records results and status events
- Updates sticky session records
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from autoresearch.shared.models import (
    ClaudeAgentCreateRequest,
    ClaudeRuntimeSessionRecordRead,
    JobStatus,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ClaudeRuntimeExecutionResult:
    message: str
    status: JobStatus = JobStatus.COMPLETED
    error: str | None = None
    agent_run_id: str | None = None
    stdout_preview: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)


class ClaudeRuntimeService:
    """Execute claude_runtime tasks on the worker side.

    Reuses ClaudeAgentService for the actual subprocess execution but
    decouples it from the Telegram webhook's direct call path.
    """

    def __init__(
        self,
        agent_service: Any,
        session_record_service: Any,
    ) -> None:
        self._agent_service = agent_service
        self._session_record_service = session_record_service

    def execute_payload(
        self,
        payload: dict[str, Any],
        *,
        worker_id: str | None = None,
        queue_metadata: dict[str, Any] | None = None,
    ) -> ClaudeRuntimeExecutionResult:
        session_id = payload.get("session_id")
        session_key = payload.get("session_key", "")
        prompt = payload.get("prompt", "")
        task_name = payload.get("task_name", "claude_runtime")
        assistant_id = payload.get("assistant_id")
        chat_id = payload.get("chat_id")
        message_thread_id = payload.get("message_thread_id")
        timeout_seconds = max(30, min(int(payload.get("timeout_seconds", 900)), 7200))
        work_dir = payload.get("work_dir")
        agent_name = payload.get("agent_name")
        cli_args = payload.get("cli_args", [])
        skill_names = payload.get("skill_names", [])
        images = payload.get("images", [])

        if not prompt:
            return ClaudeRuntimeExecutionResult(
                message="empty prompt",
                status=JobStatus.FAILED,
                error="No prompt provided in payload",
            )

        # Update sticky session record with current worker
        if worker_id and session_key:
            self._bind_sticky_session(session_key=session_key, worker_id=worker_id, work_dir=work_dir)

        # Build the ClaudeAgentCreateRequest
        request = ClaudeAgentCreateRequest(
            task_name=task_name,
            prompt=prompt,
            session_id=session_id,
            agent_name=agent_name,
            timeout_seconds=timeout_seconds,
            work_dir=work_dir,
            cli_args=cli_args,
            skill_names=skill_names,
            images=images,
            metadata={
                "source": "claude_runtime_worker",
                "session_key": session_key,
                "assistant_id": assistant_id,
                "chat_id": chat_id,
                "message_thread_id": message_thread_id,
                **(queue_metadata or {}),
            },
        )

        # Create the agent run
        run = self._agent_service.create(request)
        agent_run_id = run.agent_run_id

        logger.info(
            "claude_runtime created agent_run %s for session_key=%s",
            agent_run_id,
            session_key,
        )

        # Execute synchronously (worker is dedicated for this)
        try:
            self._agent_service.execute(agent_run_id, request)
        except Exception as exc:
            logger.exception("claude_runtime execute failed for agent_run %s", agent_run_id)
            # Update sticky record with failure
            self._update_sticky_summary(session_key=session_key, summary=f"failed: {exc}")
            return ClaudeRuntimeExecutionResult(
                message=f"execution failed: {exc}",
                status=JobStatus.FAILED,
                error=str(exc),
                agent_run_id=agent_run_id,
            )

        # Read the final result
        final_run = self._agent_service.get(agent_run_id)
        if final_run is None:
            return ClaudeRuntimeExecutionResult(
                message="run disappeared after execution",
                status=JobStatus.FAILED,
                error="Agent run not found after execution",
                agent_run_id=agent_run_id,
            )

        stdout_preview = final_run.stdout_preview
        error = final_run.error
        run_status = final_run.status

        # Update sticky record with success
        summary = (stdout_preview or "")[:500] if run_status == JobStatus.COMPLETED else (error or "unknown")[:500]
        self._update_sticky_summary(session_key=session_key, summary=summary)

        return ClaudeRuntimeExecutionResult(
            message=f"claude_runtime {run_status.value}",
            status=run_status,
            error=error,
            agent_run_id=agent_run_id,
            stdout_preview=stdout_preview,
            result={
                "agent_run_id": agent_run_id,
                "session_id": session_id,
                "returncode": final_run.returncode,
                "duration_seconds": final_run.duration_seconds,
            },
            metrics={
                "duration_seconds": final_run.duration_seconds or 0,
            },
        )

    def _bind_sticky_session(
        self,
        *,
        session_key: str,
        worker_id: str,
        work_dir: str | None = None,
    ) -> None:
        try:
            self._session_record_service.bind_session_to_worker(
                session_key=session_key,
                worker_id=worker_id,
                project_dir=work_dir,
            )
        except Exception:
            logger.warning("Failed to bind sticky session for %s", session_key, exc_info=True)

    def _update_sticky_summary(self, *, session_key: str, summary: str) -> None:
        try:
            self._session_record_service.update_latest(
                session_key=session_key,
                last_summary=summary,
            )
        except Exception:
            logger.warning("Failed to update sticky session summary for %s", session_key, exc_info=True)
