from __future__ import annotations

from collections.abc import Callable
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
from autoresearch.agent_protocol.runtime_models import RuntimeRunRead
from autoresearch.shared.models import JobStatus, WorkerQueueItemRead, WorkerTaskType, utc_now
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.core.services.worker_runtime_dispatch import WorkerRuntimeDispatchService


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
        runtime_dispatch: WorkerRuntimeDispatchService | None = None,
        hermes_live_report: Callable[[WorkerQueueItemRead, RuntimeRunRead, int], None] | None = None,
        youtube_live_report: Callable[[WorkerQueueItemRead, str, str, dict[str, Any]], None] | None = None,
        cancel_requested: Callable[[str], bool] | None = None,
    ) -> None:
        self._config = config
        self._youtube_bridge = youtube_bridge
        self._youtube_autoflow = youtube_autoflow
        self._runtime_dispatch = runtime_dispatch
        self._hermes_live_report = hermes_live_report
        self._youtube_live_report = youtube_live_report
        self._cancel_requested = cancel_requested

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
        if run.task_type == WorkerTaskType.EXCEL_AUDIT:
            return self._execute_excel_audit(run)
        if run.task_type == WorkerTaskType.CONTENT_KB_CLASSIFY:
            return self._execute_content_kb_classify(run)
        if run.task_type == WorkerTaskType.CONTENT_KB_INGEST:
            return self._execute_content_kb_ingest(run)
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
        dispatch = self._runtime_dispatch
        if dispatch is None:
            return MacWorkerExecutionResult(
                message="claude_runtime not available",
                status=JobStatus.FAILED,
                error="WorkerRuntimeDispatchService not configured on this worker",
            )
        meta = run.metadata or {}
        live_cb = None
        if (
            self._hermes_live_report is not None
            and meta.get("telegram_completion_via_api")
            and str(run.payload.get("runtime_id") or "claude").strip().lower() == "hermes"
        ):

            def live_cb_impl(latest: RuntimeRunRead, elapsed_s: int) -> None:
                self._hermes_live_report(run, latest, elapsed_s)  # type: ignore[misc]

            live_cb = live_cb_impl

        outcome = dispatch.execute_payload(
            run.payload,
            worker_id=run.assigned_worker_id,
            queue_metadata=run.metadata,
            hermes_live_progress=live_cb,
            hermes_live_report_interval_seconds=self._config.hermes_live_report_interval_seconds,
            hermes_live_report_on_newline=self._config.hermes_live_report_on_newline,
        )
        return MacWorkerExecutionResult(
            message=outcome.message,
            status=outcome.status,
            error=outcome.error,
            result={
                **outcome.result,
                "agent_run_id": outcome.agent_run_id,
                "stdout_preview": outcome.stdout_preview,
            },
            metrics=outcome.metrics,
        )

    def _execute_youtube_autoflow(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        def progress(stage: str, message: str, metadata: dict[str, Any]) -> None:
            if self._youtube_live_report is not None:
                self._youtube_live_report(run, stage, message, metadata)

        def cancel_requested() -> bool:
            if self._cancel_requested is not None:
                return bool(self._cancel_requested(run.run_id))
            return bool((run.metadata or {}).get("cancel_requested"))

        outcome = self._get_youtube_autoflow().execute_payload(
            run.payload,
            queue_requested_by=run.requested_by,
            queue_metadata=run.metadata,
            progress_callback=progress,
            cancel_requested=cancel_requested,
        )
        result = outcome.model_dump(mode="json")
        result["telegram_completion_card_text"] = _youtube_autoflow_completion_card(
            run=run,
            result=result,
            status=outcome.status,
            message=outcome.reason or f"youtube autoflow {outcome.status.value}",
        )
        metrics = {
            "success": int(outcome.success),
            "telegram_notify_status": "delegated_api",
            "exit_reason": outcome.status.value,
        }
        if outcome.failed_stage:
            metrics["youtube_failed_stage"] = outcome.failed_stage
        if outcome.error_kind:
            metrics["error_kind"] = outcome.error_kind
        return MacWorkerExecutionResult(
            message=outcome.reason or f"youtube autoflow {outcome.status.value}",
            status=outcome.status,
            error=outcome.reason if outcome.status == JobStatus.FAILED else None,
            result=result,
            metrics=metrics,
        )

    def _execute_excel_audit(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        """Delegate to the deterministic excel_audit engine."""
        try:
            from excel_audit.contracts import ExcelAuditRule, RuleDsl, SheetMapping
            from excel_audit.workbook_runner import run_audit
        except ImportError:
            return MacWorkerExecutionResult(
                message="excel_audit not available",
                status=JobStatus.FAILED,
                error="excel_audit module not installed",
            )

        payload = run.payload
        source_files = payload.get("source_files", [])
        rules_raw = payload.get("rules", [])
        mapping_raw = payload.get("sheet_mapping", {})

        rules = [
            ExcelAuditRule(
                id=r.get("id", f"r{i}"),
                name=r.get("name", f"rule_{i}"),
                when=r.get("when", ""),
                formula=r.get("formula", ""),
            )
            for i, r in enumerate(rules_raw)
        ]

        mapping = SheetMapping(
            source=mapping_raw.get("source", ""),
            target=mapping_raw.get("target", ""),
            key_column=mapping_raw.get("key_column", ""),
        )

        dsl = RuleDsl(
            inputs={"source_files": source_files},
            sheet_mapping=mapping,
            rules=rules,
            outputs=payload.get("outputs", {}),
        )

        report = run_audit(dsl, job_id=run.run_id)
        return MacWorkerExecutionResult(
            message=f"excel_audit {report.status}",
            status=JobStatus.COMPLETED if report.status == "completed" else JobStatus.FAILED,
            result={
                "rows_checked": report.result.rows_checked,
                "rows_mismatched": report.result.rows_mismatched,
                "mismatch_amount_total": report.result.mismatch_amount_total,
                "artifacts": report.artifacts,
            },
            metrics={"findings": len(report.result.findings)},
        )

    def _execute_content_kb_classify(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        """Delegate to content_kb topic classifier."""
        from content_kb.topic_classifier import classify_by_keywords

        text = run.payload.get("text", "")
        if not text:
            return MacWorkerExecutionResult(
                message="content_kb_classify skipped: no text provided",
                status=JobStatus.FAILED,
                error="payload.text is required",
            )
        result = classify_by_keywords(text)
        return MacWorkerExecutionResult(
            message=f"content_kb_classify: {result.primary_topic}",
            result={
                "primary_topic": result.primary_topic,
                "confidence": result.confidence,
                "alternatives": [
                    {"topic": a.topic, "confidence": a.confidence}
                    for a in result.alternatives
                ],
            },
        )

    def _execute_content_kb_ingest(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        """Full ingest pipeline: subtitle read → normalize → classify → index build.

        Optionally signals a draft PR should be opened via result metadata.
        The actual PR creation is a downstream concern (github_assistant or DAG).
        """
        from content_kb.contracts import SpeakerIndex, TimelineIndex, TopicIndex
        from content_kb.index_builder import build_speaker_index, build_timeline_index, build_topic_index
        from content_kb.repo_selector import resolve_repo_selection
        from content_kb.subtitle_ingest import infer_topic_from_subtitle, ingest_subtitle

        payload = run.payload
        file_path = payload.get("subtitle_text_path", "")
        if not file_path:
            return MacWorkerExecutionResult(
                message="content_kb_ingest skipped: no subtitle_text_path",
                status=JobStatus.FAILED,
                error="payload.subtitle_text_path is required",
            )

        path = Path(file_path)
        if not path.exists():
            return MacWorkerExecutionResult(
                message=f"content_kb_ingest skipped: file not found: {file_path}",
                status=JobStatus.FAILED,
                error=f"file not found: {file_path}",
            )

        title = payload.get("title", "") or path.stem
        topic = payload.get("topic", "")
        source_url = payload.get("source_url", "")
        owner = payload.get("owner", "knowledge-base")
        default_repo = payload.get("default_repo", "knowledge-base")
        open_draft_pr = payload.get("open_draft_pr", False)

        # 1. Classify if topic not provided
        if not topic:
            topic = infer_topic_from_subtitle(path)

        # 2. Ingest subtitle
        ingest_result = ingest_subtitle(
            file_path=path,
            title=title,
            topic=topic,
            source_url=source_url,
        )

        # 3. Resolve repo/directory
        repo_selection = resolve_repo_selection(owner, default_repo, topic, title)

        # 4. Build indexes from the ingested entry
        entry = {
            "topic": topic,
            "title": title,
            "slug": repo_selection.recommended_directory.split("/")[-1],
            "speaker": payload.get("speakers", []),
            "created_at": payload.get("created_at", ""),
        }
        topic_idx = build_topic_index(None, [entry])
        speaker_idx = build_speaker_index(None, [entry])
        timeline_idx = build_timeline_index(None, [entry])

        # 5. Assemble result
        result_data = {
            "job_id": ingest_result.job_id,
            "topic": topic,
            "repo": repo_selection.recommended_repo,
            "directory": repo_selection.recommended_directory,
            "files_written": ingest_result.files_written,
            "indexes": {
                "topic": topic_idx.model_dump(),
                "speaker": speaker_idx.model_dump(),
                "timeline": timeline_idx.model_dump(),
            },
        }

        # 6. PR callback hook — signal intent for downstream orchestration
        if open_draft_pr:
            result_data["draft_pr_requested"] = True
            result_data["draft_pr_hint"] = {
                "repo": repo_selection.recommended_repo,
                "branch_prefix": "content-kb/ingest",
                "title_prefix": f"docs(content-kb): ingest {title[:60]}",
                "source_path": str(path),
            }

        return MacWorkerExecutionResult(
            message=f"content_kb_ingest: {topic} → {repo_selection.recommended_repo}",
            result=result_data,
            metrics={
                "files_written": len(ingest_result.files_written),
                "indexes_built": 3,
                "draft_pr_requested": int(open_draft_pr),
            },
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


def _youtube_autoflow_completion_card(
    *,
    run: WorkerQueueItemRead,
    result: dict[str, Any],
    status: JobStatus,
    message: str,
) -> str:
    rows = [
        ("任务", run.task_name or run.task_type.value),
        ("run_id", run.run_id),
        ("状态", status.value),
    ]
    for key, label in (
        ("source_url", "url"),
        ("video_id", "video_id"),
        ("transcript_id", "transcript_id"),
        ("digest_id", "digest_id"),
        ("repo", "repo"),
        ("pr_url", "pr"),
        ("failed_stage", "failed_stage"),
        ("error_kind", "error_kind"),
    ):
        value = result.get(key)
        if value:
            rows.append((label, str(value)))
    reason = str(result.get("reason") or message or "").strip()
    if reason:
        rows.append(("原因 | Reason", reason[:600]))

    table = ["| 项 | 值 |", "| --- | --- |"]
    for key, value in rows:
        cell = str(value).replace("|", "/").replace("\n", " ").strip()
        table.append(f"| {key} | {cell[:900]} |")

    if status == JobStatus.COMPLETED:
        heading = "YouTube 自动流已完成。 / YouTube autoflow completed."
    elif status == JobStatus.CANCELLED:
        heading = "YouTube 自动流已取消。 / YouTube autoflow cancelled."
    else:
        heading = "YouTube 自动流失败。 / YouTube autoflow failed."

    retry_hint = ""
    if status == JobStatus.FAILED:
        retry_hint = f"\n\n可重试：/retry {run.run_id}\nRetry: /retry {run.run_id}"
    return (heading + "\n\n" + "\n".join(table) + retry_hint)[:3900]
