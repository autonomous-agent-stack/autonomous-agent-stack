from __future__ import annotations

from typing import Any

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
    ApprovalRisk,
    ApprovalStatus,
    WorkerQueueItemCreateRequest,
    WorkerQueueItemRead,
)
from autoresearch.shared.worker_orchestration_contract import (
    WorkerApprovalResumeRead,
    WorkerOrchestrationReplayPayload,
    WorkerRoutingDecision,
)


WORKER_ORCHESTRATION_APPROVAL_SOURCE = "worker_orchestration"
_HIGH_RISK_HINTS = (
    " main",
    "main ",
    "merge",
    "delete",
    "remove",
    "reset",
    "rebase",
    "force",
    "production",
    "prod",
    "合并",
    "主分支",
    "删除",
    "上线",
    "生产",
)


class WorkerOrchestrationService:
    """Approval replay/resume spine for queued worker tasks."""

    def __init__(
        self,
        *,
        approval_store: ApprovalStoreService,
        worker_scheduler: WorkerSchedulerService,
    ) -> None:
        self._approval_store = approval_store
        self._worker_scheduler = worker_scheduler

    def decide(
        self,
        *,
        prompt: str,
        selected_worker: str,
        worker_chain: list[str] | None = None,
        approval_policy: str = "auto",
        metadata: dict[str, Any] | None = None,
    ) -> WorkerRoutingDecision:
        normalized_policy = str(approval_policy or "auto").strip().lower()
        if normalized_policy not in {"auto", "approval_required", "blocked"}:
            normalized_policy = "auto"
        high_risk = _looks_high_risk(prompt)
        requires_approval = normalized_policy == "approval_required" or high_risk
        risk = ApprovalRisk.DESTRUCTIVE if high_risk else (ApprovalRisk.EXTERNAL if requires_approval else None)
        reason = None
        if normalized_policy == "blocked":
            reason = "worker action is blocked by approval policy"
        elif high_risk:
            reason = "high-risk worker intent detected; approval is required before queueing"
        elif requires_approval:
            reason = "worker action requires approval before queueing"
        return WorkerRoutingDecision(
            route=selected_worker,
            selected_worker=selected_worker,
            worker_chain=list(worker_chain or [selected_worker]),
            selection_reason=f"deterministic worker route: {selected_worker}",
            requires_approval=requires_approval,
            approval_risk=risk,
            approval_reason=reason,
            approval_policy=normalized_policy,  # type: ignore[arg-type]
            metadata=dict(metadata or {}),
        )

    def queue_or_request_approval(
        self,
        *,
        queue_request: WorkerQueueItemCreateRequest,
        decision: WorkerRoutingDecision,
        prompt: str,
        title: str,
        telegram_uid: str | None = None,
        session_id: str | None = None,
    ) -> tuple[WorkerQueueItemRead | None, ApprovalRequestRead | None]:
        if decision.approval_policy == "blocked":
            raise PermissionError(decision.approval_reason or "worker action is blocked by approval policy")
        if not decision.requires_approval:
            return self._worker_scheduler.enqueue(queue_request), None
        replay = WorkerOrchestrationReplayPayload(queue_request=queue_request, decision=decision)
        approval = self._approval_store.create_request(
            ApprovalRequestCreateRequest(
                title=f"审批 worker 执行 / Approve worker run: {title}",
                summary="\n".join(
                    [
                        f"worker: {decision.selected_worker}",
                        f"reason: {decision.approval_reason or decision.selection_reason}",
                        f"prompt: {prompt[:1000]}",
                    ]
                ),
                risk=decision.approval_risk or ApprovalRisk.WRITE,
                source=WORKER_ORCHESTRATION_APPROVAL_SOURCE,
                telegram_uid=telegram_uid,
                session_id=session_id,
                metadata={
                    "action_type": WORKER_ORCHESTRATION_APPROVAL_SOURCE,
                    "orchestration": {
                        "resume_state": "waiting_approval",
                        "selected_worker": decision.selected_worker,
                        "worker_chain": decision.worker_chain,
                    },
                    "worker_orchestration_replay": replay.model_dump(mode="json"),
                },
            )
        )
        return None, approval

    def resume_approved_request(self, approval_id: str) -> WorkerApprovalResumeRead | None:
        approval = self._approval_store.get_request(approval_id)
        if approval is None:
            raise KeyError(f"approval not found: {approval_id}")
        if approval.source != WORKER_ORCHESTRATION_APPROVAL_SOURCE:
            return None
        if approval.status != ApprovalStatus.APPROVED:
            return None
        orchestration = dict(approval.metadata.get("orchestration") or {})
        if orchestration.get("resumed_run_id"):
            return None
        replay_raw = approval.metadata.get("worker_orchestration_replay")
        if not isinstance(replay_raw, dict):
            self._mark_resume_failure(approval, "worker orchestration replay payload missing")
            return None
        try:
            replay = WorkerOrchestrationReplayPayload.model_validate(replay_raw)
        except Exception as exc:
            self._mark_resume_failure(approval, f"invalid worker orchestration replay payload: {exc}")
            return None

        queue_request = replay.queue_request.model_copy(
            update={
                "metadata": {
                    **replay.queue_request.metadata,
                    "approval_id": approval.approval_id,
                    "approval_status": approval.status.value,
                    "approval_decided_by": approval.decided_by,
                    "orchestration": {
                        **orchestration,
                        "resume_state": "queued",
                    },
                }
            }
        )
        run = self._worker_scheduler.enqueue(queue_request)
        self._approval_store.update_request_metadata(
            approval.approval_id,
            {
                "orchestration": {
                    **orchestration,
                    "resume_state": "queued",
                    "resumed_run_id": run.run_id,
                    "approval_status": approval.status.value,
                    "approval_decided_by": approval.decided_by,
                },
                "resumed_worker_run_id": run.run_id,
            },
        )
        return WorkerApprovalResumeRead(
            approval_id=approval.approval_id,
            run_id=run.run_id,
            queue_request=queue_request,
            decision=replay.decision,
        )

    def _mark_resume_failure(self, approval: ApprovalRequestRead, error: str) -> None:
        orchestration = dict(approval.metadata.get("orchestration") or {})
        self._approval_store.update_request_metadata(
            approval.approval_id,
            {
                "orchestration": {
                    **orchestration,
                    "resume_state": "failed",
                    "resume_error": error,
                }
            },
        )


def _looks_high_risk(prompt: str) -> bool:
    normalized = f" {str(prompt or '').strip().lower()} "
    return any(token in normalized for token in _HIGH_RISK_HINTS)
