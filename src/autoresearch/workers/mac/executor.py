from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
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
from autoresearch.core.services.github_ops import GitHubOpsService, build_default_github_ops_service
from autoresearch.agent_protocol.runtime_models import RuntimeRunRead
from autoresearch.shared.models import JobStatus, WorkerQueueItemRead, WorkerTaskType, utc_now
from autoresearch.workers.mac.config import MacWorkerConfig
from autoresearch.core.services.worker_runtime_dispatch import WorkerRuntimeDispatchService

_XREACH_BROWSER_NAMES = {"arc", "brave", "chrome", "chromium", "edge", "firefox", "opera", "safari", "vivaldi"}


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
        github_ops: GitHubOpsService | None = None,
        runtime_dispatch: WorkerRuntimeDispatchService | None = None,
        hermes_live_report: Callable[[WorkerQueueItemRead, RuntimeRunRead, int], None] | None = None,
        youtube_live_report: Callable[[WorkerQueueItemRead, str, str, dict[str, Any]], None] | None = None,
        cancel_requested: Callable[[str], bool] | None = None,
    ) -> None:
        self._config = config
        self._youtube_bridge = youtube_bridge
        self._youtube_autoflow = youtube_autoflow
        self._github_ops = github_ops
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
        if run.task_type == WorkerTaskType.SOURCE_COLLECT:
            return self._execute_source_collect(run)
        if run.task_type == WorkerTaskType.YOUTUBE_ACTION:
            return self._execute_youtube_action(run)
        if run.task_type == WorkerTaskType.YOUTUBE_AUTOFLOW:
            return self._execute_youtube_autoflow(run)
        if run.task_type == WorkerTaskType.GITHUB_OPS:
            return self._execute_github_ops(run)
        if run.task_type == WorkerTaskType.CLAUDE_RUNTIME:
            return self._execute_claude_runtime(run)
        if run.task_type == WorkerTaskType.EXCEL_AUDIT:
            return self._execute_excel_audit(run)
        if run.task_type == WorkerTaskType.CONTENT_KB_CLASSIFY:
            return self._execute_content_kb_classify(run)
        if run.task_type == WorkerTaskType.CONTENT_KB_INGEST:
            return self._execute_content_kb_ingest(run)
        if run.task_type == WorkerTaskType.SECURITY_AUDIT:
            return self._execute_security_audit(run)
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

    def _execute_source_collect(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        payload = dict(run.payload or {})
        source_kind = str(payload.get("source_kind") or "bookmarks").strip().lower()
        if source_kind not in {"x_bookmarks", "youtube_transcript", "bookmarks"}:
            return MacWorkerExecutionResult(
                message=f"source_collect unsupported source_kind: {source_kind}",
                status=JobStatus.FAILED,
                error=f"unsupported source_kind: {source_kind}",
                result={
                    "task_type": WorkerTaskType.SOURCE_COLLECT.value,
                    "source_kind": source_kind,
                    "error_kind": "unsupported_source_kind",
                },
            )
        request_text = str(payload.get("request_text") or run.task_name or "").strip()
        collector = str(payload.get("collector") or "xreach").strip().lower() or "xreach"
        if _source_collect_asks_for_new_details(request_text):
            detail_outcome = self._execute_source_collect_new_details(
                run=run,
                payload=payload,
                source_kind=source_kind,
                collector=collector,
                request_text=request_text,
            )
            if detail_outcome is not None:
                return detail_outcome
        try:
            loaded = _load_source_collect_items(payload=payload, source_kind=source_kind)
        except _SourceCollectLoadError as exc:
            if exc.error_kind == "collector_auth_failed":
                user_summary = "X 书签采集需要恢复本机登录态，管家已交给 Hermes 兜底。"
                user_hint = (
                    "Hermes 会给出可继续执行的恢复步骤；完成后点“我已完成，继续采集”。"
                )
                auth_attempts = list(exc.metadata.get("xreach_auth_attempts") or [])
                return MacWorkerExecutionResult(
                    message="source_collect waiting for X auth recovery",
                    status=JobStatus.RUNNING,
                    error=None,
                    result={
                        "task_type": WorkerTaskType.SOURCE_COLLECT.value,
                        "source_kind": source_kind,
                        "collector": exc.collector,
                        "error_kind": "collector_auth_required",
                        "exit_reason": "collector_auth_required",
                        "summary": user_summary,
                        "telegram_hint": user_hint,
                        "collector_error": str(exc),
                        "collector_error_kind": exc.error_kind,
                        "request_text": payload.get("request_text") or "",
                        "xreach_auth_status": "required",
                        "xreach_auth_attempts": auth_attempts,
                        "xreach_auth_next_actions": [
                            "open_login",
                            "resume_after_login",
                            "recheck_auth",
                            "cancel",
                        ],
                    },
                    metrics={
                        "error_kind": "collector_auth_required",
                        "exit_reason": "collector_auth_required",
                        "collector": exc.collector,
                        "worker_pause_reason": "xreach_auth_required",
                        "telegram_notify_status": "deferred",
                        "xreach_auth_status": "required",
                        "xreach_auth_attempt_count": len(auth_attempts),
                        "telegram_display_runtime_id": "source_collect",
                        "telegram_display_primary_agent": "source_collect",
                        "telegram_display_agent_names": ["source_collect", "hermes"],
                    },
                )
            user_summary = _source_collect_failure_summary(exc)
            user_hint = _source_collect_failure_hint(exc)
            return MacWorkerExecutionResult(
                message=f"source_collect failed: {user_summary}",
                status=JobStatus.FAILED,
                error=user_summary,
                result={
                    "task_type": WorkerTaskType.SOURCE_COLLECT.value,
                    "source_kind": source_kind,
                    "collector": exc.collector,
                    "error_kind": exc.error_kind,
                    "exit_reason": exc.error_kind,
                    "summary": user_summary,
                    "telegram_hint": user_hint,
                    "collector_error": str(exc),
                    "request_text": payload.get("request_text") or "",
                },
                metrics={
                    "error_kind": exc.error_kind,
                    "exit_reason": exc.error_kind,
                    "collector": exc.collector,
                    "telegram_notify_status": "failed",
                },
            )
        items = loaded.items
        if not items:
            collector = str(loaded.metadata.get("collector") or "fixture")
            error_kind = "collector_empty" if collector == "xreach" else "fixture_empty"
            return MacWorkerExecutionResult(
                message="source_collect found no items",
                status=JobStatus.FAILED,
                error="source collector returned no collectable items",
                result={
                    "task_type": WorkerTaskType.SOURCE_COLLECT.value,
                    "source_kind": source_kind,
                    "collector": collector,
                    "error_kind": error_kind,
                    "request_text": payload.get("request_text") or "",
                },
            )

        out_dir = self._config.housekeeping_root / "artifacts" / "source_collect" / run.run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = out_dir / "normalized_subtitle.txt"
        metadata_path = out_dir / "metadata.json"
        normalized = _render_source_collect_text(items=items, source_kind=source_kind)
        artifact_path.write_text(normalized, encoding="utf-8")
        source_urls = _source_collect_urls(items, payload)
        collector = str(loaded.metadata.get("collector") or "fixture").strip().lower() or "fixture"
        delta = _source_collect_delta(
            artifact_root=self._config.housekeeping_root / "artifacts" / "source_collect",
            current_run_id=run.run_id,
            source_kind=source_kind,
            collector=collector,
            source_urls=source_urls,
        )
        new_items = _source_collect_items_for_urls(items, delta["new_source_urls"])
        answer = _source_collect_user_answer(
            request_text=request_text,
            source_kind=source_kind,
            item_count=len(items),
            delta=delta,
            new_items=new_items,
        )
        metadata = {
            **loaded.metadata,
            "run_id": run.run_id,
            "source_kind": source_kind,
            "item_count": len(items),
            "source_urls": source_urls,
            "artifact_path": str(artifact_path),
            "request_text": request_text,
            "answer": answer,
            "new_items": new_items,
            **delta,
        }
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        title = str(payload.get("title") or "Collected source artifact").strip()
        content_kb_payload = {
            "subtitle_text_path": str(artifact_path),
            "title": title,
            "topic": str(payload.get("topic") or "").strip(),
            "source_url": str(payload.get("source_url") or (source_urls[0] if source_urls else "")).strip(),
            "speakers": [],
            "created_at": "",
            "owner": str(payload.get("owner") or "knowledge-base").strip() or "knowledge-base",
            "default_repo": str(payload.get("default_repo") or "knowledge-base").strip() or "knowledge-base",
            "open_draft_pr": bool(payload.get("open_draft_pr")),
            "request_text": request_text,
            "source_collect_run_id": run.run_id,
            "source_kind": source_kind,
            "source_collect_answer": answer,
            "source_collect_item_count": len(items),
            "source_collect_previous_item_count": delta["previous_item_count"],
            "source_collect_known_item_count": delta["known_item_count"],
            "source_collect_new_item_count": delta["new_item_count"],
            "source_collect_has_new_items": delta["has_new_items"],
            "source_collect_new_source_urls": delta["new_source_urls"],
            "source_collect_new_items": new_items,
            "source_collect_previous_run_id": delta["previous_source_collect_run_id"],
        }
        new_count = delta["new_item_count"]
        if delta["previous_source_collect_run_id"]:
            summary = f"Collected {len(items)} item(s); {new_count} new since previous collection."
        else:
            summary = f"Collected {len(items)} item(s); no previous collection found."
        return MacWorkerExecutionResult(
            message=f"source_collect: {source_kind} → local artifact",
            result={
                "artifact_path": str(artifact_path),
                "artifact_type": "text",
                "metadata_path": str(metadata_path),
                "source_kind": source_kind,
                "collector": collector,
                "item_count": len(items),
                "source_urls": source_urls,
                "previous_source_collect_run_id": delta["previous_source_collect_run_id"],
                "previous_item_count": delta["previous_item_count"],
                "known_item_count": delta["known_item_count"],
                "new_item_count": new_count,
                "has_new_items": delta["has_new_items"],
                "new_source_urls": delta["new_source_urls"],
                "new_items": new_items,
                "answer": answer,
                "content_kb_payload": content_kb_payload,
                "summary": summary,
            },
            metrics={
                "items_collected": len(items),
                "new_items_collected": new_count,
                "known_items_collected": delta["known_item_count"],
                "telegram_notify_status": "deferred",
                "defer_completion_until": WorkerTaskType.CONTENT_KB_INGEST.value,
            },
        )

    def _execute_source_collect_new_details(
        self,
        *,
        run: WorkerQueueItemRead,
        payload: dict[str, Any],
        source_kind: str,
        collector: str,
        request_text: str,
    ) -> MacWorkerExecutionResult | None:
        context = _latest_source_collect_new_detail_context(
            artifact_root=self._config.housekeeping_root / "artifacts" / "source_collect",
            current_run_id=run.run_id,
            source_kind=source_kind,
            collector=collector,
        )
        if context is None:
            return None

        out_dir = self._config.housekeeping_root / "artifacts" / "source_collect" / run.run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = out_dir / "normalized_subtitle.txt"
        metadata_path = out_dir / "metadata.json"
        detail_items = context["new_items"]
        normalized = _render_source_collect_text(items=detail_items, source_kind=source_kind)
        artifact_path.write_text(normalized, encoding="utf-8")

        source_urls = _source_collect_urls(detail_items, payload)
        answer = _source_collect_details_answer(source_kind=source_kind, items=detail_items, context=context)
        previous_run_id = str(context.get("previous_source_collect_run_id") or "")
        source_run_id = str(context.get("source_collect_run_id") or "")
        item_count = _metadata_int(context.get("item_count"))
        new_count = len(detail_items)
        metadata = {
            "collector": "context_lookup",
            "context_collector": collector,
            "source_kind": source_kind,
            "run_id": run.run_id,
            "source_collect_run_id": source_run_id,
            "source_collect_context_run_id": source_run_id,
            "previous_source_collect_run_id": previous_run_id,
            "previous_item_count": _metadata_int(context.get("previous_item_count")),
            "item_count": item_count,
            "known_item_count": max(0, item_count - new_count),
            "new_item_count": new_count,
            "has_new_items": bool(detail_items),
            "source_urls": source_urls,
            "new_source_urls": source_urls,
            "new_items": detail_items,
            "artifact_path": str(artifact_path),
            "request_text": request_text,
            "answer": answer,
            "detail_lookup": True,
        }
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        title = str(payload.get("title") or request_text or "X bookmark detail lookup").strip()
        content_kb_payload = {
            "subtitle_text_path": str(artifact_path),
            "title": title,
            "topic": str(payload.get("topic") or "").strip(),
            "source_url": source_urls[0] if source_urls else "",
            "speakers": [],
            "created_at": "",
            "owner": str(payload.get("owner") or "knowledge-base").strip() or "knowledge-base",
            "default_repo": str(payload.get("default_repo") or "knowledge-base").strip() or "knowledge-base",
            "open_draft_pr": bool(payload.get("open_draft_pr")),
            "request_text": request_text,
            "source_collect_run_id": run.run_id,
            "source_collect_context_run_id": source_run_id,
            "source_kind": source_kind,
            "source_collect_answer": answer,
            "source_collect_item_count": item_count,
            "source_collect_previous_item_count": _metadata_int(context.get("previous_item_count")),
            "source_collect_known_item_count": max(0, item_count - new_count),
            "source_collect_new_item_count": new_count,
            "source_collect_has_new_items": bool(detail_items),
            "source_collect_new_source_urls": source_urls,
            "source_collect_new_items": detail_items,
            "source_collect_previous_run_id": previous_run_id,
            "source_collect_detail_lookup": True,
        }
        return MacWorkerExecutionResult(
            message=f"source_collect: {source_kind} new bookmark details",
            result={
                "artifact_path": str(artifact_path),
                "artifact_type": "text",
                "metadata_path": str(metadata_path),
                "source_kind": source_kind,
                "collector": "context_lookup",
                "context_collector": collector,
                "source_collect_context_run_id": source_run_id,
                "previous_source_collect_run_id": previous_run_id,
                "item_count": item_count,
                "new_item_count": new_count,
                "known_item_count": max(0, item_count - new_count),
                "has_new_items": bool(detail_items),
                "source_urls": source_urls,
                "new_source_urls": source_urls,
                "new_items": detail_items,
                "answer": answer,
                "content_kb_payload": content_kb_payload,
                "summary": f"Found {new_count} previous new X bookmark detail(s).",
            },
            metrics={
                "items_collected": item_count,
                "new_items_collected": new_count,
                "known_items_collected": max(0, item_count - new_count),
                "source_collect_detail_lookup": True,
                "telegram_notify_status": "deferred",
                "defer_completion_until": WorkerTaskType.CONTENT_KB_INGEST.value,
            },
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
        payload = {
            **dict(run.payload or {}),
            "run_id": run.run_id,
        }
        if run.assigned_worker_id:
            payload["worker_id"] = run.assigned_worker_id
        meta = run.metadata or {}
        live_cb = None
        if (
            self._hermes_live_report is not None
            and meta.get("telegram_completion_via_api")
            and str(payload.get("runtime_id") or "claude").strip().lower() == "hermes"
        ):

            def live_cb_impl(latest: RuntimeRunRead, elapsed_s: int) -> None:
                self._hermes_live_report(run, latest, elapsed_s)  # type: ignore[misc]

            live_cb = live_cb_impl

        outcome = dispatch.execute_payload(
            payload,
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

    def _execute_github_ops(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        from autoresearch.core.services.github_ops import GitHubOpsRequest

        payload = {
            **dict(run.payload or {}),
            "metadata": {
                **dict(run.metadata or {}),
                **dict((run.payload or {}).get("metadata") or {}),
                "run_id": run.run_id,
            },
        }
        outcome = self._get_github_ops().execute(GitHubOpsRequest.model_validate(payload))
        status = JobStatus.COMPLETED if outcome.status in {"completed", "approval_required", "blocked"} else JobStatus.FAILED
        return MacWorkerExecutionResult(
            message=outcome.summary or f"github_ops {outcome.status}",
            status=status,
            error=outcome.reason if outcome.status == "failed" else None,
            result=outcome.model_dump(mode="json"),
            metrics={
                "github_ops_status": outcome.status,
                "approval_policy": outcome.approval_policy,
                "approval_required": int(outcome.status == "approval_required"),
            },
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

        output_dir = self._config.housekeeping_root / "artifacts" / "excel_audit" / run.run_id
        report = run_audit(dsl, job_id=run.run_id, output_dir=output_dir)
        return MacWorkerExecutionResult(
            message=f"excel_audit {report.status}",
            status=JobStatus.COMPLETED if report.status == "completed" else JobStatus.FAILED,
            result={
                "task_type": WorkerTaskType.EXCEL_AUDIT.value,
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
        from content_kb.index_builder import (
            build_speaker_index,
            build_timeline_index,
            build_topic_index,
            write_index_file,
        )
        from content_kb.repo_selector import resolve_repo_selection
        from content_kb.subtitle_ingest import (
            infer_topic_from_subtitle,
            ingest_subtitle,
            normalize_subtitle,
            read_subtitle,
        )

        payload = run.payload
        file_path = payload.get("subtitle_text_path", "")
        if not file_path:
            return MacWorkerExecutionResult(
                message="content_kb_ingest needs a local subtitle_text_path or text file path",
                status=JobStatus.FAILED,
                error="payload.subtitle_text_path is required for content_kb_ingest",
                result={
                    "task_type": WorkerTaskType.CONTENT_KB_INGEST.value,
                    "status": "missing_input_file",
                    "required_field": "subtitle_text_path",
                    "request_text": payload.get("request_text", ""),
                },
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

        artifact_root = (
            self._config.housekeeping_root / "artifacts" / "content_kb" / repo_selection.recommended_repo
        )
        artifact_dir = artifact_root / repo_selection.recommended_directory
        artifact_dir.mkdir(parents=True, exist_ok=True)
        normalized_text = normalize_subtitle(read_subtitle(path))
        normalized_path = artifact_dir / "normalized_subtitle.txt"
        metadata_path = artifact_dir / "metadata.json"
        topic_index_path = artifact_root / "indexes" / "topics.json"
        speaker_index_path = artifact_root / "indexes" / "speakers.json"
        timeline_index_path = artifact_root / "indexes" / "timeline.json"

        normalized_path.write_text(normalized_text, encoding="utf-8")
        source_collect_stats = _source_collect_stats_from_payload(payload)
        metadata_path.write_text(
            json.dumps(
                {
                    "job_id": ingest_result.job_id,
                    "run_id": run.run_id,
                    "source_collect_run_id": payload.get("source_collect_run_id"),
                    "source_kind": payload.get("source_kind"),
                    "source_path": str(path),
                    "title": title,
                    "topic": topic,
                    "repo": repo_selection.recommended_repo,
                    "directory": repo_selection.recommended_directory,
                    "source_url": source_url,
                    "source_collect": source_collect_stats,
                    "metadata": ingest_result.metadata,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        write_index_file(topic_index_path, topic_idx)
        write_index_file(speaker_index_path, speaker_idx)
        write_index_file(timeline_index_path, timeline_idx)

        # 5. Assemble result
        result_data = {
            "job_id": ingest_result.job_id,
            "topic": topic,
            "repo": repo_selection.recommended_repo,
            "directory": repo_selection.recommended_directory,
            "artifact_root": str(artifact_root),
            "artifact_directory": str(artifact_dir),
            "files_written": [str(normalized_path)],
            "metadata_path": str(metadata_path),
            "index_paths": {
                "topic": str(topic_index_path),
                "speaker": str(speaker_index_path),
                "timeline": str(timeline_index_path),
            },
            "indexes": {
                "topic": topic_idx.model_dump(),
                "speaker": speaker_idx.model_dump(),
                "timeline": timeline_idx.model_dump(),
            },
            **source_collect_stats,
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

    def _execute_security_audit(self, run: WorkerQueueItemRead) -> MacWorkerExecutionResult:
        from autoresearch.core.services.security_audit import (
            SecurityAuditQuickScanRequest,
            build_default_security_audit_service,
        )

        service = build_default_security_audit_service(repo_root=self._config.housekeeping_root)
        payload = dict(run.payload or {})
        action = str(payload.get("action") or "quick_scan").strip().lower() or "quick_scan"
        if action in {"daily", "daily_report"}:
            report = service.generate_daily_report()
            failed = report.status == "fail"
            return MacWorkerExecutionResult(
                message=f"security_audit daily {report.status}",
                status=JobStatus.FAILED if failed else JobStatus.COMPLETED,
                error="security daily report failed" if failed else None,
                result=report.model_dump(mode="json"),
                metrics={
                    "security_audit_status": report.status,
                    "findings": len(report.findings),
                },
            )
        if action in {"drift", "drift_check"}:
            report = service.generate_daily_report(write_artifact=False)
            failed = report.status == "fail"
            return MacWorkerExecutionResult(
                message=f"security_audit drift_check {report.status}",
                status=JobStatus.FAILED if failed else JobStatus.COMPLETED,
                error="security drift check failed" if failed else None,
                result=report.model_dump(mode="json"),
                metrics={
                    "security_audit_status": report.status,
                    "findings": len(report.findings),
                },
            )
        if action in {"deep_scan", "prompt_hygiene"}:
            scan = service.run_prompt_hygiene()
            failed = scan.status == "fail"
            return MacWorkerExecutionResult(
                message=scan.summary,
                status=JobStatus.FAILED if failed else JobStatus.COMPLETED,
                error=scan.summary if failed else None,
                result=scan.model_dump(mode="json"),
                metrics={
                    "security_audit_status": scan.status,
                    "findings": len(scan.findings),
                },
            )

        rule_candidate = payload.get("rule_candidate")
        scan = service.quick_scan(
            SecurityAuditQuickScanRequest(
                diff=payload.get("diff") if isinstance(payload.get("diff"), str) else None,
                files=_normalize_security_audit_files(payload.get("files")),
                rule_candidate=rule_candidate if isinstance(rule_candidate, dict) else None,
            )
        )
        failed = scan.status == "fail"
        return MacWorkerExecutionResult(
            message=scan.summary,
            status=JobStatus.FAILED if failed else JobStatus.COMPLETED,
            error=scan.summary if failed else None,
            result=scan.model_dump(mode="json"),
            metrics={
                "security_audit_status": scan.status,
                "findings": len(scan.findings),
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

    def _get_github_ops(self) -> GitHubOpsService:
        if self._github_ops is None:
            self._github_ops = build_default_github_ops_service(repo_root=self._config.housekeeping_root)
        return self._github_ops

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


def _normalize_security_audit_files(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


@dataclass(slots=True)
class _SourceCollectLoadResult:
    items: list[dict[str, Any]]
    metadata: dict[str, Any]


class _SourceCollectLoadError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        error_kind: str,
        collector: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_kind = error_kind
        self.collector = collector
        self.metadata = dict(metadata or {})


def _load_source_collect_items(*, payload: dict[str, Any], source_kind: str) -> _SourceCollectLoadResult:
    fixture_path = str(payload.get("fixture_path") or "").strip()
    if fixture_path:
        path = Path(fixture_path).expanduser()
        if not path.exists():
            raise _SourceCollectLoadError(
                f"source fixture not found: {fixture_path}",
                error_kind="fixture_missing",
                collector="fixture",
            )
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise _SourceCollectLoadError(
                f"source fixture invalid JSON: {fixture_path}",
                error_kind="fixture_invalid_json",
                collector="fixture",
            ) from exc
        try:
            items = _source_collect_items_from_raw(raw, source_kind=source_kind)
        except ValueError as exc:
            raise _SourceCollectLoadError(
                f"source fixture has unsupported shape: {fixture_path}",
                error_kind="fixture_invalid_json",
                collector="fixture",
            ) from exc
        return _SourceCollectLoadResult(
            items=items,
            metadata={
                "collector": "fixture",
                "fixture_path": str(path),
            },
        )
    if source_kind == "x_bookmarks":
        return _load_x_bookmark_items_from_xreach(payload)
    return _SourceCollectLoadResult(
        items=_default_source_collect_items(source_kind),
        metadata={
            "collector": "fixture",
            "fixture_default": True,
        },
    )


def _load_x_bookmark_items_from_xreach(payload: dict[str, Any]) -> _SourceCollectLoadResult:
    collector = str(payload.get("collector") or "xreach").strip() or "xreach"
    if collector != "xreach":
        raise _SourceCollectLoadError(
            f"unsupported source collector: {collector}",
            error_kind="collector_failed",
            collector=collector,
        )
    executable = shutil.which("xreach")
    if executable is None:
        raise _SourceCollectLoadError(
            "xreach collector is not installed or not on PATH",
            error_kind="collector_missing",
            collector="xreach",
        )

    auth_metadata = _prepare_xreach_auth(executable=executable, payload=payload)
    limit = _bounded_int(payload.get("limit"), default=50, minimum=1, maximum=500)
    max_pages = _optional_bounded_int(payload.get("max_pages"), default=1, minimum=1, maximum=100)
    completed = _run_xreach_bookmarks_command(executable=executable, limit=limit, max_pages=max_pages)
    if completed.returncode != 0:
        detail = _redact_xreach_auth_detail(completed.stderr or completed.stdout or "").strip()
        error_kind = _classify_xreach_error_kind(detail)
        if error_kind == "collector_auth_failed":
            refresh_metadata = _prepare_xreach_auth(
                executable=executable,
                payload=payload,
                force_extract=True,
            )
            auth_metadata = _merge_xreach_auth_metadata(auth_metadata, refresh_metadata)
            completed = _run_xreach_bookmarks_command(executable=executable, limit=limit, max_pages=max_pages)
            if completed.returncode == 0:
                auth_metadata = {
                    **auth_metadata,
                    "xreach_auth_status": "recovered",
                    "xreach_auth_retry_after_bookmarks_auth_failed": True,
                }
            else:
                detail = _redact_xreach_auth_detail(completed.stderr or completed.stdout or "").strip()
                error_kind = _classify_xreach_error_kind(detail)
        if completed.returncode != 0:
            raise _SourceCollectLoadError(
                detail[:500] or f"xreach bookmarks exited with code {completed.returncode}",
                error_kind=error_kind,
                collector="xreach",
                metadata=auth_metadata,
            )
    try:
        raw = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise _SourceCollectLoadError(
            "xreach bookmarks returned invalid JSON",
            error_kind="collector_invalid_json",
            collector="xreach",
        ) from exc
    try:
        items = _source_collect_items_from_raw(raw, source_kind="x_bookmarks")
    except ValueError as exc:
        raise _SourceCollectLoadError(
            "xreach bookmarks returned unsupported JSON shape",
            error_kind="collector_invalid_json",
            collector="xreach",
        ) from exc
    return _SourceCollectLoadResult(
        items=items,
        metadata={
            **auth_metadata,
            "collector": "xreach",
            "collector_command": ["xreach", "bookmarks", "--json", "-n", str(limit)]
            + ([] if max_pages is None else ["--max-pages", str(max_pages)]),
            "limit": limit,
            "max_pages": max_pages,
        },
    )


def _run_xreach_bookmarks_command(
    *,
    executable: str,
    limit: int,
    max_pages: int | None,
) -> subprocess.CompletedProcess[str]:
    command = [executable, "bookmarks", "--json", "-n", str(limit)]
    if max_pages is not None:
        command.extend(["--max-pages", str(max_pages)])
    try:
        return subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=90,
        )
    except FileNotFoundError as exc:
        raise _SourceCollectLoadError(
            "xreach collector is not installed or not on PATH",
            error_kind="collector_missing",
            collector="xreach",
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise _SourceCollectLoadError(
            "xreach bookmarks timed out",
            error_kind="collector_failed",
            collector="xreach",
        ) from exc


def _prepare_xreach_auth(
    *,
    executable: str,
    payload: dict[str, Any],
    force_extract: bool = False,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    check = _run_xreach_command(executable, ["auth", "check"], timeout=20)
    attempts.append(_xreach_attempt("auth check", check))
    if check.returncode == 0 and not force_extract:
        return {"xreach_auth_status": "ok", "xreach_auth_attempts": attempts}

    browsers = _run_xreach_command(executable, ["auth", "browsers"], timeout=20)
    attempts.append(_xreach_attempt("auth browsers", browsers))
    candidates = _xreach_auth_extract_candidates(payload=payload, browsers_output=browsers.stdout)
    for browser, profile in candidates:
        extract = _run_xreach_command(
            executable,
            ["auth", "extract", "--browser", browser, "--profile", profile],
            timeout=45,
        )
        attempts.append(_xreach_attempt(f"auth extract {browser}/{profile}", extract))
        if extract.returncode != 0:
            continue
        recheck = _run_xreach_command(executable, ["auth", "check"], timeout=20)
        attempts.append(_xreach_attempt("auth check after extract", recheck))
        if recheck.returncode == 0:
            return {"xreach_auth_status": "recovered", "xreach_auth_attempts": attempts}

    if check.returncode == 0:
        return {"xreach_auth_status": "ok", "xreach_auth_attempts": attempts}

    detail = _redact_xreach_auth_detail(check.stderr or check.stdout or "").strip()
    raise _SourceCollectLoadError(
        detail[:500] or "xreach authentication is required",
        error_kind="collector_auth_failed",
        collector="xreach",
        metadata={
            "xreach_auth_status": "required",
            "xreach_auth_attempts": attempts,
        },
    )


def _merge_xreach_auth_metadata(*metadata_items: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    attempts: list[dict[str, Any]] = []
    for metadata in metadata_items:
        merged.update(metadata)
        raw_attempts = metadata.get("xreach_auth_attempts")
        if isinstance(raw_attempts, list):
            attempts.extend(item for item in raw_attempts if isinstance(item, dict))
    if attempts:
        merged["xreach_auth_attempts"] = attempts
    return merged


def _run_xreach_command(executable: str, args: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [executable, *args],
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            [executable, *args],
            returncode=124,
            stdout=exc.stdout or "",
            stderr=exc.stderr or "xreach command timed out",
        )


def _xreach_attempt(label: str, completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    safe_label = _redact_xreach_auth_detail(label).strip()
    detail = _redact_xreach_auth_detail(completed.stderr or completed.stdout or "").strip()
    return {
        "step": safe_label,
        "returncode": completed.returncode,
        "detail": detail[:300],
    }


def _redact_xreach_auth_detail(value: str) -> str:
    redacted = re.sub(
        r"(?i)\b(auth[-_ ]?token|ct0|cookie|authorization)\s*[:=]\s*\S+",
        r"\1: <redacted>",
        value,
    )
    return re.sub(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+", "Bearer <redacted>", redacted)


def _xreach_auth_extract_candidates(
    *,
    payload: dict[str, Any],
    browsers_output: str,
) -> list[tuple[str, str]]:
    configured_browser = str(
        payload.get("xreach_auth_browser")
        or os.getenv("XREACH_AUTH_BROWSER")
        or ""
    ).strip()
    configured_profile = str(
        payload.get("xreach_auth_profile")
        or os.getenv("XREACH_AUTH_PROFILE")
        or ""
    ).strip()
    candidates: list[tuple[str, str]] = []
    if configured_browser:
        candidates.append((configured_browser, configured_profile or "Default"))
    candidates.extend(
        [
            ("chrome", "Default"),
            ("arc", "Default"),
            ("safari", "Default"),
            ("edge", "Default"),
        ]
    )
    for line in browsers_output.splitlines():
        browser, profile = _parse_xreach_browser_candidate(line)
        if browser:
            candidates.append((browser, profile or "Default"))
    return _dedupe_xreach_candidates(candidates)


def _parse_xreach_browser_candidate(line: str) -> tuple[str, str]:
    text = line.strip()
    if not text:
        return "", ""
    parts = [part.strip(" -:\t") for part in re.split(r"[,|]", text) if part.strip(" -:\t")]
    browser = ""
    profile = ""
    for part in parts:
        lowered = part.lower()
        if lowered.startswith("browser"):
            browser = part.split("=", 1)[-1].split(":", 1)[-1].strip()
        elif lowered.startswith("profile"):
            profile = part.split("=", 1)[-1].split(":", 1)[-1].strip()
    if browser and browser.lower() in _XREACH_BROWSER_NAMES:
        return browser.lower(), profile or "Default"
    tokens = text.split()
    if tokens and tokens[0].lower() in _XREACH_BROWSER_NAMES:
        return tokens[0].lower(), " ".join(tokens[1:]).strip() or "Default"
    return "", ""


def _dedupe_xreach_candidates(candidates: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[tuple[str, str]] = []
    for browser, profile in candidates:
        key = (browser.strip().lower(), profile.strip() or "Default")
        if not key[0] or key in seen:
            continue
        seen.add(key)
        deduped.append(key)
    return deduped[:8]


def _source_collect_items_from_raw(raw: Any, *, source_kind: str) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        for key in ("items", "bookmarks", "transcripts", "entries"):
            value = raw.get(key)
            if isinstance(value, list):
                return [
                    _normalize_source_collect_item(item, source_kind=source_kind, index=index)
                    for index, item in enumerate(value, start=1)
                    if isinstance(item, dict)
                ]
        return [_normalize_source_collect_item(raw, source_kind=source_kind, index=1)]
    if isinstance(raw, list):
        return [
            _normalize_source_collect_item(item, source_kind=source_kind, index=index)
            for index, item in enumerate(raw, start=1)
            if isinstance(item, dict)
        ]
    raise ValueError("source fixture must be a JSON object or list")


def _classify_xreach_error_kind(detail: str) -> str:
    normalized = detail.strip().lower()
    if any(
        token in normalized
        for token in (
            "could not authenticate",
            "unauthorized",
            "authentication",
            "not authenticated",
            "not logged in",
            "login required",
        )
    ):
        return "collector_auth_failed"
    return "collector_failed"


def _source_collect_failure_summary(exc: _SourceCollectLoadError) -> str:
    if exc.error_kind == "collector_auth_failed":
        return "X 书签采集器 xreach 鉴权失败，无法读取书签。"
    if exc.error_kind == "collector_missing":
        return "未找到 X 书签采集器 xreach。"
    if exc.error_kind == "collector_invalid_json":
        return "X 书签采集器返回了无法解析的数据。"
    if exc.error_kind == "collector_failed":
        return "X 书签采集器执行失败。"
    return str(exc).strip() or "source_collect failed"


def _source_collect_failure_hint(exc: _SourceCollectLoadError) -> str:
    if exc.error_kind == "collector_auth_failed":
        return "请在本机重新完成 xreach 登录后重试；如果只想验证链路，可先传 fixture_path 做离线 smoke。"
    if exc.error_kind == "collector_missing":
        return "请先安装 xreach 并确认 worker 进程的 PATH 能找到它；离线测试可传 fixture_path。"
    if exc.error_kind == "collector_invalid_json":
        return "请确认 xreach bookmarks --json 输出为 JSON；离线测试可传 fixture_path。"
    return "请查看 collector_error 获取采集器原始错误；离线测试可传 fixture_path。"


def _default_source_collect_items(source_kind: str) -> list[dict[str, Any]]:
    if source_kind == "youtube_transcript":
        return [
            {
                "title": "Local YouTube transcript fixture",
                "url": "fixture://youtube/local-transcript",
                "text": "AI 与 GPT 模型正在快速发展，本地字幕 fixture 用于验证知识库入库闭环。",
            }
        ]
    return [
        {
            "title": "Local X bookmark fixture",
            "url": "fixture://x/bookmarks/local-001",
            "text": "AI agents, GPT 模型与本地自动化工作流正在快速发展，适合整理进知识库。",
        },
        {
            "title": "Knowledge workflow note",
            "url": "fixture://x/bookmarks/local-002",
            "text": "Bookmark collection should first create a local artifact, then hand it to content_kb_ingest.",
        },
    ]


def _render_source_collect_text(*, items: list[dict[str, Any]], source_kind: str) -> str:
    lines = [f"# source_collect {source_kind}", ""]
    for index, item in enumerate(items, start=1):
        title = str(item.get("title") or f"Item {index}").strip()
        url = str(item.get("url") or item.get("source_url") or "").strip()
        author = str(item.get("author") or "").strip()
        created_at = str(item.get("created_at") or "").strip()
        text = str(item.get("text") or item.get("content") or item.get("body") or "").strip()
        lines.append(f"## {index}. {title}")
        if url:
            lines.append(f"Source: {url}")
        if author:
            lines.append(f"Author: {author}")
        if created_at:
            lines.append(f"Created: {created_at}")
        if text:
            lines.append(text)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _source_collect_urls(items: list[dict[str, Any]], payload: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for raw in payload.get("source_urls") or []:
        text = str(raw).strip()
        if text:
            urls.append(text)
    source_url = str(payload.get("source_url") or "").strip()
    if source_url:
        urls.append(source_url)
    for item in items:
        text = str(item.get("url") or item.get("source_url") or "").strip()
        if text:
            urls.append(text)
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def _source_collect_delta(
    *,
    artifact_root: Path,
    current_run_id: str,
    source_kind: str,
    collector: str,
    source_urls: list[str],
) -> dict[str, Any]:
    previous = _latest_source_collect_metadata(
        artifact_root=artifact_root,
        current_run_id=current_run_id,
        source_kind=source_kind,
        collector=collector,
    )
    previous_urls = _metadata_url_list(previous.get("source_urls") if previous else None)
    previous_seen = set(previous_urls)
    new_urls = [url for url in source_urls if url and url not in previous_seen]
    previous_count = _metadata_int(previous.get("item_count") if previous else None)
    previous_run_id = str(previous.get("run_id") or "") if previous else ""
    known_count = max(0, len(source_urls) - len(new_urls)) if previous else 0
    return {
        "previous_source_collect_run_id": previous_run_id,
        "previous_item_count": previous_count,
        "known_item_count": known_count,
        "new_item_count": len(new_urls) if previous else len(source_urls),
        "has_new_items": bool(new_urls) if previous else bool(source_urls),
        "new_source_urls": new_urls if previous else list(source_urls),
    }


def _latest_source_collect_new_detail_context(
    *,
    artifact_root: Path,
    current_run_id: str,
    source_kind: str,
    collector: str,
) -> dict[str, Any] | None:
    if not artifact_root.exists():
        return None
    candidates: list[tuple[float, str, dict[str, Any]]] = []
    normalized_collector = collector.strip().lower()
    for path in artifact_root.glob("run_*/metadata.json"):
        run_id = path.parent.name
        if run_id == current_run_id:
            continue
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("source_kind") or "").strip().lower() != source_kind:
            continue
        if str(metadata.get("collector") or "").strip().lower() != normalized_collector:
            continue
        new_urls = _metadata_url_list(metadata.get("new_source_urls"))
        if not new_urls:
            continue
        candidates.append((path.stat().st_mtime, run_id, {"run_id": run_id, **metadata}))
    if not candidates:
        return None
    _, run_id, metadata = max(candidates, key=lambda item: (item[0], item[1]))
    items = _source_collect_new_items_from_metadata(metadata)
    if not items:
        items = _source_collect_items_for_urls(
            _source_collect_items_from_artifact(metadata.get("artifact_path")),
            _metadata_url_list(metadata.get("new_source_urls")),
        )
    if not items:
        return None
    return {
        **metadata,
        "source_collect_run_id": run_id,
        "new_items": items,
    }


def _latest_source_collect_metadata(
    *,
    artifact_root: Path,
    current_run_id: str,
    source_kind: str,
    collector: str,
) -> dict[str, Any] | None:
    if not artifact_root.exists():
        return None
    candidates: list[tuple[float, str, dict[str, Any]]] = []
    normalized_collector = collector.strip().lower()
    for path in artifact_root.glob("run_*/metadata.json"):
        run_id = path.parent.name
        if run_id == current_run_id:
            continue
        try:
            metadata = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(metadata, dict):
            continue
        if str(metadata.get("source_kind") or "").strip().lower() != source_kind:
            continue
        candidate_collector = str(metadata.get("collector") or "").strip().lower()
        if normalized_collector and candidate_collector != normalized_collector:
            continue
        if normalized_collector != "fixture" and (
            candidate_collector == "fixture" or _metadata_url_list(metadata.get("source_urls")) == []
        ):
            continue
        candidates.append((path.stat().st_mtime, run_id, metadata))
    if not candidates:
        return None
    _, run_id, metadata = max(candidates, key=lambda item: (item[0], item[1]))
    return {"run_id": run_id, **metadata}


def _source_collect_new_items_from_metadata(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    raw = metadata.get("new_items")
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        items.append(_normalize_source_collect_item(item, source_kind=str(metadata.get("source_kind") or ""), index=index))
    return items


def _source_collect_items_from_artifact(value: Any) -> list[dict[str, Any]]:
    path = Path(str(value or "")).expanduser()
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    items: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    body_lines: list[str] = []

    def flush() -> None:
        nonlocal current, body_lines
        if current is None:
            return
        body = "\n".join(line for line in body_lines if line.strip()).strip()
        if body:
            current["text"] = body
        items.append(current)
        current = None
        body_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            flush()
            title = stripped.split(".", 1)[-1].strip() if "." in stripped else stripped[3:].strip()
            current = {"title": title}
            body_lines = []
            continue
        if current is None:
            continue
        if stripped.startswith("Source:"):
            current["url"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Author:"):
            current["author"] = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("Created:"):
            current["created_at"] = stripped.split(":", 1)[1].strip()
        elif stripped and not stripped.startswith("#"):
            body_lines.append(line)
    flush()
    return items


def _source_collect_items_for_urls(items: list[dict[str, Any]], urls: list[str]) -> list[dict[str, Any]]:
    wanted = set(urls)
    if not wanted:
        return []
    matched: list[dict[str, Any]] = []
    for item in items:
        url = str(item.get("url") or item.get("source_url") or "").strip()
        if url in wanted:
            matched.append(item)
    return matched


def _metadata_url_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    urls: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        urls.append(text)
        seen.add(text)
    return urls


def _metadata_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _source_collect_user_answer(
    *,
    request_text: str,
    source_kind: str,
    item_count: int,
    delta: dict[str, Any],
    new_items: list[dict[str, Any]],
) -> str:
    label_zh = "X 书签" if source_kind == "x_bookmarks" else "资料"
    label_en = "X bookmark(s)" if source_kind == "x_bookmarks" else "source item(s)"
    previous_run_id = str(delta.get("previous_source_collect_run_id") or "").strip()
    new_count = _metadata_int(delta.get("new_item_count"))
    asks_delta = _source_collect_asks_for_delta(request_text)
    if asks_delta and previous_run_id:
        if new_count > 0:
            detail = _source_collect_detail_lines(new_items, max_items=3)
            suffix = f"\n\n新增详情 / New details：\n{detail}" if detail else ""
            return f"有，发现新增 {new_count} 条 {label_zh}。\nYes, found {new_count} new {label_en}.{suffix}"
        return f"没有发现新增 {label_zh}。\nNo new {label_en} found."
    if asks_delta:
        return (
            f"这是首次可比对采集，本次保存 {item_count} 条 {label_zh}作为后续基线。\n"
            f"This is the first comparable collection; saved {item_count} {label_en} as the baseline."
        )
    return f"已采集 {item_count} 条 {label_zh}。\nCollected {item_count} {label_en}."


def _source_collect_details_answer(*, source_kind: str, items: list[dict[str, Any]], context: dict[str, Any]) -> str:
    label_zh = "X 书签" if source_kind == "x_bookmarks" else "资料"
    label_en = "X bookmark(s)" if source_kind == "x_bookmarks" else "source item(s)"
    detail = _source_collect_detail_lines(items, max_items=10)
    source_run_id = str(context.get("source_collect_run_id") or context.get("run_id") or "").strip()
    source_line = f"\n来源运行 / Source run：{source_run_id}" if source_run_id else ""
    if not detail:
        return f"上一轮没有可展示的新增{label_zh}详情。\nNo previous new {label_en} details are available.{source_line}"
    count = len(items)
    return (
        f"上一轮发现新增 {count} 条 {label_zh}，详情如下：\n"
        f"Last run found {count} new {label_en}; details below:{source_line}\n\n"
        f"{detail}"
    )


def _source_collect_detail_lines(items: list[dict[str, Any]], *, max_items: int) -> str:
    lines: list[str] = []
    for index, item in enumerate(items[:max_items], start=1):
        title = str(item.get("title") or f"Item {index}").strip()
        url = str(item.get("url") or item.get("source_url") or "").strip()
        author = str(item.get("author") or "").strip()
        text = str(item.get("text") or item.get("content") or item.get("body") or "").strip()
        label = _source_collect_compact_item_label(title=title, author=author, text=text)
        lines.append(f"{index}. {label}")
        if author:
            lines.append(f"   作者 / Author：{author}")
        if url:
            lines.append(f"   {url}")
        lines.append("")
    return "\n".join(lines).strip()


def _source_collect_compact_item_label(*, title: str, author: str, text: str) -> str:
    clean_title = title.strip()
    if clean_title.lower().startswith("x bookmark by @"):
        clean_title = ""
    prefix = author.strip() or clean_title or "X bookmark"
    summary = _source_collect_compact_text(text, limit=80)
    if summary and summary != prefix:
        return f"{prefix}：{summary}"
    return prefix


def _source_collect_compact_text(text: str, *, limit: int) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(1, limit - 1)].rstrip() + "…"


def _source_collect_asks_for_new_details(request_text: str) -> bool:
    text = request_text.strip().lower()
    if not text:
        return False
    has_new = any(token in request_text for token in ("新增", "新的", "新书签")) or any(
        token in text for token in ("new", "latest")
    )
    asks_detail = any(token in request_text for token in ("详情", "内容", "是什么", "哪条", "哪些", "发了什么")) or any(
        token in text for token in ("detail", "details", "what", "which", "content")
    )
    has_bookmark = any(token in request_text for token in ("书签", "收藏")) or "bookmark" in text
    return has_new and asks_detail and has_bookmark


def _source_collect_asks_for_delta(request_text: str) -> bool:
    text = request_text.strip().lower()
    if not text:
        return False
    zh_tokens = ("上次", "新的", "新增", "新书签", "有没有", "之后", "以后")
    en_tokens = ("new", "since last", "since previous", "after last", "anything new")
    return any(token in request_text for token in zh_tokens) or any(token in text for token in en_tokens)


def _source_collect_stats_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "request_text",
        "source_collect_run_id",
        "source_kind",
        "source_collect_answer",
        "source_collect_item_count",
        "source_collect_previous_item_count",
        "source_collect_known_item_count",
        "source_collect_new_item_count",
        "source_collect_has_new_items",
        "source_collect_new_source_urls",
        "source_collect_new_items",
        "source_collect_context_run_id",
        "source_collect_detail_lookup",
        "source_collect_previous_run_id",
    )
    return {key: payload.get(key) for key in keys if key in payload}


def _normalize_source_collect_item(item: dict[str, Any], *, source_kind: str, index: int) -> dict[str, Any]:
    user = item.get("user") if isinstance(item.get("user"), dict) else {}
    screen_name = _first_text(
        item,
        "screenName",
        "screen_name",
        "username",
        "author_screen_name",
    ) or _first_text(user, "screenName", "screen_name", "username")
    author_name = _first_text(item, "author", "author_name") or _first_text(user, "name", "displayName")
    tweet_id = _first_text(item, "id", "id_str", "tweet_id", "status_id")
    url = _first_text(item, "url", "source_url", "tweet_url", "link")
    if not url and source_kind == "x_bookmarks" and screen_name and tweet_id:
        url = f"https://twitter.com/{screen_name}/status/{tweet_id}"
    text = _first_text(item, "text", "full_text", "content", "body", "summary")
    title = _first_text(item, "title", "name")
    if not title:
        if screen_name:
            title = f"X bookmark by @{screen_name}"
        elif author_name:
            title = f"X bookmark by {author_name}"
        else:
            title = f"Item {index}"
    normalized = dict(item)
    normalized.update(
        {
            "title": title,
            "url": url or "",
            "text": text or "",
            "author": author_name or (f"@{screen_name}" if screen_name else ""),
            "created_at": _first_text(item, "createdAt", "created_at", "date") or "",
        }
    )
    return normalized


def _first_text(mapping: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)


def _optional_bounded_int(value: Any, *, default: int | None, minimum: int, maximum: int) -> int | None:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


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
    suggestions = result.get("metadata", {}).get("publish_suggestions") if isinstance(result.get("metadata"), dict) else None
    if isinstance(suggestions, dict):
        suggested_title = str(suggestions.get("suggested_title") or "").strip()
        suggested_tags = suggestions.get("suggested_tags")
        if suggested_title:
            rows.append(("发布标题 | Publish title", suggested_title))
        if isinstance(suggested_tags, list) and suggested_tags:
            rows.append(("标签 | Tags", ", ".join(str(item) for item in suggested_tags[:8])))
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
