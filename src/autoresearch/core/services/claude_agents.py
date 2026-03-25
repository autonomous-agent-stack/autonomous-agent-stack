from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import time

from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.shared.models import (
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    JobStatus,
    OpenClawSessionCreateRequest,
    OpenClawSessionEventAppendRequest,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


class ClaudeAgentService:
    """Claude CLI subagent scheduler with depth/concurrency guardrails."""

    ACTIVE_STATUSES = {JobStatus.QUEUED, JobStatus.RUNNING}

    def __init__(
        self,
        repository: Repository[ClaudeAgentRunRead],
        openclaw_service: OpenClawCompatService,
        repo_root: Path | None = None,
        max_agents: int = 20,
        max_depth: int = 3,
        claude_command: list[str] | None = None,
    ) -> None:
        self._repository = repository
        self._openclaw_service = openclaw_service
        self._repo_root = repo_root or Path(__file__).resolve().parents[4]
        self._max_agents = max_agents
        self._max_depth = max_depth
        if claude_command is not None:
            self._claude_command = list(claude_command)
        else:
            self._claude_command = shlex.split(os.getenv("AUTORESEARCH_CLAUDE_COMMAND", "claude"))

    def create(self, request: ClaudeAgentCreateRequest) -> ClaudeAgentRunRead:
        if request.generation_depth > self._max_depth:
            raise ValueError(
                f"generation depth {request.generation_depth} exceeds max depth {self._max_depth}"
            )
        if self.active_count() >= self._max_agents:
            raise RuntimeError(f"active agent limit reached ({self._max_agents})")

        session_id = request.session_id
        if session_id is None:
            session = self._openclaw_service.create_session(
                OpenClawSessionCreateRequest(
                    channel="claude_cli",
                    title=request.task_name,
                    metadata={
                        "source": "claude_agent_scheduler",
                        "parent_agent_id": request.parent_agent_id,
                    },
                )
            )
            session_id = session.session_id
        elif self._openclaw_service.get_session(session_id) is None:
            raise ValueError(f"session not found: {session_id}")

        command = self._build_command(request)
        now = utc_now()
        run = ClaudeAgentRunRead(
            agent_run_id=create_resource_id("agent"),
            task_name=request.task_name,
            prompt=request.prompt,
            status=JobStatus.QUEUED,
            agent_name=request.agent_name,
            session_id=session_id,
            parent_agent_id=request.parent_agent_id,
            generation_depth=request.generation_depth,
            command=command,
            timeout_seconds=request.timeout_seconds,
            work_dir=str(self._resolve_work_dir(request.work_dir)),
            returncode=None,
            stdout_preview=None,
            stderr_preview=None,
            duration_seconds=None,
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
            error=None,
        )
        saved = self._repository.save(run.agent_run_id, run)
        self._openclaw_service.append_event(
            session_id=session_id,
            request=OpenClawSessionEventAppendRequest(
                role="status",
                content=f"agent queued: {saved.agent_run_id}",
                metadata={
                    "agent_run_id": saved.agent_run_id,
                    "generation_depth": saved.generation_depth,
                    "parent_agent_id": saved.parent_agent_id,
                },
            ),
        )
        self._openclaw_service.set_status(
            session_id=session_id,
            status=JobStatus.QUEUED,
            metadata_updates={"latest_agent_run_id": saved.agent_run_id},
        )
        return saved

    def list(self) -> list[ClaudeAgentRunRead]:
        return self._repository.list()

    def get(self, agent_run_id: str) -> ClaudeAgentRunRead | None:
        return self._repository.get(agent_run_id)

    def active_count(self) -> int:
        return sum(1 for item in self.list() if item.status in self.ACTIVE_STATUSES)

    def execute(self, agent_run_id: str, request: ClaudeAgentCreateRequest) -> None:
        current = self.get(agent_run_id)
        if current is None:
            return

        running = current.model_copy(
            update={
                "status": JobStatus.RUNNING,
                "updated_at": utc_now(),
                "error": None,
            }
        )
        self._repository.save(running.agent_run_id, running)

        if running.session_id is not None:
            self._openclaw_service.append_event(
                session_id=running.session_id,
                request=OpenClawSessionEventAppendRequest(
                    role="status",
                    content=f"agent running: {running.agent_run_id}",
                    metadata={"agent_run_id": running.agent_run_id},
                ),
            )
            self._openclaw_service.set_status(
                session_id=running.session_id,
                status=JobStatus.RUNNING,
            )

        env = os.environ.copy()
        env.update(request.env)
        started = time.perf_counter()
        work_dir = self._resolve_work_dir(request.work_dir)

        try:
            completed = subprocess.run(
                running.command,
                cwd=work_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=request.timeout_seconds,
            )
            duration_seconds = time.perf_counter() - started
            succeeded = completed.returncode == 0
            finalized = running.model_copy(
                update={
                    "status": JobStatus.COMPLETED if succeeded else JobStatus.FAILED,
                    "returncode": completed.returncode,
                    "stdout_preview": self._preview_output(completed.stdout),
                    "stderr_preview": self._preview_output(completed.stderr),
                    "duration_seconds": duration_seconds,
                    "updated_at": utc_now(),
                    "error": None if succeeded else self._build_error_message(completed),
                    "metadata": {
                        **running.metadata,
                        "work_dir": str(work_dir),
                        "env_overrides": request.env,
                    },
                }
            )
            self._repository.save(finalized.agent_run_id, finalized)
            self._finalize_openclaw_session(finalized)
        except subprocess.TimeoutExpired as exc:
            duration_seconds = time.perf_counter() - started
            timed_out = running.model_copy(
                update={
                    "status": JobStatus.FAILED,
                    "returncode": -1,
                    "stdout_preview": self._preview_output(exc.stdout or ""),
                    "stderr_preview": self._preview_output(exc.stderr or ""),
                    "duration_seconds": duration_seconds,
                    "updated_at": utc_now(),
                    "error": f"agent timed out after {request.timeout_seconds}s",
                    "metadata": {
                        **running.metadata,
                        "work_dir": str(work_dir),
                        "env_overrides": request.env,
                    },
                }
            )
            self._repository.save(timed_out.agent_run_id, timed_out)
            self._finalize_openclaw_session(timed_out)
        except FileNotFoundError as exc:
            duration_seconds = time.perf_counter() - started
            missing = running.model_copy(
                update={
                    "status": JobStatus.FAILED,
                    "returncode": -1,
                    "duration_seconds": duration_seconds,
                    "updated_at": utc_now(),
                    "error": str(exc),
                    "metadata": {
                        **running.metadata,
                        "work_dir": str(work_dir),
                        "env_overrides": request.env,
                    },
                }
            )
            self._repository.save(missing.agent_run_id, missing)
            self._finalize_openclaw_session(missing)

    def _finalize_openclaw_session(self, run: ClaudeAgentRunRead) -> None:
        if run.session_id is None:
            return
        status_text = "completed" if run.status is JobStatus.COMPLETED else "failed"
        self._openclaw_service.append_event(
            session_id=run.session_id,
            request=OpenClawSessionEventAppendRequest(
                role="status",
                content=f"agent {status_text}: {run.agent_run_id}",
                metadata={
                    "agent_run_id": run.agent_run_id,
                    "returncode": run.returncode,
                    "duration_seconds": run.duration_seconds,
                    "error": run.error,
                },
            ),
        )
        self._openclaw_service.set_status(
            session_id=run.session_id,
            status=run.status,
            error=run.error,
            metadata_updates={
                "latest_agent_run_id": run.agent_run_id,
                "latest_status": run.status.value,
            },
        )

    def _build_command(self, request: ClaudeAgentCreateRequest) -> list[str]:
        if request.command_override:
            command = list(request.command_override)
        else:
            command = list(self._claude_command)
            if request.agent_name:
                command.extend(["--agent", request.agent_name])
            if request.cli_args:
                command.extend(request.cli_args)
            else:
                command.append("--print")

        if request.append_prompt:
            command.append(request.prompt)
        return command

    def _build_error_message(self, completed: subprocess.CompletedProcess[str]) -> str:
        stderr = self._preview_output(completed.stderr or "")
        if stderr:
            return stderr
        return f"agent exited with code {completed.returncode}"

    def _resolve_work_dir(self, work_dir: str | None) -> Path:
        if work_dir is None:
            return self._repo_root
        path = Path(work_dir)
        if path.is_absolute():
            return path.resolve()
        return (self._repo_root / path).resolve()

    def _preview_output(self, text: str, limit: int = 1000) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 16] + "\n...[truncated]"
