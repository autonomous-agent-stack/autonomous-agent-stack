from __future__ import annotations

from pathlib import Path

from autoresearch.core.repositories.evaluations import EvaluationRepository
from autoresearch.core.task_runner import run_task
from autoresearch.shared.models import EvaluationCreateRequest, EvaluationRead, JobStatus, utc_now
from autoresearch.shared.store import create_resource_id


class EvaluationService:
    """Evaluation service backed by the existing run_task flow."""

    def __init__(self, repository: EvaluationRepository, repo_root: Path | None = None) -> None:
        self._repository = repository
        self._repo_root = repo_root or Path(__file__).resolve().parents[3]

    def create(self, request: EvaluationCreateRequest) -> EvaluationRead:
        now = utc_now()
        evaluation = EvaluationRead(
            evaluation_id=create_resource_id("eval"),
            task_name=request.task_name,
            config_path=str(self._resolve_config_path(request.config_path)),
            description=request.description,
            status=JobStatus.QUEUED,
            result_status=None,
            run_id=None,
            score=None,
            summary="Evaluation accepted and queued.",
            duration_seconds=None,
            artifact_dir=None,
            metrics={},
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
            error=None,
        )
        return self._repository.create(evaluation, request)

    def list(self) -> list[EvaluationRead]:
        return self._repository.list()

    def get(self, evaluation_id: str) -> EvaluationRead | None:
        return self._repository.get(evaluation_id)

    def execute(self, evaluation_id: str, request: EvaluationCreateRequest) -> None:
        current = self.get(evaluation_id)
        if current is None:
            return

        running = current.model_copy(
            update={
                "status": JobStatus.RUNNING,
                "summary": "Evaluation running.",
                "updated_at": utc_now(),
                "error": None,
            }
        )
        self._repository.update(running)

        try:
            task_run = run_task(
                config_path=self._resolve_config_path(request.config_path),
                description=request.description,
                evaluator_command=request.evaluator_command,
            )
            result = task_run["result"]
            completed = running.model_copy(
                update={
                    "status": JobStatus.COMPLETED if str(result["status"]) == "pass" else JobStatus.FAILED,
                    "result_status": str(result["status"]),
                    "run_id": str(task_run["run_id"]),
                    "score": float(result["score"]),
                    "summary": str(result["summary"]),
                    "duration_seconds": float(task_run["duration_seconds"]),
                    "artifact_dir": str(task_run["artifact_dir"]),
                    "metrics": dict(result.get("metrics", {})),
                    "updated_at": utc_now(),
                    "error": self._build_error_message(task_run, result),
                    "metadata": {
                        **running.metadata,
                        "branch": task_run["branch"],
                        "commit": task_run["commit"],
                        "comparison": task_run["comparison"],
                        "best_before": task_run["best_before"],
                        "command": task_run["command"],
                        "command_source": task_run["command_source"],
                        "timeout_seconds": task_run["timeout_seconds"],
                        "work_dir": task_run["work_dir"],
                        "env_overrides": task_run["env_overrides"],
                        "returncode": task_run["returncode"],
                        "stdout_log": task_run["stdout_log"],
                        "stderr_log": task_run["stderr_log"],
                        "stdout_preview": task_run["stdout_preview"],
                        "stderr_preview": task_run["stderr_preview"],
                    },
                }
            )
            self._repository.update(completed)
        except Exception as exc:
            failed = running.model_copy(
                update={
                    "status": JobStatus.FAILED,
                    "result_status": "crash",
                    "summary": f"evaluation service crashed: {exc}",
                    "updated_at": utc_now(),
                    "error": str(exc),
                }
            )
            self._repository.update(failed)

    def recover_interrupted(self) -> int:
        return self._repository.interrupt_running(
            "API service restarted before evaluation finished."
        )

    def _build_error_message(
        self,
        task_run: dict[str, object],
        result: dict[str, object],
    ) -> str | None:
        if str(result.get("status")) == "pass":
            return None

        summary = str(result.get("summary") or "").strip()
        stderr_preview = str(task_run.get("stderr_preview") or "").strip()
        returncode = task_run.get("returncode")

        if summary and stderr_preview and stderr_preview not in summary:
            return f"{summary} | stderr: {stderr_preview}"
        if summary:
            return summary
        if stderr_preview:
            return stderr_preview
        if isinstance(returncode, int) and returncode != 0:
            return f"evaluator exited with code {returncode}"
        return None

    def _resolve_config_path(self, config_path: str) -> Path:
        path = Path(config_path)
        if path.is_absolute():
            return path
        return (self._repo_root / path).resolve()
