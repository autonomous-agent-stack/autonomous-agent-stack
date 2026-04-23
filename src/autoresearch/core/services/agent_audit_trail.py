from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any

from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.shared.models import (
    AdminAgentAuditRole,
    AdminAgentAuditTrailDetailRead,
    AdminAgentAuditTrailEntryRead,
    AdminAgentAuditTrailSnapshotRead,
    AdminAgentAuditTrailStatsRead,
    JobStatus,
    utc_now,
)

_MAX_PATCH_CHARS = 120_000
_SUCCESS_STATUSES = {"completed", "ready_for_promotion", "promoted", "succeeded"}
_FAILED_STATUSES = {
    "failed",
    "blocked",
    "interrupted",
    "timed_out",
    "stalled_no_progress",
    "policy_blocked",
    "contract_error",
    "rejected",
}
_PENDING_STATUSES = {"queued", "created", "pending", "dispatching"}
_RUNNING_STATUSES = {"running"}
_REVIEW_STATUSES = {"human_review", "needs_human_review"}


@dataclass(slots=True)
class _AuditEntryContext:
    entry: AdminAgentAuditTrailEntryRead
    input_prompt: str | None = None
    job_spec: dict[str, Any] = field(default_factory=dict)
    worker_spec: dict[str, Any] = field(default_factory=dict)
    controlled_request: dict[str, Any] = field(default_factory=dict)
    patch_text: str = ""
    patch_truncated: bool = False
    error_reason: str | None = None
    traceback: str | None = None
    raw_record: dict[str, Any] = field(default_factory=dict)


class AgentAuditTrailService:
    """Aggregate worker execution footprints into an admin-friendly audit timeline."""

    def __init__(
        self,
        *,
        repo_root: Path,
        planner_service: AutoResearchPlannerService,
        manager_service: ManagerAgentService,
        agent_service: ClaudeAgentService,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._planner_service = planner_service
        self._manager_service = manager_service
        self._agent_service = agent_service

    def snapshot(
        self,
        *,
        limit: int = 20,
        status_filter: str | None = None,
        agent_role: str | None = None,
    ) -> AdminAgentAuditTrailSnapshotRead:
        contexts = self._filter_contexts(
            self._collect_entry_contexts(),
            status_filter=status_filter,
            agent_role=agent_role,
        )
        items = [context.entry for context in contexts[: max(1, limit)]]
        return AdminAgentAuditTrailSnapshotRead(
            items=items,
            stats=self._build_stats(items),
            issued_at=utc_now(),
        )

    def detail(self, entry_id: str) -> AdminAgentAuditTrailDetailRead:
        normalized_entry_id = entry_id.strip()
        if not normalized_entry_id:
            raise KeyError("audit trail entry id is required")
        for context in self._collect_entry_contexts():
            if context.entry.entry_id != normalized_entry_id:
                continue
            return AdminAgentAuditTrailDetailRead(
                entry=context.entry,
                input_prompt=context.input_prompt,
                job_spec=dict(context.job_spec),
                worker_spec=dict(context.worker_spec),
                controlled_request=dict(context.controlled_request),
                patch_text=context.patch_text,
                patch_truncated=context.patch_truncated,
                error_reason=context.error_reason,
                traceback=context.traceback,
                raw_record=dict(context.raw_record),
            )
        raise KeyError(f"audit trail entry not found: {entry_id}")

    def _collect_entry_contexts(self) -> list[_AuditEntryContext]:
        contexts_by_run: dict[str, _AuditEntryContext] = {}
        for context in self._collect_manager_contexts():
            contexts_by_run[context.entry.run_id] = context
        for context in self._collect_planner_contexts():
            contexts_by_run.setdefault(context.entry.run_id, context)
        for context in self._collect_claude_contexts():
            contexts_by_run.setdefault(context.entry.run_id, context)
        for context in self._collect_runtime_contexts():
            existing = contexts_by_run.get(context.entry.run_id)
            if existing is None:
                contexts_by_run[context.entry.run_id] = context
                continue
            contexts_by_run[context.entry.run_id] = self._merge_contexts(
                existing=existing,
                incoming=context,
            )
        return sorted(
            contexts_by_run.values(),
            key=lambda item: item.entry.recorded_at,
            reverse=True,
        )

    def _collect_manager_contexts(self) -> list[_AuditEntryContext]:
        contexts: list[_AuditEntryContext] = []
        for dispatch in self._manager_service.list_dispatches():
            if dispatch.execution_plan is None:
                continue
            for task in dispatch.execution_plan.tasks:
                run_summary = task.run_summary
                patch_uri = run_summary.promotion_patch_uri if run_summary is not None else None
                patch_text, patch_truncated = self._load_patch_text(patch_uri)
                changed_paths = self._extract_changed_paths(run_summary)
                error_reason = (
                    self._normalize_text(task.error)
                    or self._extract_run_summary_error(run_summary)
                    or self._normalize_text(dispatch.error)
                )
                contexts.append(
                    _AuditEntryContext(
                        entry=AdminAgentAuditTrailEntryRead(
                            entry_id=f"manager:{task.task_id}",
                            source="manager_task",
                            agent_role=AdminAgentAuditRole.MANAGER,
                            run_id=self._extract_task_run_id(task, fallback=task.task_id),
                            agent_id=run_summary.driver_result.agent_id if run_summary is not None else "openhands",
                            title=task.title,
                            status=task.status.value,
                            final_status=run_summary.final_status if run_summary is not None else None,
                            recorded_at=dispatch.updated_at,
                            duration_ms=self._extract_duration_ms(run_summary),
                            first_progress_ms=self._extract_metric(run_summary, "first_progress_ms"),
                            first_scoped_write_ms=self._extract_metric(run_summary, "first_scoped_write_ms"),
                            first_state_heartbeat_ms=self._extract_metric(run_summary, "first_state_heartbeat_ms"),
                            files_changed=len(changed_paths),
                            changed_paths=changed_paths,
                            scope_paths=list(task.worker_spec.allowed_paths) if task.worker_spec is not None else [],
                            patch_uri=patch_uri,
                            summary=task.summary,
                            metadata={
                                "dispatch_id": dispatch.dispatch_id,
                                "intent": dispatch.selected_intent.label if dispatch.selected_intent is not None else None,
                                "stage": task.stage.value,
                                "depends_on": list(task.depends_on),
                            },
                        ),
                        input_prompt=dispatch.prompt,
                        job_spec=self._model_payload(task.agent_job),
                        worker_spec=self._model_payload(task.worker_spec),
                        controlled_request=self._model_payload(task.controlled_request),
                        patch_text=patch_text,
                        patch_truncated=patch_truncated,
                        error_reason=error_reason,
                        traceback=self._multiline_or_none(task.error),
                        raw_record={"manager_dispatch": dispatch.model_dump(mode="json")},
                    )
                )
        return contexts

    def _collect_planner_contexts(self) -> list[_AuditEntryContext]:
        contexts: list[_AuditEntryContext] = []
        for plan in self._planner_service.list():
            run_summary = plan.run_summary
            patch_uri = run_summary.promotion_patch_uri if run_summary is not None else None
            patch_text, patch_truncated = self._load_patch_text(patch_uri)
            changed_paths = self._extract_changed_paths(run_summary)
            title = plan.selected_candidate.title if plan.selected_candidate is not None else plan.goal
            contexts.append(
                _AuditEntryContext(
                    entry=AdminAgentAuditTrailEntryRead(
                        entry_id=f"plan:{plan.plan_id}",
                        source="autoresearch_plan",
                        agent_role=AdminAgentAuditRole.PLANNER,
                        run_id=run_summary.run_id if run_summary is not None else (plan.agent_job.run_id if plan.agent_job else plan.plan_id),
                        agent_id=run_summary.driver_result.agent_id if run_summary is not None else "openhands",
                        title=title,
                        status=plan.dispatch_status.value,
                        final_status=run_summary.final_status if run_summary is not None else None,
                        recorded_at=plan.dispatch_completed_at or plan.updated_at,
                        duration_ms=self._extract_duration_ms(run_summary),
                        first_progress_ms=self._extract_metric(run_summary, "first_progress_ms"),
                        first_scoped_write_ms=self._extract_metric(run_summary, "first_scoped_write_ms"),
                        first_state_heartbeat_ms=self._extract_metric(run_summary, "first_state_heartbeat_ms"),
                        files_changed=len(changed_paths),
                        changed_paths=changed_paths,
                        scope_paths=list(plan.worker_spec.allowed_paths) if plan.worker_spec is not None else [],
                        patch_uri=patch_uri,
                        summary=plan.summary,
                        metadata={
                            "plan_id": plan.plan_id,
                            "candidate_category": (
                                plan.selected_candidate.category if plan.selected_candidate is not None else None
                            ),
                            "source_path": (
                                plan.selected_candidate.source_path if plan.selected_candidate is not None else None
                            ),
                        },
                    ),
                    input_prompt=plan.goal,
                    job_spec=self._model_payload(plan.agent_job),
                    worker_spec=self._model_payload(plan.worker_spec),
                    controlled_request=self._model_payload(plan.controlled_request),
                    patch_text=patch_text,
                    patch_truncated=patch_truncated,
                    error_reason=(
                        self._normalize_text(plan.dispatch_error)
                        or self._normalize_text(plan.error)
                        or self._extract_run_summary_error(run_summary)
                    ),
                    traceback=self._multiline_or_none(plan.error),
                    raw_record={"autoresearch_plan": plan.model_dump(mode="json")},
                )
            )
        return contexts

    def _collect_claude_contexts(self) -> list[_AuditEntryContext]:
        contexts: list[_AuditEntryContext] = []
        for run in self._agent_service.list():
            contexts.append(
                _AuditEntryContext(
                    entry=AdminAgentAuditTrailEntryRead(
                        entry_id=f"claude:{run.agent_run_id}",
                        source="claude_agent",
                        agent_role=AdminAgentAuditRole.WORKER,
                        run_id=run.agent_run_id,
                        agent_id=run.agent_name or "claude_cli",
                        title=run.task_name,
                        status=run.status.value,
                        final_status=(
                            run.status.value
                            if run.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.INTERRUPTED, JobStatus.CANCELLED}
                            else None
                        ),
                        recorded_at=run.updated_at,
                        duration_ms=int(run.duration_seconds * 1000) if run.duration_seconds is not None else None,
                        first_progress_ms=None,
                        first_scoped_write_ms=None,
                        first_state_heartbeat_ms=None,
                        files_changed=0,
                        changed_paths=[],
                        scope_paths=[],
                        patch_uri=self._normalize_text(run.metadata.get("patch_uri")),
                        summary=run.stderr_preview or run.stdout_preview or run.prompt[:160],
                        metadata={"session_id": run.session_id, "parent_agent_id": run.parent_agent_id},
                    ),
                    input_prompt=run.prompt,
                    patch_text=self._load_patch_text(self._normalize_text(run.metadata.get("patch_uri")))[0]
                    if self._normalize_text(run.metadata.get("patch_uri"))
                    else "",
                    patch_truncated=self._load_patch_text(self._normalize_text(run.metadata.get("patch_uri")))[1]
                    if self._normalize_text(run.metadata.get("patch_uri"))
                    else False,
                    error_reason=self._normalize_text(run.error),
                    traceback=self._normalize_text(run.stderr_preview),
                    raw_record={"claude_agent": run.model_dump(mode="json")},
                )
            )
        return contexts

    def _collect_runtime_contexts(self) -> list[_AuditEntryContext]:
        contexts: list[_AuditEntryContext] = []
        for path in self._runtime_summary_files():
            payload = self._load_json(path)
            if not isinstance(payload, dict):
                continue
            run_id = str(payload.get("run_id", "")).strip()
            if not run_id:
                continue
            changed_paths = self._runtime_changed_paths(payload)
            patch_uri = self._runtime_patch_uri(payload)
            patch_text, patch_truncated = self._load_patch_text(patch_uri)
            contexts.append(
                _AuditEntryContext(
                    entry=AdminAgentAuditTrailEntryRead(
                        entry_id=f"runtime:{run_id}",
                        source="runtime_artifact",
                        agent_role=AdminAgentAuditRole.WORKER,
                        run_id=run_id,
                        agent_id=self._runtime_agent_id(payload),
                        title=str(payload.get("task") or payload.get("run_id") or path.parent.name),
                        status=self._runtime_status(payload),
                        final_status=str(payload.get("final_status") or payload.get("status") or "").strip() or None,
                        recorded_at=datetime.fromtimestamp(path.stat().st_mtime, tz=utc_now().tzinfo),
                        duration_ms=self._runtime_duration_ms(payload),
                        first_progress_ms=self._runtime_metric_ms(payload, "first_progress_ms"),
                        first_scoped_write_ms=self._runtime_metric_ms(payload, "first_scoped_write_ms"),
                        first_state_heartbeat_ms=self._runtime_metric_ms(payload, "first_state_heartbeat_ms"),
                        files_changed=self._runtime_files_changed(payload, changed_paths),
                        changed_paths=changed_paths,
                        scope_paths=[],
                        patch_uri=patch_uri,
                        isolated_workspace=str(payload.get("isolated_workspace", "")).strip() or None,
                        summary=self._runtime_summary_text(payload),
                        metadata={"artifact_path": str(path)},
                    ),
                    input_prompt=self._normalize_text(payload.get("task")),
                    job_spec=self._dict_payload(payload.get("job_spec")),
                    worker_spec=self._dict_payload(payload.get("worker_spec")),
                    controlled_request=self._dict_payload(payload.get("controlled_request")),
                    patch_text=patch_text,
                    patch_truncated=patch_truncated,
                    error_reason=self._runtime_error_reason(payload),
                    traceback=self._runtime_traceback(payload),
                    raw_record={"runtime_artifact": payload},
                )
            )
        return contexts

    def _filter_contexts(
        self,
        contexts: list[_AuditEntryContext],
        *,
        status_filter: str | None,
        agent_role: str | None,
    ) -> list[_AuditEntryContext]:
        normalized_status = self._normalize_filter(status_filter)
        normalized_role = self._normalize_filter(agent_role)
        filtered: list[_AuditEntryContext] = []
        for context in contexts:
            if not self._matches_status_filter(context.entry, normalized_status):
                continue
            if not self._matches_role_filter(context.entry, normalized_role):
                continue
            filtered.append(context)
        return filtered

    def _merge_contexts(
        self,
        *,
        existing: _AuditEntryContext,
        incoming: _AuditEntryContext,
    ) -> _AuditEntryContext:
        return _AuditEntryContext(
            entry=existing.entry.model_copy(
                update={
                    "duration_ms": self._prefer_metric(
                        existing.entry.duration_ms,
                        incoming.entry.duration_ms,
                    ),
                    "first_progress_ms": self._prefer_metric(
                        existing.entry.first_progress_ms,
                        incoming.entry.first_progress_ms,
                    ),
                    "first_scoped_write_ms": self._prefer_metric(
                        existing.entry.first_scoped_write_ms,
                        incoming.entry.first_scoped_write_ms,
                    ),
                    "first_state_heartbeat_ms": self._prefer_metric(
                        existing.entry.first_state_heartbeat_ms,
                        incoming.entry.first_state_heartbeat_ms,
                    ),
                    "files_changed": max(existing.entry.files_changed, incoming.entry.files_changed),
                    "changed_paths": existing.entry.changed_paths or incoming.entry.changed_paths,
                    "patch_uri": existing.entry.patch_uri or incoming.entry.patch_uri,
                    "isolated_workspace": existing.entry.isolated_workspace or incoming.entry.isolated_workspace,
                    "summary": existing.entry.summary or incoming.entry.summary,
                    "metadata": {**incoming.entry.metadata, **existing.entry.metadata},
                }
            ),
            input_prompt=existing.input_prompt or incoming.input_prompt,
            job_spec=existing.job_spec or incoming.job_spec,
            worker_spec=existing.worker_spec or incoming.worker_spec,
            controlled_request=existing.controlled_request or incoming.controlled_request,
            patch_text=existing.patch_text or incoming.patch_text,
            patch_truncated=existing.patch_truncated or incoming.patch_truncated,
            error_reason=existing.error_reason or incoming.error_reason,
            traceback=existing.traceback or incoming.traceback,
            raw_record={**incoming.raw_record, **existing.raw_record},
        )

    def _build_stats(self, items: list[AdminAgentAuditTrailEntryRead]) -> AdminAgentAuditTrailStatsRead:
        stats = AdminAgentAuditTrailStatsRead(total=len(items))
        for item in items:
            normalized = self._status_bucket(item)
            if normalized == "success":
                stats.succeeded += 1
            elif normalized == "failed":
                stats.failed += 1
            elif normalized == "running":
                stats.running += 1
            elif normalized == "pending":
                stats.queued += 1
            elif normalized == "review":
                stats.review_required += 1
        return stats

    def _runtime_summary_files(self) -> list[Path]:
        files: list[Path] = []
        for pattern in (
            ".masfactory_runtime/runs/*/summary.json",
            ".masfactory_runtime/smokes/*/artifacts/chain_summary.json",
            "logs/audit/openhands/jobs/*/chain_summary.json",
        ):
            files.extend(self._repo_root.glob(pattern))
        files.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        return files[:80]

    def _load_patch_text(self, patch_uri: str | None) -> tuple[str, bool]:
        patch_path = self._resolve_repo_path(patch_uri)
        if patch_path is None or not patch_path.exists() or not patch_path.is_file():
            return "", False
        try:
            patch_text = patch_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return "", False
        if len(patch_text) <= _MAX_PATCH_CHARS:
            return patch_text, False
        truncated = patch_text[:_MAX_PATCH_CHARS].rstrip()
        return f"{truncated}\n\n... [patch truncated]", True

    def _resolve_repo_path(self, candidate: str | None) -> Path | None:
        normalized = self._normalize_text(candidate)
        if not normalized:
            return None
        path = Path(normalized)
        if path.is_absolute():
            return path
        return (self._repo_root / path).resolve()

    @staticmethod
    def _normalize_filter(value: str | None) -> str | None:
        normalized = str(value or "").strip().lower()
        return None if normalized in {"", "all"} else normalized

    @staticmethod
    def _prefer_metric(primary: int | None, secondary: int | None) -> int | None:
        return primary if primary is not None else secondary

    @staticmethod
    def _matches_role_filter(entry: AdminAgentAuditTrailEntryRead, agent_role: str | None) -> bool:
        if agent_role is None:
            return True
        return entry.agent_role.value == agent_role

    def _matches_status_filter(self, entry: AdminAgentAuditTrailEntryRead, status_filter: str | None) -> bool:
        if status_filter is None:
            return True
        return self._status_bucket(entry) == status_filter

    def _status_bucket(self, entry: AdminAgentAuditTrailEntryRead) -> str:
        normalized = (entry.final_status or entry.status).strip().lower()
        if normalized in _SUCCESS_STATUSES:
            return "success"
        if normalized in _FAILED_STATUSES:
            return "failed"
        if normalized in _RUNNING_STATUSES:
            return "running"
        if normalized in _PENDING_STATUSES:
            return "pending"
        if normalized in _REVIEW_STATUSES:
            return "review"
        return normalized or "pending"

    @staticmethod
    def _extract_task_run_id(task: Any, *, fallback: str) -> str:
        if getattr(task, "run_summary", None) is not None:
            return task.run_summary.run_id
        if getattr(task, "agent_job", None) is not None:
            return task.agent_job.run_id
        return fallback

    @staticmethod
    def _extract_changed_paths(run_summary: Any) -> list[str]:
        if run_summary is None:
            return []
        return list(run_summary.driver_result.changed_paths)

    @staticmethod
    def _extract_duration_ms(run_summary: Any) -> int | None:
        if run_summary is None:
            return None
        return run_summary.driver_result.metrics.duration_ms

    @staticmethod
    def _extract_metric(run_summary: Any, metric_name: str) -> int | None:
        if run_summary is None:
            return None
        value = getattr(run_summary.driver_result.metrics, metric_name, None)
        return int(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def _extract_run_summary_error(run_summary: Any) -> str | None:
        if run_summary is None:
            return None
        return str(run_summary.driver_result.error or "").strip() or None

    @staticmethod
    def _model_payload(model: Any) -> dict[str, Any]:
        if model is None:
            return {}
        if hasattr(model, "model_dump"):
            return model.model_dump(mode="json")
        if isinstance(model, dict):
            return dict(model)
        return {"value": model}

    @staticmethod
    def _dict_payload(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        return {}

    @staticmethod
    def _load_json(path: Path) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return None

    @staticmethod
    def _normalize_text(value: Any) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @staticmethod
    def _multiline_or_none(value: Any) -> str | None:
        normalized = str(value or "").strip()
        if "\n" not in normalized:
            return None
        return normalized

    @staticmethod
    def _runtime_status(payload: dict[str, Any]) -> str:
        if "promotion_ready" in payload:
            return "ready_for_promotion" if bool(payload.get("promotion_ready")) else "failed"
        return str(payload.get("final_status") or payload.get("status") or "unknown")

    @staticmethod
    def _runtime_agent_id(payload: dict[str, Any]) -> str | None:
        driver_result = payload.get("driver_result")
        if isinstance(driver_result, dict):
            agent_id = str(driver_result.get("agent_id", "")).strip()
            if agent_id:
                return agent_id
        return "openhands"

    @staticmethod
    def _runtime_duration_ms(payload: dict[str, Any]) -> int | None:
        return AgentAuditTrailService._runtime_metric_ms(payload, "duration_ms")

    @staticmethod
    def _runtime_metric_ms(payload: dict[str, Any], metric_name: str) -> int | None:
        driver_result = payload.get("driver_result")
        if not isinstance(driver_result, dict):
            return None
        metrics = driver_result.get("metrics")
        if not isinstance(metrics, dict):
            return None
        value = metrics.get(metric_name)
        return int(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def _runtime_changed_paths(payload: dict[str, Any]) -> list[str]:
        promotion = payload.get("promotion")
        if isinstance(promotion, dict):
            changed = promotion.get("changed_files")
            if isinstance(changed, list):
                return [str(item) for item in changed]
        driver_result = payload.get("driver_result")
        if isinstance(driver_result, dict):
            changed = driver_result.get("changed_paths")
            if isinstance(changed, list):
                return [str(item) for item in changed]
        return []

    @staticmethod
    def _runtime_files_changed(payload: dict[str, Any], changed_paths: list[str]) -> int:
        promotion = payload.get("promotion")
        if isinstance(promotion, dict):
            diff_stats = promotion.get("diff_stats")
            if isinstance(diff_stats, dict):
                value = diff_stats.get("files_changed")
                if isinstance(value, (int, float)):
                    return int(value)
        return len(changed_paths)

    @staticmethod
    def _runtime_patch_uri(payload: dict[str, Any]) -> str | None:
        for candidate in (
            payload.get("promotion_patch_uri"),
            (payload.get("artifacts") or {}).get("promotion_patch")
            if isinstance(payload.get("artifacts"), dict)
            else None,
            (payload.get("promotion") or {}).get("patch_uri")
            if isinstance(payload.get("promotion"), dict)
            else None,
        ):
            normalized = str(candidate or "").strip()
            if normalized:
                return normalized
        return None

    @staticmethod
    def _runtime_summary_text(payload: dict[str, Any]) -> str:
        driver_result = payload.get("driver_result")
        if isinstance(driver_result, dict):
            summary = str(driver_result.get("summary", "")).strip()
            if summary:
                return summary
        return str(payload.get("task") or payload.get("status") or "").strip()

    def _runtime_error_reason(self, payload: dict[str, Any]) -> str | None:
        for candidate in (
            payload.get("error"),
            payload.get("detail"),
            (payload.get("driver_result") or {}).get("error")
            if isinstance(payload.get("driver_result"), dict)
            else None,
            self._runtime_status(payload) if self._runtime_status(payload) in _FAILED_STATUSES | _REVIEW_STATUSES else None,
        ):
            normalized = self._normalize_text(candidate)
            if normalized:
                return normalized
        return None

    def _runtime_traceback(self, payload: dict[str, Any]) -> str | None:
        for candidate in (
            payload.get("traceback"),
            payload.get("stderr"),
            (payload.get("driver_result") or {}).get("stderr")
            if isinstance(payload.get("driver_result"), dict)
            else None,
            (payload.get("validation") or {}).get("detail")
            if isinstance(payload.get("validation"), dict)
            else None,
        ):
            normalized = self._normalize_text(candidate)
            if normalized:
                return normalized
        return None
