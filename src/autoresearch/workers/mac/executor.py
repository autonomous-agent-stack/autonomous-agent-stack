from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from autoresearch.core.services.apple_double_cleaner import AppleDoubleCleaner
from autoresearch.core.services.standby_youtube_autoflow import (
    StandbyYouTubeAutoflowService,
    build_default_standby_youtube_autoflow_service,
)
from autoresearch.core.services.standby_youtube_bridge import (
    StandbyYouTubeBridgeService,
    build_default_standby_youtube_bridge_service,
)
from autoresearch.shared.models import JobStatus, WorkerQueueItemRead, WorkerTaskType, utc_now
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.core.services.claude_runtime_service import ClaudeRuntimeService


@dataclass(slots=True)
class MacWorkerExecutionResult:
    message: str
    status: JobStatus = JobStatus.COMPLETED
    error: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)


class MacWorkerExecutor:
    def __init__(
        self,
        config: MacWorkerConfig,
        *,
        youtube_bridge: StandbyYouTubeBridgeService | None = None,
        youtube_autoflow: StandbyYouTubeAutoflowService | None = None,
        claude_runtime: ClaudeRuntimeService | None = None,
    ) -> None:
        self._config = config
        self._youtube_bridge = youtube_bridge
        self._youtube_autoflow = youtube_autoflow
        self._claude_runtime = claude_runtime

    def execute(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        if run.task_type == WorkerTaskType.NOOP:
            return self._execute_noop(run.payload)
        if run.task_type == WorkerTaskType.CLEANUP_APPLEDOUBLE:
            return self._execute_cleanup_appledouble(run.payload)
        if run.task_type == WorkerTaskType.CLEANUP_TMP:
            return self._execute_cleanup_tmp(run.payload)
        if run.task_type == WorkerTaskType.YOUTUBE_ACTION:
            return self._execute_youtube_action(run)
        if run.task_type == WorkerTaskType.YOUTUBE_AUTOFLOW:
            return self._execute_youtube_autoflow(run)
        if run.task_type == WorkerTaskType.CLAUDE_RUNTIME:
            return self._execute_claude_runtime(run)
        raise ValueError(f"Unsupported task type: {run.task_type}")

    def _execute_noop(self, payload: dict[str, Any]) -> MacWorkerExecutionResult:
        message = str(payload.get("message", "noop completed")).strip() or "noop completed"
        return MacWorkerExecutionResult(
            message=message,
            result={"echo": message},
            metrics={"operations": 1},
        )

    def _execute_cleanup_appledouble(self, payload: dict[str, Any]) -> MacWorkerExecutionResult:
        root_path = self._resolve_root_path(payload)
        recursive = bool(payload.get("recursive", True))
        dry_run = self._resolve_dry_run(payload)
        deleted_files = AppleDoubleCleaner.clean(
            directory=str(root_path),
            recursive=recursive,
            dry_run=dry_run,
        )
        return MacWorkerExecutionResult(
            message="cleanup_appledouble finished",
            result={
                "task_type": WorkerTaskType.CLEANUP_APPLEDOUBLE.value,
                "root_path": str(root_path),
                "dry_run": dry_run,
                "deleted_count": len(deleted_files),
                "deleted_paths": deleted_files[:100],
            },
            metrics={"files_scanned_or_matched": len(deleted_files)},
        )

    def _execute_cleanup_tmp(self, payload: dict[str, Any]) -> MacWorkerExecutionResult:
        root_path = self._resolve_root_path(payload)
        self._assert_safe_cleanup_root(root_path)
        older_than_hours = max(0, int(payload.get("older_than_hours", 24)))
        dry_run = self._resolve_dry_run(payload)
        cutoff = utc_now() - timedelta(hours=older_than_hours)

        matched_paths: list[str] = []
        removed_paths: list[str] = []
        scanned_entries = 0

        if root_path.exists():
            paths = sorted(root_path.rglob("*"), key=lambda item: (len(item.parts), str(item)), reverse=True)
            for candidate in paths:
                scanned_entries += 1
                try:
                    modified_at = datetime.fromtimestamp(candidate.stat().st_mtime, tz=cutoff.tzinfo)
                except OSError:
                    continue
                if modified_at > cutoff:
                    continue
                if candidate.is_dir():
                    if any(candidate.iterdir()):
                        continue
                    matched_paths.append(str(candidate))
                    if not dry_run:
                        candidate.rmdir()
                    removed_paths.append(str(candidate))
                    continue
                matched_paths.append(str(candidate))
                if not dry_run:
                    if candidate.is_symlink() or candidate.is_file():
                        candidate.unlink()
                removed_paths.append(str(candidate))

        return MacWorkerExecutionResult(
            message="cleanup_tmp finished",
            result={
                "task_type": WorkerTaskType.CLEANUP_TMP.value,
                "root_path": str(root_path),
                "dry_run": dry_run,
                "matched_count": len(matched_paths),
                "deleted_count": len(removed_paths),
                "deleted_paths": removed_paths[:100],
                "older_than_hours": older_than_hours,
            },
            metrics={"entries_scanned": scanned_entries},
        )

    def _execute_youtube_action(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        outcome = self._get_youtube_bridge().execute_payload(
            run.payload,
            queue_requested_by=run.requested_by,
            queue_metadata=run.metadata,
        )
        return MacWorkerExecutionResult(
            message=outcome.reason or f"youtube {outcome.action} {outcome.status.value}",
            status=outcome.status,
            error=outcome.reason if outcome.status == JobStatus.FAILED else None,
            result=outcome.model_dump(mode="json"),
            metrics={"success": int(outcome.success)},
        )

    def _execute_claude_runtime(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        runtime = self._claude_runtime
        if runtime is None:
            return MacWorkerExecutionResult(
                message="claude_runtime not available",
                status=JobStatus.FAILED,
                error="ClaudeRuntimeService not configured on this worker",
            )
        outcome = runtime.execute_payload(
            run.payload,
            worker_id=run.assigned_worker_id,
            queue_metadata=run.metadata,
        )
        return MacWorkerExecutionResult(
            message=outcome.message,
            status=outcome.status,
            error=outcome.error,
            result={
                **outcome.result,
                "agent_run_id": outcome.agent_run_id,
            },
            metrics=outcome.metrics,
        )

    def _execute_youtube_autoflow(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        outcome = self._get_youtube_autoflow().execute_payload(
            run.payload,
            queue_requested_by=run.requested_by,
            queue_metadata=run.metadata,
        )
        return MacWorkerExecutionResult(
            message=outcome.reason or f"youtube autoflow {outcome.status.value}",
            status=outcome.status,
            error=outcome.reason if outcome.status == JobStatus.FAILED else None,
            result=outcome.model_dump(mode="json"),
            metrics={"success": int(outcome.success)},
        )

    def _get_youtube_bridge(self) -> StandbyYouTubeBridgeService:
        if self._youtube_bridge is None:
            self._youtube_bridge = build_default_standby_youtube_bridge_service()
        return self._youtube_bridge

    def _get_youtube_autoflow(self) -> StandbyYouTubeAutoflowService:
        if self._youtube_autoflow is None:
            self._youtube_autoflow = build_default_standby_youtube_autoflow_service()
        return self._youtube_autoflow

    def _resolve_root_path(self, payload: dict[str, Any]) -> Path:
        raw = payload.get("root_path")
        if raw is None:
            return self._config.housekeeping_root
        return Path(str(raw)).expanduser().resolve()

    def _resolve_dry_run(self, payload: dict[str, Any]) -> bool:
        value = payload.get("dry_run")
        if value is None:
            return self._config.dry_run
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _assert_safe_cleanup_root(root_path: Path) -> None:
        unsafe_roots = {
            Path("/"),
            Path("/Users"),
            Path("/Volumes"),
            Path("/private"),
            Path("/System"),
            Path("/tmp"),
            Path("/var"),
            Path.home(),
        }
        resolved = root_path.resolve()
        if resolved in unsafe_roots:
            raise ValueError(f"Refusing to clean unsafe root path: {resolved}")
        if len(resolved.parts) < 3:
            raise ValueError(f"Refusing to clean shallow root path: {resolved}")
        if not resolved.exists():
            return
        if not resolved.is_dir():
            raise ValueError(f"Cleanup root must be a directory: {resolved}")
