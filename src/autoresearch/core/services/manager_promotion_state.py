from __future__ import annotations

from dataclasses import dataclass

from autoresearch.agent_protocol.models import RunSummary
from autoresearch.core.services.git_promotion_gate import GitPromotionRead, GitPromotionService
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead
from autoresearch.shared.models import GitPromotionMode, JobStatus, PromotionDiffStats, PromotionResult


@dataclass(frozen=True, slots=True)
class ManagerDispatchPromotionState:
    phase: str
    final_status: str | None
    approval_id: str | None = None
    promotion_id: str | None = None
    promotion_status: str | None = None
    pr_url: str | None = None
    branch_name: str | None = None
    commit_sha: str | None = None
    error: str | None = None
    source: str = "dispatch"
    record: GitPromotionRead | None = None


def manager_dispatch_requests_draft_pr(dispatch: ManagerDispatchRead) -> bool:
    return str(dispatch.metadata.get("pipeline_target") or "").strip().lower() == "draft_pr"


def build_promotion_result_from_record(
    record: GitPromotionRead,
    *,
    run_summary: RunSummary | None = None,
) -> PromotionResult:
    changed_files = _resolve_changed_files(record=record, run_summary=run_summary)
    return PromotionResult(
        run_id=record.run_id,
        success=record.status is JobStatus.COMPLETED,
        mode=_promotion_mode_from_record(record),
        patch_uri=record.patch_path,
        branch_name=record.branch_name,
        commit_sha=record.commit_sha,
        pr_url=record.pr_url,
        base_ref=record.base_ref,
        target_base_branch=record.base_ref,
        changed_files=changed_files,
        diff_stats=PromotionDiffStats(files_changed=len(changed_files)),
        finalized_by=str(record.metadata.get("approved_via") or "promotion_service"),
        created_at=record.created_at,
        updated_at=record.updated_at,
        reason=record.error,
        metadata=dict(record.metadata),
    )


def hydrate_manager_dispatch_promotion(
    dispatch: ManagerDispatchRead,
    *,
    promotion_service: GitPromotionService | None = None,
) -> ManagerDispatchRead:
    record = _resolve_promotion_record(dispatch=dispatch, promotion_service=promotion_service)
    if record is None:
        return dispatch

    metadata_updates = {
        "promotion_id": record.promotion_id,
        "promotion_status": record.status.value,
        "promotion_pr_url": record.pr_url,
        "promotion_branch_name": record.branch_name,
        "promotion_commit_sha": record.commit_sha,
        "promotion_error": record.error,
        "promotion_step_summary": record.metadata.get("step_summary"),
        "promotion_step_trace_file": record.metadata.get("step_trace_file"),
    }
    run_summary = dispatch.run_summary
    if run_summary is not None:
        run_summary = run_summary.model_copy(
            update={
                "promotion": build_promotion_result_from_record(record, run_summary=run_summary),
                "final_status": (
                    "promoted"
                    if record.status is JobStatus.COMPLETED and record.pr_url
                    else run_summary.final_status
                ),
            }
        )
    return dispatch.model_copy(
        update={
            "metadata": {
                **dispatch.metadata,
                **metadata_updates,
            },
            "run_summary": run_summary,
        }
    )


def resolve_manager_dispatch_promotion_state(
    dispatch: ManagerDispatchRead,
    *,
    promotion_service: GitPromotionService | None = None,
) -> ManagerDispatchPromotionState:
    approval_id = str(dispatch.metadata.get("promotion_approval_id") or "").strip() or None
    record = _resolve_promotion_record(dispatch=dispatch, promotion_service=promotion_service)
    if record is not None:
        if record.status is JobStatus.COMPLETED and record.pr_url:
            return ManagerDispatchPromotionState(
                phase="draft_pr_created",
                final_status="promoted",
                approval_id=approval_id,
                promotion_id=record.promotion_id,
                promotion_status=record.status.value,
                pr_url=record.pr_url,
                branch_name=record.branch_name,
                commit_sha=record.commit_sha,
                error=record.error,
                source="promotion_record",
                record=record,
            )
        if record.status is JobStatus.FAILED:
            return ManagerDispatchPromotionState(
                phase="promotion_failed",
                final_status="promotion_failed",
                approval_id=approval_id,
                promotion_id=record.promotion_id,
                promotion_status=record.status.value,
                pr_url=record.pr_url,
                branch_name=record.branch_name,
                commit_sha=record.commit_sha,
                error=record.error,
                source="promotion_record",
                record=record,
            )
        return ManagerDispatchPromotionState(
            phase="promotion_in_progress",
            final_status="promotion_in_progress",
            approval_id=approval_id,
            promotion_id=record.promotion_id,
            promotion_status=record.status.value,
            pr_url=record.pr_url,
            branch_name=record.branch_name,
            commit_sha=record.commit_sha,
            error=record.error,
            source="promotion_record",
            record=record,
        )

    promotion = dispatch.run_summary.promotion if dispatch.run_summary is not None else None
    if promotion is not None and promotion.pr_url:
        return ManagerDispatchPromotionState(
            phase="draft_pr_created",
            final_status="promoted",
            approval_id=approval_id,
            pr_url=promotion.pr_url,
            branch_name=promotion.branch_name,
            commit_sha=promotion.commit_sha,
            error=promotion.reason,
            source="run_summary",
        )
    if promotion is not None and promotion.success is False and promotion.reason:
        return ManagerDispatchPromotionState(
            phase="promotion_failed",
            final_status="promotion_failed",
            approval_id=approval_id,
            error=promotion.reason,
            source="run_summary",
        )

    promotion_status = str(dispatch.metadata.get("promotion_status") or "").strip().lower()
    if promotion_status == JobStatus.FAILED.value:
        return ManagerDispatchPromotionState(
            phase="promotion_failed",
            final_status="promotion_failed",
            approval_id=approval_id,
            promotion_id=str(dispatch.metadata.get("promotion_id") or "").strip() or None,
            promotion_status=promotion_status,
            pr_url=str(dispatch.metadata.get("promotion_pr_url") or "").strip() or None,
            branch_name=str(dispatch.metadata.get("promotion_branch_name") or "").strip() or None,
            commit_sha=str(dispatch.metadata.get("promotion_commit_sha") or "").strip() or None,
            error=str(dispatch.metadata.get("promotion_error") or "").strip() or None,
            source="dispatch_metadata",
        )
    if promotion_status == "rejected":
        return ManagerDispatchPromotionState(
            phase="patch_only_execution",
            final_status="ready_for_promotion",
            approval_id=approval_id,
            promotion_status=promotion_status,
            source="dispatch_metadata",
        )

    if approval_id and manager_dispatch_requests_draft_pr(dispatch):
        return ManagerDispatchPromotionState(
            phase="awaiting_approval",
            final_status="ready_for_promotion",
            approval_id=approval_id,
            source="dispatch_metadata",
        )
    if dispatch.status is JobStatus.QUEUED:
        return ManagerDispatchPromotionState(phase="task_accepted", final_status=None, source="dispatch")
    if dispatch.status is JobStatus.RUNNING:
        return ManagerDispatchPromotionState(phase="running", final_status=None, source="dispatch")
    if dispatch.run_summary is not None and dispatch.run_summary.final_status == "ready_for_promotion":
        return ManagerDispatchPromotionState(
            phase="patch_only_execution",
            final_status=dispatch.run_summary.final_status,
            source="dispatch",
        )
    if dispatch.status is JobStatus.FAILED:
        return ManagerDispatchPromotionState(
            phase="terminal_failed",
            final_status=dispatch.run_summary.final_status if dispatch.run_summary is not None else dispatch.status.value,
            error=dispatch.error,
            source="dispatch",
        )
    return ManagerDispatchPromotionState(
        phase=dispatch.status.value,
        final_status=dispatch.run_summary.final_status if dispatch.run_summary is not None else dispatch.status.value,
        source="dispatch",
    )


def _resolve_promotion_record(
    *,
    dispatch: ManagerDispatchRead,
    promotion_service: GitPromotionService | None,
) -> GitPromotionRead | None:
    if promotion_service is None:
        return None
    promotion_id = str(dispatch.metadata.get("promotion_id") or "").strip()
    if promotion_id:
        return promotion_service.get_promotion(promotion_id)
    run_id = dispatch.run_summary.run_id if dispatch.run_summary is not None else None
    if run_id:
        return promotion_service.find_latest_promotion_for_run(run_id)
    return None


def _promotion_mode_from_record(record: GitPromotionRead) -> GitPromotionMode:
    if record.pr_url or bool(record.metadata.get("open_draft_pr")):
        return GitPromotionMode.DRAFT_PR
    return GitPromotionMode.PATCH


def _resolve_changed_files(
    *,
    record: GitPromotionRead,
    run_summary: RunSummary | None,
) -> list[str]:
    if run_summary is not None and run_summary.promotion is not None and run_summary.promotion.changed_files:
        return list(run_summary.promotion.changed_files)
    if run_summary is not None and run_summary.driver_result.changed_paths:
        return list(run_summary.driver_result.changed_paths)
    return list(record.metadata.get("changed_files") or [])
