from __future__ import annotations

from typing import Any

from autoresearch.core.services.github_ops import GITHUB_OPS_APPROVAL_ACTION, GitHubOpsService
from autoresearch.core.services.approval_actions import HERMES_INTERACTIVE_APPROVAL_ACTION
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.hermes_gateway_bridge import HermesGatewayTransport, HermesGatewayTransportError
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.worker_scheduler import WorkerReportError, WorkerSchedulerService
from autoresearch.shared.models import ApprovalDecisionRequest, ApprovalRequestRead, ApprovalStatus


class ApprovalDecisionDeliveryError(RuntimeError):
    """Raised when an approval decision cannot be delivered to its runtime."""


class ApprovalDecisionService:
    """Resolve approval decisions and run action-specific side effects."""

    def __init__(
        self,
        *,
        approval_store: ApprovalStoreService,
        worker_scheduler: WorkerSchedulerService | None = None,
        hermes_transport: HermesGatewayTransport | None = None,
        github_ops_service: GitHubOpsService | None = None,
        session_events: SessionEventService | None = None,
    ) -> None:
        self._approval_store = approval_store
        self._worker_scheduler = worker_scheduler
        self._hermes_transport = hermes_transport
        self._github_ops_service = github_ops_service
        self._session_events = session_events

    def resolve_request(
        self,
        approval_id: str,
        request: ApprovalDecisionRequest,
    ) -> ApprovalRequestRead:
        approval = self._approval_store.get_request(approval_id)
        if approval is None:
            raise KeyError(f"approval not found: {approval_id}")
        action_type = approval.metadata.get("action_type")
        if action_type == HERMES_INTERACTIVE_APPROVAL_ACTION:
            return self._resolve_hermes_interactive_approval(approval, request)
        if action_type == GITHUB_OPS_APPROVAL_ACTION:
            return self._resolve_github_ops_approval(approval, request)
        return self._approval_store.resolve_request(approval_id, request)

    def _resolve_github_ops_approval(
        self,
        approval: ApprovalRequestRead,
        request: ApprovalDecisionRequest,
    ) -> ApprovalRequestRead:
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"approval is not pending: {approval.approval_id}")
        if request.decision == "rejected":
            return self._approval_store.resolve_request(approval.approval_id, request)
        if self._github_ops_service is None:
            raise ApprovalDecisionDeliveryError("GitHub ops executor is not configured")
        try:
            result = self._github_ops_service.execute_approved_approval(approval)
        except Exception as exc:
            self._record_github_ops_delivery_failure(approval, request, str(exc))
            raise ApprovalDecisionDeliveryError(str(exc)) from exc
        return self._approval_store.resolve_request(
            approval.approval_id,
            request.model_copy(
                update={
                    "metadata": {
                        **dict(request.metadata),
                        "github_ops_executed": result.status == "completed",
                        "github_ops_result": result.model_dump(mode="json"),
                    }
                }
            ),
        )

    def _resolve_hermes_interactive_approval(
        self,
        approval: ApprovalRequestRead,
        request: ApprovalDecisionRequest,
    ) -> ApprovalRequestRead:
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"approval is not pending: {approval.approval_id}")
        if self._hermes_transport is None:
            raise ApprovalDecisionDeliveryError("Hermes gateway callback transport is not configured")

        metadata = dict(approval.metadata)
        gateway_session_id = str(metadata.get("gateway_session_id") or "").strip()
        gateway_event_id = str(metadata.get("gateway_event_id") or "").strip()
        if not gateway_session_id or not gateway_event_id:
            raise ApprovalDecisionDeliveryError("Hermes approval is missing gateway session or event id")

        callback_metadata: dict[str, Any] = {
            "approval_id": approval.approval_id,
            "action_type": HERMES_INTERACTIVE_APPROVAL_ACTION,
            "aas_session_id": metadata.get("aas_session_id"),
            "run_id": metadata.get("run_id"),
            "source": "aas_approval_decision",
            **dict(request.metadata),
        }
        try:
            self._hermes_transport.submit_approval_decision(
                gateway_session_id=gateway_session_id,
                event_id=gateway_event_id,
                decision=request.decision,
                decided_by=request.decided_by,
                note=request.note,
                metadata=callback_metadata,
            )
        except HermesGatewayTransportError as exc:
            self._record_hermes_delivery_failure(approval, request, str(exc))
            raise ApprovalDecisionDeliveryError(str(exc)) from exc

        resolved = self._approval_store.resolve_request(
            approval.approval_id,
            request.model_copy(
                update={
                    "metadata": {
                        **dict(request.metadata),
                        "hermes_gateway_decision_delivered": True,
                        "hermes_gateway_decision_delivered_to": gateway_session_id,
                        "hermes_gateway_event_id": gateway_event_id,
                    }
                }
            ),
        )
        self._requeue_hermes_run_after_decision(resolved)
        return resolved

    def _requeue_hermes_run_after_decision(self, approval: ApprovalRequestRead) -> None:
        if self._worker_scheduler is None:
            self._approval_store.update_request_metadata(
                approval.approval_id,
                {"hermes_requeue_status": "skipped_no_scheduler"},
            )
            return
        run_id = str(approval.metadata.get("run_id") or "").strip()
        if not run_id:
            self._approval_store.update_request_metadata(
                approval.approval_id,
                {"hermes_requeue_status": "skipped_no_run_id"},
            )
            return
        try:
            self._worker_scheduler.requeue_run(
                run_id,
                reason=f"Hermes interactive approval {approval.status.value}",
                backoff_seconds=1,
                increment_retry=False,
            )
        except (KeyError, WorkerReportError) as exc:
            self._approval_store.update_request_metadata(
                approval.approval_id,
                {
                    "hermes_requeue_status": "failed",
                    "hermes_requeue_error": str(exc),
                },
            )
            return
        self._approval_store.update_request_metadata(
            approval.approval_id,
            {"hermes_requeue_status": "requeued"},
        )

    def _record_hermes_delivery_failure(
        self,
        approval: ApprovalRequestRead,
        request: ApprovalDecisionRequest,
        error: str,
    ) -> None:
        if self._session_events is None:
            return
        try:
            self._approval_store.append_pending_side_event(
                approval,
                event_type="approval.decision_delivery_failed",
                content="Hermes approval decision delivery failed",
                idempotency_key=f"approval:{approval.approval_id}:delivery_failed:{request.decision}",
                metadata={
                    "decision": request.decision,
                    "decided_by": request.decided_by,
                    "error": error,
                    "action_type": HERMES_INTERACTIVE_APPROVAL_ACTION,
                },
            )
        except Exception:
            return

    def _record_github_ops_delivery_failure(
        self,
        approval: ApprovalRequestRead,
        request: ApprovalDecisionRequest,
        error: str,
    ) -> None:
        if self._session_events is None:
            return
        try:
            self._approval_store.append_pending_side_event(
                approval,
                event_type="approval.decision_delivery_failed",
                content="GitHub ops approval execution failed",
                idempotency_key=f"approval:{approval.approval_id}:github_ops_failed:{request.decision}",
                metadata={
                    "decision": request.decision,
                    "decided_by": request.decided_by,
                    "error": error,
                    "action_type": GITHUB_OPS_APPROVAL_ACTION,
                },
            )
        except Exception:
            return
