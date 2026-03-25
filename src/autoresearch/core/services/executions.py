from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time

from autoresearch.shared.models import ExecutionCreateRequest, ExecutionRead, JobStatus, utc_now
from autoresearch.shared.store import Repository, create_resource_id


class ExecutionService:
    """Execute shell commands in a controlled API job lifecycle."""

    def __init__(self, repository: Repository[ExecutionRead], repo_root: Path | None = None) -> None:
        self._repository = repository
        self._repo_root = repo_root or Path(__file__).resolve().parents[4]

    def create(self, request: ExecutionCreateRequest) -> ExecutionRead:
        now = utc_now()
        execution = ExecutionRead(
            execution_id=create_resource_id("exec"),
            name=request.name,
            status=JobStatus.QUEUED,
            command=list(request.command),
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
        return self._repository.save(execution.execution_id, execution)

    def list(self) -> list[ExecutionRead]:
        return self._repository.list()

    def get(self, execution_id: str) -> ExecutionRead | None:
        return self._repository.get(execution_id)

    def execute(self, execution_id: str, request: ExecutionCreateRequest) -> None:
        current = self.get(execution_id)
        if current is None:
            return

        running = current.model_copy(
            update={
                "status": JobStatus.RUNNING,
                "updated_at": utc_now(),
                "error": None,
            }
        )
        self._repository.save(running.execution_id, running)

        command = list(request.command)
        work_dir = self._resolve_work_dir(request.work_dir)
        env = os.environ.copy()
        env.update(request.env)

        started = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
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
            self._repository.save(finalized.execution_id, finalized)
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
                    "error": f"execution timed out after {request.timeout_seconds}s",
                    "metadata": {
                        **running.metadata,
                        "work_dir": str(work_dir),
                        "env_overrides": request.env,
                    },
                }
            )
            self._repository.save(timed_out.execution_id, timed_out)
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
            self._repository.save(missing.execution_id, missing)

    def _build_error_message(self, completed: subprocess.CompletedProcess[str]) -> str:
        stderr = self._preview_output(completed.stderr or "")
        if stderr:
            return stderr
        return f"executor exited with code {completed.returncode}"

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
