from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from autoresearch.control_plane.capabilities import ControlPlaneCapabilityRegistry
from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalDecisionRequest,
    ControlPlaneApprovalGrantRead,
    ControlPlaneApprovalGrantStatus,
    ControlPlaneApprovalRead,
    ControlPlaneApprovalStatus,
    ControlPlaneArtifactRead,
    ControlPlaneAuditEventRead,
    ControlPlaneOperatorActionRequest,
    ControlPlanePromotionRead,
    ControlPlaneRunRead,
    ControlPlaneRunStatus,
    ControlPlaneSessionRead,
    ControlPlaneTaskCreateRequest,
    ControlPlaneTaskRead,
    ControlPlaneTaskStatus,
)
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.butler_agent_state import ButlerAgentStateService
from autoresearch.core.services.butler_failure_review import (
    ButlerFailureReviewRequest,
    ButlerFailureReviewService,
)
from autoresearch.core.services.butler_tool_broker import (
    ButlerToolBroker,
    ButlerToolResolveRequest,
)
from autoresearch.core.services.worker_scheduler import WorkerReportError, WorkerSchedulerService
from autoresearch.shared.models import JobStatus, SessionEventCreateRequest, utc_now
from autoresearch.shared.models import WorkerQueueItemCreateRequest, WorkerQueueItemRead
from autoresearch.shared.models import WorkerTaskType
from autoresearch.shared.store import Repository, create_resource_id


logger = logging.getLogger(__name__)

_APPROVAL_REQUIRED_TAGS = {"shell", "filesystem_write", "external_api"}
_ANNUAL_APPROVAL_GRANT_SECONDS = 365 * 24 * 60 * 60
_RETRY_METADATA_PRESERVE_KEYS = {
    "chat_id",
    "message_thread_id",
    "session_key",
    "control_plane_task_id",
    "control_plane_session_id",
    "capability_id",
    "telegram_completion_via_api",
    "telegram_queue_ack_message_id",
}
_RETRY_TELEGRAM_DROP_KEYS = {
    "telegram_butler_fallback_reason",
    "telegram_butler_fallback_sent",
    "telegram_butler_primary_sent",
    "telegram_cancel_requested_sent",
    "telegram_live_last_body_hash",
    "telegram_live_last_edit_at",
}


@dataclass(frozen=True)
class ControlPlaneRepositories:
    sessions: Repository[ControlPlaneSessionRead]
    tasks: Repository[ControlPlaneTaskRead]
    runs: Repository[ControlPlaneRunRead]
    approvals: Repository[ControlPlaneApprovalRead]
    approval_grants: Repository[ControlPlaneApprovalGrantRead]
    artifacts: Repository[ControlPlaneArtifactRead]
    audit_events: Repository[ControlPlaneAuditEventRead]
    promotions: Repository[ControlPlanePromotionRead]


class ControlPlaneService:
    def __init__(
        self,
        *,
        repositories: ControlPlaneRepositories,
        worker_scheduler: WorkerSchedulerService,
        session_events: SessionEventService,
        capabilities: ControlPlaneCapabilityRegistry | None = None,
        tool_broker: ButlerToolBroker | None = None,
        butler_agent_state: ButlerAgentStateService | None = None,
        failure_review_service: ButlerFailureReviewService | None = None,
    ) -> None:
        self._repositories = repositories
        self._worker_scheduler = worker_scheduler
        self._session_events = session_events
        self._capabilities = capabilities or ControlPlaneCapabilityRegistry()
        self._tool_broker = tool_broker or ButlerToolBroker()
        self._butler_agent_state = butler_agent_state
        self._failure_review_service = failure_review_service

    def create_task(self, request: ControlPlaneTaskCreateRequest) -> ControlPlaneTaskRead:
        now = utc_now()
        capability = self._capabilities.get(request.capability_id).descriptor
        parameters = dict(request.parameters)
        task_metadata = dict(request.metadata)
        effective_risk_tags = {*request.risk_tags, *capability.risk_tags}
        tool_resolution = None
        tool_requirements = parameters.get("tool_requirements") or task_metadata.get("tool_requirements") or []
        if tool_requirements:
            tool_resolution = self._tool_broker.resolve(
                ButlerToolResolveRequest(
                    requested_by=request.requested_by,
                    actor_role=str(
                        parameters.get("actor_role")
                        or task_metadata.get("actor_role")
                        or task_metadata.get("role")
                        or "operator"
                    ),
                    target_agent=str(
                        parameters.get("target_agent")
                        or parameters.get("agent_name")
                        or task_metadata.get("target_agent")
                        or "butler_orchestrator"
                    ),
                    tool_requirements=tool_requirements,
                    task_risk_tags=list(effective_risk_tags),
                    parameters=parameters,
                )
            )
            tool_payload = tool_resolution.model_dump(mode="json")
            parameters["tool_grants"] = tool_payload["grants"]
            parameters["tool_denials"] = tool_payload["denied"]
            task_metadata["tool_broker"] = tool_payload
            task_metadata["tool_grants"] = tool_payload["grants"]
            effective_risk_tags.update(tool_resolution.risk_tags)
        session = self._ensure_session(
            session_id=request.session_id,
            owner=request.requested_by,
            metadata={
                "created_by": "control_plane_v2",
                "first_task_name": request.name,
            },
        )
        sorted_risk_tags = sorted(effective_risk_tags)
        task = ControlPlaneTaskRead(
            task_id=create_resource_id("task"),
            session_id=session.session_id,
            name=request.name,
            intent=request.intent,
            status=ControlPlaneTaskStatus.CREATED,
            capability_id=request.capability_id,
            parameters=parameters,
            risk_tags=sorted_risk_tags,
            requested_by=request.requested_by,
            created_at=now,
            updated_at=now,
            metadata={
                **task_metadata,
                "priority": request.priority,
                "capability_type": capability.type,
            },
        )
        self._repositories.tasks.save(task.task_id, task)
        self._record(
            session_id=task.session_id,
            subject_type="task",
            subject_id=task.task_id,
            event_type="task.created",
            message=f"Task created: {task.name}",
            task_id=task.task_id,
            metadata={"capability_id": task.capability_id, "risk_tags": task.risk_tags},
        )
        unavailable = self._agent_unavailable_reason(task)
        if unavailable is not None:
            unavailable_agent, unavailable_reason = unavailable
            rejected = task.model_copy(
                update={
                    "status": ControlPlaneTaskStatus.REJECTED,
                    "error": unavailable_reason,
                    "updated_at": utc_now(),
                    "metadata": {
                        **task.metadata,
                        "butler_agent_hotplug": True,
                        "butler_agent_name": unavailable_agent.agent_name,
                        "butler_agent_status": unavailable_agent.status.value,
                        "butler_agent_reason": unavailable_agent.reason,
                    },
                }
            )
            self._repositories.tasks.save(rejected.task_id, rejected)
            self._record(
                session_id=rejected.session_id,
                subject_type="agent",
                subject_id=unavailable_agent.agent_name,
                event_type="agent.unavailable",
                message=unavailable_reason,
                task_id=rejected.task_id,
                metadata={
                    "agent_name": unavailable_agent.agent_name,
                    "agent_status": unavailable_agent.status.value,
                    "capability_id": rejected.capability_id,
                },
            )
            return rejected
        if tool_resolution is not None:
            self._record(
                session_id=task.session_id,
                subject_type="tool_broker",
                subject_id=task.task_id,
                event_type="tool_broker.resolved",
                message=f"Tool broker resolved {len(tool_resolution.grants)} grant(s).",
                task_id=task.task_id,
                metadata=tool_resolution.model_dump(mode="json"),
            )

        approval_grant = self._find_active_approval_grant(task)
        if approval_grant is not None:
            granted_task = task.model_copy(
                update={
                    "metadata": {
                        **task.metadata,
                        "approval_grant_id": approval_grant.grant_id,
                        "approval_grant_expires_at": approval_grant.expires_at.isoformat(),
                        "approval_grant_source_approval_id": approval_grant.source_approval_id,
                    },
                    "updated_at": utc_now(),
                }
            )
            self._repositories.tasks.save(granted_task.task_id, granted_task)
            self._record(
                session_id=granted_task.session_id,
                subject_type="approval_grant",
                subject_id=approval_grant.grant_id,
                event_type="approval.grant_applied",
                message="Annual approval grant applied.",
                task_id=granted_task.task_id,
                metadata={
                    "grant_id": approval_grant.grant_id,
                    "canonical_task_type": approval_grant.canonical_task_type,
                    "source_kind": approval_grant.source_kind,
                    "downstream_capability_id": approval_grant.downstream_capability_id,
                    "expires_at": approval_grant.expires_at.isoformat(),
                },
            )
            self._record(
                session_id=granted_task.session_id,
                subject_type="policy",
                subject_id=granted_task.task_id,
                event_type="policy.auto_approved",
                message="Task matched an active approval grant.",
                task_id=granted_task.task_id,
                metadata={"risk_tags": granted_task.risk_tags, "approval_grant_id": approval_grant.grant_id},
            )
            return self._dispatch_task(granted_task)

        if self._requires_approval(task, capability_requires_approval=capability.requires_approval):
            approval = self._create_approval(task)
            awaiting = task.model_copy(
                update={
                    "status": ControlPlaneTaskStatus.AWAITING_APPROVAL,
                    "approval_id": approval.approval_id,
                    "updated_at": utc_now(),
                }
            )
            self._repositories.tasks.save(awaiting.task_id, awaiting)
            self._record(
                session_id=awaiting.session_id,
                subject_type="approval",
                subject_id=approval.approval_id,
                event_type="approval.requested",
                message="Task requires approval before dispatch.",
                task_id=awaiting.task_id,
                approval_id=approval.approval_id,
                metadata={"risk_tags": awaiting.risk_tags},
            )
            return awaiting

        self._record(
            session_id=task.session_id,
            subject_type="policy",
            subject_id=task.task_id,
            event_type="policy.auto_approved",
            message="Task policy allowed automatic dispatch.",
            task_id=task.task_id,
            metadata={"risk_tags": task.risk_tags},
        )
        return self._dispatch_task(task)

    def list_tasks(self) -> list[ControlPlaneTaskRead]:
        return [self._project_task(item) for item in self._repositories.tasks.list()]

    def list_approvals(self) -> list[ControlPlaneApprovalRead]:
        return self._repositories.approvals.list()

    def list_approval_grants(self) -> list[ControlPlaneApprovalGrantRead]:
        grants = [
            self._normalize_approval_grant_expiration(item)
            for item in self._repositories.approval_grants.list()
        ]
        return sorted(grants, key=lambda item: item.updated_at, reverse=True)

    def _agent_unavailable_reason(self, task: ControlPlaneTaskRead):
        if self._butler_agent_state is None:
            return None
        target_agent = str(
            (task.parameters or {}).get("target_agent")
            or (task.parameters or {}).get("agent_name")
            or self._butler_agent_state.default_agent_for_capability(task.capability_id)
            or ""
        ).strip()
        return self._butler_agent_state.unavailable_reason(target_agent)

    def revoke_approval_grant(
        self,
        grant_id: str,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneApprovalGrantRead | None:
        grant = self._repositories.approval_grants.get(grant_id)
        if grant is None:
            return None
        current = utc_now()
        revoked = grant.model_copy(
            update={
                "status": ControlPlaneApprovalGrantStatus.REVOKED,
                "updated_at": current,
                "revoked_at": current,
                "metadata": {
                    **grant.metadata,
                    "revoke_reason": request.reason,
                    "revoked_by": request.requested_by,
                    **dict(request.metadata),
                },
            }
        )
        saved = self._repositories.approval_grants.save(revoked.grant_id, revoked)
        self._record(
            session_id=str(saved.metadata.get("session_id") or saved.grant_id),
            subject_type="approval_grant",
            subject_id=saved.grant_id,
            event_type="approval.grant_revoked",
            message=f"Approval grant revoked: {request.reason}",
            metadata={
                "grant_id": saved.grant_id,
                "requested_by": saved.requested_by,
                "reason": request.reason,
                "revoked_by": request.requested_by,
            },
        )
        return saved

    def get_approval(self, approval_id: str) -> ControlPlaneApprovalRead | None:
        return self._repositories.approvals.get(approval_id)

    def get_task(self, task_id: str) -> ControlPlaneTaskRead | None:
        task = self._repositories.tasks.get(task_id)
        if task is None:
            return None
        return self._project_task(task)

    def get_run(self, run_id: str) -> ControlPlaneRunRead | None:
        run = self._repositories.runs.get(run_id)
        if run is None:
            return None
        return self._project_run(run)

    def list_capabilities(self):
        return self._capabilities.list_descriptors()

    def session_timeline(self, *, session_id: str, limit: int = 100):
        return self._session_events.timeline(session_id=session_id, limit=limit)

    def run_events(self, run_id: str) -> list[ControlPlaneAuditEventRead]:
        run = self.get_run(run_id)
        if run is None:
            return []
        events = [
            event
            for event in self._repositories.audit_events.list()
            if event.run_id == run_id or event.task_id == run.task_id or event.session_id == run.session_id
        ]
        return sorted(events, key=lambda item: (item.created_at, item.event_id))

    def decide_task(
        self,
        task_id: str,
        request: ControlPlaneApprovalDecisionRequest,
    ) -> ControlPlaneTaskRead | None:
        task = self._repositories.tasks.get(task_id)
        if task is None:
            return None
        if not task.approval_id:
            raise ValueError("task does not have a pending approval")
        approval = self._repositories.approvals.get(task.approval_id)
        if approval is None:
            raise ValueError("approval record not found")
        if approval.status != ControlPlaneApprovalStatus.PENDING:
            raise ValueError("approval has already been decided")
        if task.status != ControlPlaneTaskStatus.AWAITING_APPROVAL:
            raise ValueError(f"task is not awaiting approval: {task.status.value}")

        status = (
            ControlPlaneApprovalStatus.APPROVED
            if request.decision == "approved"
            else ControlPlaneApprovalStatus.REJECTED
        )
        resolved = approval.model_copy(
            update={
                "status": status,
                "decided_by": request.decided_by,
                "note": request.note,
                "updated_at": utc_now(),
                "metadata": {**approval.metadata, **request.metadata},
            }
        )
        self._repositories.approvals.save(resolved.approval_id, resolved)
        self._record(
            session_id=task.session_id,
            subject_type="approval",
            subject_id=resolved.approval_id,
            event_type=f"approval.{status.value}",
            message=f"Approval {status.value}.",
            task_id=task.task_id,
            approval_id=resolved.approval_id,
            metadata={"decided_by": request.decided_by, "note": request.note},
        )

        if status == ControlPlaneApprovalStatus.REJECTED:
            rejected = task.model_copy(
                update={
                    "status": ControlPlaneTaskStatus.REJECTED,
                    "updated_at": utc_now(),
                    "error": request.note or "Task rejected by approver.",
                }
            )
            self._repositories.tasks.save(rejected.task_id, rejected)
            self._record(
                session_id=rejected.session_id,
                subject_type="task",
                subject_id=rejected.task_id,
                event_type="task.rejected",
                message="Task rejected and will not dispatch.",
                task_id=rejected.task_id,
            )
            return rejected
        dispatch_task = task
        approval_grant = self._maybe_create_approval_grant(
            task=task,
            approval=resolved,
            decision=request,
        )
        if approval_grant is not None:
            dispatch_task = task.model_copy(
                update={
                    "metadata": {
                        **task.metadata,
                        "approval_grant_id": approval_grant.grant_id,
                        "approval_grant_expires_at": approval_grant.expires_at.isoformat(),
                        "approval_grant_source_approval_id": approval_grant.source_approval_id,
                    },
                    "updated_at": utc_now(),
                }
            )
            self._repositories.tasks.save(dispatch_task.task_id, dispatch_task)
        return self._dispatch_task(dispatch_task)

    def cancel_task(
        self,
        task_id: str,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneTaskRead | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        run = self._current_run_for_task(task)
        return self._cancel_task_run(task=task, run=run, request=request)

    def cancel_run(
        self,
        run_id: str,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneTaskRead | None:
        resolved = self._resolve_current_task_run(run_id)
        if resolved is None:
            return None
        task, run = resolved
        return self._cancel_task_run(task=task, run=run, request=request)

    def force_fail_task(
        self,
        task_id: str,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneTaskRead | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        run = self._current_run_for_task(task)
        return self._force_fail_task_run(task=task, run=run, request=request)

    def force_fail_run(
        self,
        run_id: str,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneTaskRead | None:
        resolved = self._resolve_current_task_run(run_id)
        if resolved is None:
            return None
        task, run = resolved
        return self._force_fail_task_run(task=task, run=run, request=request)

    def retry_task(
        self,
        task_id: str,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneTaskRead | None:
        task = self.get_task(task_id)
        if task is None:
            return None
        run = self._current_run_for_task(task)
        return self._retry_task_run(task=task, run=run, request=request)

    def retry_run(
        self,
        run_id: str,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneTaskRead | None:
        resolved = self._resolve_current_task_run(run_id)
        if resolved is None:
            return None
        task, run = resolved
        return self._retry_task_run(task=task, run=run, request=request)

    def sync_worker_run(self, worker_run: WorkerQueueItemRead) -> ControlPlaneTaskRead | None:
        task_id = str((worker_run.metadata or {}).get("control_plane_task_id") or "").strip()
        if not task_id:
            return None
        task = self._repositories.tasks.get(task_id)
        if task is None:
            logger.warning("Control Plane v2 task %s not found while syncing worker run %s", task_id, worker_run.run_id)
            return None

        run = self._find_run_by_worker_run_id(worker_run.run_id)
        if run is None:
            run = self._repositories.runs.get(task.run_id or worker_run.run_id)
        if run is None:
            logger.warning("Control Plane v2 run for worker run %s not found while syncing task %s", worker_run.run_id, task_id)
            return None

        current = utc_now()
        run_status = _run_status_from_worker(worker_run.status)
        task_status = _task_status_from_run(run_status)
        worker_snapshot = {
            "worker_run_id": worker_run.run_id,
            "worker_status": worker_run.status.value,
            "worker_message": worker_run.message,
            "worker_result": worker_run.result,
            "worker_error": worker_run.error,
            "worker_metrics": worker_run.metrics,
        }
        updated_run = run.model_copy(
            update={
                "status": run_status,
                "worker_run_id": worker_run.run_id,
                "output": worker_run.result if worker_run.result is not None else run.output,
                "error": worker_run.error,
                "started_at": worker_run.started_at or run.started_at,
                "completed_at": worker_run.completed_at or run.completed_at,
                "updated_at": max(run.updated_at, worker_run.updated_at, current),
                "metadata": {
                    **run.metadata,
                    **worker_snapshot,
                },
            }
        )
        self._repositories.runs.save(updated_run.run_id, updated_run)

        if task.run_id in {None, updated_run.run_id}:
            recovery_projection = _worker_recovery_metadata_projection(worker_run.metadata)
            updated_task = task.model_copy(
                update={
                    "status": task_status,
                    "run_id": updated_run.run_id,
                    "result": worker_run.result if worker_run.result is not None else task.result,
                    "error": worker_run.error,
                    "updated_at": max(task.updated_at, worker_run.updated_at, current),
                    "metadata": {
                        **task.metadata,
                        **recovery_projection,
                    },
                }
            )
            self._repositories.tasks.save(updated_task.task_id, updated_task)
            recovery_worker_run_id = recovery_projection.get("xreach_recovery_worker_run_id")
            if recovery_worker_run_id and not task.metadata.get("xreach_recovery_worker_run_id"):
                self._record(
                    session_id=task.session_id,
                    subject_type="run",
                    subject_id=updated_run.run_id,
                    event_type="run.recovery_queued",
                    message="XReach recovery dispatched to Hermes.",
                    task_id=task.task_id,
                    run_id=updated_run.run_id,
                    metadata={
                        "capability_id": task.capability_id,
                        **recovery_projection,
                    },
                )
        else:
            updated_task = self._project_task(task)

        terminal_event = _terminal_event_type_from_worker(worker_run.status)
        if terminal_event is not None:
            self._record(
                session_id=task.session_id,
                subject_type="run",
                subject_id=updated_run.run_id,
                event_type=terminal_event,
                message=worker_run.message or f"Worker run {worker_run.status.value}.",
                task_id=task.task_id,
                run_id=updated_run.run_id,
                metadata={
                    "capability_id": task.capability_id,
                    **worker_snapshot,
                },
            )
        if worker_run.status == JobStatus.FAILED:
            reviewed_task = self._maybe_review_failed_worker_run(
                task=updated_task,
                run=updated_run,
                worker_run=worker_run,
                worker_snapshot=worker_snapshot,
            )
            if reviewed_task is not None:
                updated_task = reviewed_task
        downstream_task = self._maybe_enqueue_source_collect_downstream(
            task=updated_task,
            source_run=updated_run,
            worker_run=worker_run,
        )
        if downstream_task is not None:
            return downstream_task
        return updated_task

    def _maybe_review_failed_worker_run(
        self,
        *,
        task: ControlPlaneTaskRead,
        run: ControlPlaneRunRead,
        worker_run: WorkerQueueItemRead,
        worker_snapshot: dict[str, Any],
    ) -> ControlPlaneTaskRead | None:
        if self._failure_review_service is None:
            return None
        try:
            review = self._failure_review_service.review(
                ButlerFailureReviewRequest(
                    message=task.intent or task.name,
                    task_id=task.task_id,
                    run_id=run.run_id,
                    capability_id=task.capability_id,
                    route_decision=_butler_route_metadata(task.metadata),
                    worker_error=worker_run.error,
                    worker_message=worker_run.message,
                    worker_result=worker_run.result if isinstance(worker_run.result, dict) else None,
                    worker_metrics=worker_run.metrics if isinstance(worker_run.metrics, dict) else None,
                    session_id=task.session_id,
                    usage_entry_id=_optional_metadata_string(task.metadata, "usage_entry_id"),
                    metadata={
                        "worker_task_type": worker_run.task_type.value,
                        "worker_run_id": worker_run.run_id,
                    },
                )
            )
        except Exception:
            logger.exception("butler failure review raised for task=%s run=%s", task.task_id, run.run_id)
            return None

        review_payload = review.model_dump(mode="json")
        rule_candidate = review.rule_candidate or {}
        repair_metadata = {
            "failure_kind": review.failure_kind,
            "failure_review_id": review.review_id,
            "route_repair_suggestion": review.suggested_route,
            "hermes_review_run_id": review.hermes_review_run_id,
            "rule_candidate_id": rule_candidate.get("candidate_id"),
            "candidate_skill_summary": review.candidate_skill_summary,
            "failure_review": review_payload,
        }
        updated_run = run.model_copy(
            update={
                "metadata": {
                    **run.metadata,
                    **worker_snapshot,
                    **repair_metadata,
                },
            }
        )
        self._repositories.runs.save(updated_run.run_id, updated_run)
        task_result = dict(task.result or {})
        task_result["failure_review"] = review_payload
        updated_task = task.model_copy(
            update={
                "result": task_result,
                "metadata": {
                    **task.metadata,
                    **repair_metadata,
                },
            }
        )
        self._repositories.tasks.save(updated_task.task_id, updated_task)
        return updated_task

    def _maybe_enqueue_source_collect_downstream(
        self,
        *,
        task: ControlPlaneTaskRead,
        source_run: ControlPlaneRunRead,
        worker_run: WorkerQueueItemRead,
    ) -> ControlPlaneTaskRead | None:
        if worker_run.task_type != WorkerTaskType.SOURCE_COLLECT:
            return None
        if worker_run.status != JobStatus.COMPLETED:
            return None
        if task.metadata.get("source_collect_downstream_run_id"):
            return None
        result = worker_run.result if isinstance(worker_run.result, dict) else {}
        payload = result.get("content_kb_payload")
        if not isinstance(payload, dict):
            return None
        subtitle_text_path = str(payload.get("subtitle_text_path") or "").strip()
        if not subtitle_text_path:
            return None

        downstream_metadata = {
            **worker_run.metadata,
            "control_plane_task_id": task.task_id,
            "control_plane_session_id": task.session_id,
            "capability_id": "content_kb",
            "source_collect_run_id": source_run.run_id,
            "source_collect_worker_run_id": worker_run.run_id,
            "source_collect_downstream": True,
            "approval_grant_id": task.metadata.get("approval_grant_id"),
        }
        downstream_request = WorkerQueueItemCreateRequest(
            task_name=task.name,
            task_type=WorkerTaskType.CONTENT_KB_INGEST,
            payload={
                **payload,
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": "content_kb",
                "request_text": task.intent or task.name,
                "runtime_id": "content_kb",
                "agent_name": "content_kb",
                "target_agent": "content_kb",
                "target_agents": ["source_collect", "content_kb"],
            },
            requested_by=task.requested_by,
            priority=int(task.metadata.get("priority") or worker_run.priority or 4),
            metadata=downstream_metadata,
        )
        downstream_worker_run = self._worker_scheduler.enqueue(downstream_request)
        downstream_run = ControlPlaneRunRead(
            run_id=downstream_worker_run.run_id,
            task_id=task.task_id,
            session_id=task.session_id,
            capability_id="content_kb",
            status=ControlPlaneRunStatus.QUEUED,
            worker_run_id=downstream_worker_run.run_id,
            queued_at=downstream_worker_run.created_at,
            updated_at=downstream_worker_run.updated_at,
            metadata={
                "dispatch_mode": "worker_queue",
                "worker_task_type": downstream_worker_run.task_type.value,
                "source_collect_run_id": source_run.run_id,
                "source_collect_worker_run_id": worker_run.run_id,
                "approval_grant_id": task.metadata.get("approval_grant_id"),
            },
        )
        self._repositories.runs.save(downstream_run.run_id, downstream_run)
        previous_run_ids = _append_previous_run_id(task.metadata.get("previous_run_ids"), source_run.run_id)
        updated_task = task.model_copy(
            update={
                "status": ControlPlaneTaskStatus.QUEUED,
                "run_id": downstream_run.run_id,
                "result": None,
                "error": None,
                "updated_at": downstream_worker_run.updated_at,
                "metadata": {
                    **task.metadata,
                    "previous_run_ids": previous_run_ids,
                    "source_collect_downstream_run_id": downstream_run.run_id,
                    "source_collect_artifact_path": result.get("artifact_path"),
                },
            }
        )
        self._repositories.tasks.save(updated_task.task_id, updated_task)
        self._record(
            session_id=task.session_id,
            subject_type="run",
            subject_id=downstream_run.run_id,
            event_type="run.queued",
            message="Source artifact dispatched to content_kb ingest.",
            task_id=task.task_id,
            run_id=downstream_run.run_id,
            metadata={
                "worker_run_id": downstream_worker_run.run_id,
                "worker_task_type": downstream_worker_run.task_type.value,
                "capability_id": "content_kb",
                "source_collect_run_id": source_run.run_id,
                "artifact_path": result.get("artifact_path"),
                "approval_grant_id": task.metadata.get("approval_grant_id"),
            },
        )
        return updated_task

    def _cancel_task_run(
        self,
        *,
        task: ControlPlaneTaskRead,
        run: ControlPlaneRunRead,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneTaskRead:
        self._require_operator_worker_run(run, allowed={ControlPlaneRunStatus.QUEUED, ControlPlaneRunStatus.RUNNING})
        assert run.worker_run_id is not None
        try:
            worker_run = self._worker_scheduler.cancel_run(run.worker_run_id, reason=request.reason)
        except KeyError as exc:
            raise ValueError("worker run not found") from exc
        except WorkerReportError as exc:
            raise ValueError(exc.detail) from exc

        if worker_run.status == JobStatus.CANCELLED:
            synced = self.sync_worker_run(worker_run)
            if synced is None:
                raise ValueError("control-plane run could not be synced after cancellation")
            return synced

        now = utc_now()
        operator_metadata = {
            "reason": request.reason,
            "requested_by": request.requested_by,
            **dict(request.metadata),
        }
        updated_run = run.model_copy(
            update={
                "status": ControlPlaneRunStatus.RUNNING,
                "updated_at": max(run.updated_at, worker_run.updated_at, now),
                "metadata": {
                    **run.metadata,
                    "cancel_requested": True,
                    "cancel_reason": request.reason,
                    "cancel_requested_by": request.requested_by,
                    "cancel_requested_at": now.isoformat(),
                    "worker_run_id": worker_run.run_id,
                    "worker_status": worker_run.status.value,
                    "worker_message": worker_run.message,
                    "operator_metadata": operator_metadata,
                },
            }
        )
        self._repositories.runs.save(updated_run.run_id, updated_run)
        updated_task = task.model_copy(
            update={
                "status": ControlPlaneTaskStatus.RUNNING,
                "run_id": updated_run.run_id,
                "updated_at": max(task.updated_at, updated_run.updated_at),
            }
        )
        self._repositories.tasks.save(updated_task.task_id, updated_task)
        self._record(
            session_id=task.session_id,
            subject_type="run",
            subject_id=updated_run.run_id,
            event_type="run.cancel_requested",
            message=f"Cancellation requested: {request.reason}",
            task_id=task.task_id,
            run_id=updated_run.run_id,
            metadata={
                "capability_id": task.capability_id,
                "worker_run_id": worker_run.run_id,
                "reason": request.reason,
                "requested_by": request.requested_by,
                **dict(request.metadata),
            },
        )
        return updated_task

    def _force_fail_task_run(
        self,
        *,
        task: ControlPlaneTaskRead,
        run: ControlPlaneRunRead,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneTaskRead:
        self._require_operator_worker_run(run, allowed={ControlPlaneRunStatus.QUEUED, ControlPlaneRunStatus.RUNNING})
        assert run.worker_run_id is not None
        try:
            worker_run = self._worker_scheduler.force_fail_run(run.worker_run_id, reason=request.reason)
        except KeyError as exc:
            raise ValueError("worker run not found") from exc
        except WorkerReportError as exc:
            raise ValueError(exc.detail) from exc
        synced = self.sync_worker_run(worker_run)
        if synced is None:
            raise ValueError("control-plane run could not be synced after force-fail")
        return synced

    def _retry_task_run(
        self,
        *,
        task: ControlPlaneTaskRead,
        run: ControlPlaneRunRead,
        request: ControlPlaneOperatorActionRequest,
    ) -> ControlPlaneTaskRead:
        self._require_operator_worker_run(run, allowed={ControlPlaneRunStatus.FAILED, ControlPlaneRunStatus.CANCELLED})
        assert run.worker_run_id is not None
        previous_worker_run = self._worker_scheduler.get_run(run.worker_run_id)
        if previous_worker_run is None:
            raise ValueError("worker run not found")

        retry_sequence = _next_retry_sequence(run, previous_worker_run)
        worker_request = WorkerQueueItemCreateRequest(
            queue_name=previous_worker_run.queue_name,
            task_name=previous_worker_run.task_name,
            task_type=previous_worker_run.task_type,
            payload=dict(previous_worker_run.payload),
            requested_by=previous_worker_run.requested_by or request.requested_by,
            priority=previous_worker_run.priority,
            max_retries=previous_worker_run.max_retries,
            metadata=_retry_worker_metadata(
                task=task,
                previous_run=run,
                previous_worker_run=previous_worker_run,
                request=request,
                retry_sequence=retry_sequence,
            ),
        )
        worker_run = self._worker_scheduler.enqueue(worker_request)
        run_metadata = {
            "dispatch_mode": "worker_queue",
            "worker_task_type": worker_run.task_type.value,
            "retry_of_run_id": run.run_id,
            "retry_of_worker_run_id": previous_worker_run.run_id,
            "retry_sequence": retry_sequence,
            "retry_reason": request.reason,
            "retry_requested_by": request.requested_by,
            "operator_metadata": dict(request.metadata),
        }
        new_run = ControlPlaneRunRead(
            run_id=worker_run.run_id,
            task_id=task.task_id,
            session_id=task.session_id,
            capability_id=task.capability_id,
            status=ControlPlaneRunStatus.QUEUED,
            worker_run_id=worker_run.run_id,
            queued_at=worker_run.created_at,
            updated_at=worker_run.updated_at,
            metadata=run_metadata,
        )
        self._repositories.runs.save(new_run.run_id, new_run)

        previous_run_ids = _append_previous_run_id(task.metadata.get("previous_run_ids"), run.run_id)
        updated_task = task.model_copy(
            update={
                "status": ControlPlaneTaskStatus.QUEUED,
                "run_id": new_run.run_id,
                "result": None,
                "error": None,
                "updated_at": worker_run.updated_at,
                "metadata": {
                    **task.metadata,
                    "previous_run_ids": previous_run_ids,
                    "latest_retry_of_run_id": run.run_id,
                },
            }
        )
        self._repositories.tasks.save(updated_task.task_id, updated_task)
        self._record(
            session_id=task.session_id,
            subject_type="task",
            subject_id=task.task_id,
            event_type="task.retried",
            message=f"Task retried: {request.reason}",
            task_id=task.task_id,
            run_id=run.run_id,
            metadata={
                "previous_run_id": run.run_id,
                "previous_worker_run_id": previous_worker_run.run_id,
                "new_run_id": new_run.run_id,
                "new_worker_run_id": worker_run.run_id,
                "retry_sequence": retry_sequence,
                "requested_by": request.requested_by,
                "reason": request.reason,
                **dict(request.metadata),
            },
        )
        self._record(
            session_id=task.session_id,
            subject_type="run",
            subject_id=new_run.run_id,
            event_type="run.queued",
            message="Retried task dispatched onto the worker queue.",
            task_id=task.task_id,
            run_id=new_run.run_id,
            metadata={
                "worker_run_id": worker_run.run_id,
                "worker_task_type": worker_run.task_type.value,
                "capability_id": task.capability_id,
                "retry_of_run_id": run.run_id,
                "retry_sequence": retry_sequence,
            },
        )
        return updated_task

    def _dispatch_task(self, task: ControlPlaneTaskRead) -> ControlPlaneTaskRead:
        adapter = self._capabilities.get(task.capability_id)
        dispatch = adapter.dispatch(task)
        now = utc_now()
        if dispatch.immediate_result is not None:
            failed = bool(dispatch.immediate_result.get("status") == "disabled")
            run = ControlPlaneRunRead(
                run_id=create_resource_id("run"),
                task_id=task.task_id,
                session_id=task.session_id,
                capability_id=task.capability_id,
                status=ControlPlaneRunStatus.FAILED if failed else ControlPlaneRunStatus.SUCCEEDED,
                output=dict(dispatch.immediate_result),
                error=str(dispatch.immediate_result.get("reason") or "") if failed else None,
                queued_at=now,
                started_at=now,
                completed_at=now,
                updated_at=now,
                metadata={"dispatch_mode": adapter.descriptor.dispatch_mode},
            )
            self._repositories.runs.save(run.run_id, run)
            updated_task = task.model_copy(
                update={
                    "status": ControlPlaneTaskStatus.FAILED if failed else ControlPlaneTaskStatus.SUCCEEDED,
                    "run_id": run.run_id,
                    "result": run.output,
                    "error": run.error,
                    "updated_at": now,
                }
            )
            self._repositories.tasks.save(updated_task.task_id, updated_task)
            self._record(
                session_id=task.session_id,
                subject_type="run",
                subject_id=run.run_id,
                event_type="run.failed" if failed else "run.succeeded",
                message=run.error or "Run completed without worker dispatch.",
                task_id=task.task_id,
                run_id=run.run_id,
                metadata={"capability_id": task.capability_id},
            )
            return updated_task

        if dispatch.worker_request is None:
            raise RuntimeError(f"capability {task.capability_id!r} produced no dispatch request")
        worker_request = dispatch.worker_request.model_copy(
            update={
                "priority": int(task.metadata.get("priority") or dispatch.worker_request.priority),
                "metadata": {
                    **dispatch.worker_request.metadata,
                    "control_plane_task_id": task.task_id,
                    "control_plane_session_id": task.session_id,
                    "capability_id": task.capability_id,
                    "aas_session_id": task.session_id,
                },
            }
        )
        worker_run = self._worker_scheduler.enqueue(worker_request)
        run = ControlPlaneRunRead(
            run_id=worker_run.run_id,
            task_id=task.task_id,
            session_id=task.session_id,
            capability_id=task.capability_id,
            status=ControlPlaneRunStatus.QUEUED,
            worker_run_id=worker_run.run_id,
            queued_at=worker_run.created_at,
            updated_at=worker_run.updated_at,
            metadata={
                "dispatch_mode": "worker_queue",
                "worker_task_type": worker_run.task_type.value,
            },
        )
        self._repositories.runs.save(run.run_id, run)
        queued = task.model_copy(
            update={
                "status": ControlPlaneTaskStatus.QUEUED,
                "run_id": run.run_id,
                "updated_at": worker_run.updated_at,
                "error": None,
            }
        )
        self._repositories.tasks.save(queued.task_id, queued)
        self._record(
            session_id=task.session_id,
            subject_type="run",
            subject_id=run.run_id,
            event_type="run.queued",
            message="Task dispatched onto the worker queue.",
            task_id=task.task_id,
            run_id=run.run_id,
            metadata={
                "worker_run_id": worker_run.run_id,
                "worker_task_type": worker_run.task_type.value,
                "capability_id": task.capability_id,
            },
        )
        return queued

    def _ensure_session(self, *, session_id: str | None, owner: str, metadata: dict[str, Any]) -> ControlPlaneSessionRead:
        current = utc_now()
        resolved_id = session_id or create_resource_id("session")
        existing = self._repositories.sessions.get(resolved_id)
        if existing is not None:
            updated = existing.model_copy(
                update={
                    "updated_at": current,
                    "metadata": {**existing.metadata, **metadata},
                }
            )
            return self._repositories.sessions.save(resolved_id, updated)
        session = ControlPlaneSessionRead(
            session_id=resolved_id,
            owner=owner,
            created_at=current,
            updated_at=current,
            metadata=metadata,
        )
        saved = self._repositories.sessions.save(resolved_id, session)
        self._record(
            session_id=saved.session_id,
            subject_type="session",
            subject_id=saved.session_id,
            event_type="session.created",
            message="Control-plane session created.",
            metadata={"owner": owner},
        )
        return saved

    def _create_approval(self, task: ControlPlaneTaskRead) -> ControlPlaneApprovalRead:
        now = utc_now()
        approval = ControlPlaneApprovalRead(
            approval_id=create_resource_id("approval"),
            task_id=task.task_id,
            session_id=task.session_id,
            requested_by=task.requested_by,
            status=ControlPlaneApprovalStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata={"risk_tags": task.risk_tags, "capability_id": task.capability_id},
        )
        return self._repositories.approvals.save(approval.approval_id, approval)

    def _project_task(self, task: ControlPlaneTaskRead) -> ControlPlaneTaskRead:
        if not task.run_id:
            return task
        run = self.get_run(task.run_id)
        if run is None:
            return task
        status = _task_status_from_run(run.status)
        projected = task.model_copy(
            update={
                "status": status,
                "result": run.output if run.output is not None else task.result,
                "error": run.error,
                "updated_at": max(task.updated_at, run.updated_at),
            }
        )
        if projected != task:
            self._repositories.tasks.save(projected.task_id, projected)
        return projected

    def _project_run(self, run: ControlPlaneRunRead) -> ControlPlaneRunRead:
        if not run.worker_run_id:
            return run
        worker_run = self._worker_scheduler.get_run(run.worker_run_id)
        if worker_run is None:
            return run
        status = _run_status_from_worker(worker_run.status)
        projected = run.model_copy(
            update={
                "status": status,
                "output": worker_run.result if worker_run.result is not None else run.output,
                "error": worker_run.error,
                "started_at": worker_run.started_at or run.started_at,
                "completed_at": worker_run.completed_at or run.completed_at,
                "updated_at": max(run.updated_at, worker_run.updated_at),
                "metadata": {
                    **run.metadata,
                    "worker_status": worker_run.status.value,
                    "worker_message": worker_run.message,
                    "worker_metrics": worker_run.metrics,
                },
            }
        )
        if projected != run:
            self._repositories.runs.save(projected.run_id, projected)
        return projected

    def _find_run_by_worker_run_id(self, worker_run_id: str) -> ControlPlaneRunRead | None:
        for run in self._repositories.runs.list():
            if run.worker_run_id == worker_run_id:
                return run
        return None

    def _current_run_for_task(self, task: ControlPlaneTaskRead) -> ControlPlaneRunRead:
        if not task.run_id:
            raise ValueError("task does not have a current run")
        run = self.get_run(task.run_id)
        if run is None:
            raise ValueError("current run not found")
        return run

    def _resolve_current_task_run(self, run_id: str) -> tuple[ControlPlaneTaskRead, ControlPlaneRunRead] | None:
        run = self.get_run(run_id)
        if run is None:
            return None
        task = self.get_task(run.task_id)
        if task is None:
            raise ValueError("task for run not found")
        if task.run_id != run.run_id:
            raise ValueError("run is not the current task run")
        return task, run

    @staticmethod
    def _require_operator_worker_run(
        run: ControlPlaneRunRead,
        *,
        allowed: set[ControlPlaneRunStatus],
    ) -> None:
        if run.status not in allowed:
            allowed_values = ", ".join(sorted(status.value for status in allowed))
            raise ValueError(f"run status does not allow this operation: {run.status.value}; allowed: {allowed_values}")
        if not run.worker_run_id:
            raise ValueError("run is not backed by a worker run")

    def _requires_approval(self, task: ControlPlaneTaskRead, *, capability_requires_approval: bool) -> bool:
        tags = {tag.strip().lower() for tag in task.risk_tags}
        return capability_requires_approval or bool(tags & _APPROVAL_REQUIRED_TAGS)

    def _find_active_approval_grant(self, task: ControlPlaneTaskRead) -> ControlPlaneApprovalGrantRead | None:
        if not _matches_annual_grant_scope(task):
            return None
        actor_user_id = _task_actor_user_id(task)
        for raw in self._repositories.approval_grants.list():
            grant = self._normalize_approval_grant_expiration(raw)
            if grant.status != ControlPlaneApprovalGrantStatus.ACTIVE:
                continue
            if grant.requested_by != task.requested_by:
                continue
            if grant.actor_user_id and actor_user_id and grant.actor_user_id != actor_user_id:
                continue
            if grant.canonical_task_type != "source_collect.collect":
                continue
            if grant.source_kind != "x_bookmarks":
                continue
            if grant.downstream_capability_id != "content_kb":
                continue
            return grant
        return None

    def _maybe_create_approval_grant(
        self,
        *,
        task: ControlPlaneTaskRead,
        approval: ControlPlaneApprovalRead,
        decision: ControlPlaneApprovalDecisionRequest,
    ) -> ControlPlaneApprovalGrantRead | None:
        if not _requests_annual_approval_grant(decision.metadata, decision.note):
            return None
        if not _matches_annual_grant_scope(task):
            return None
        current = utc_now()
        expires_at = current + timedelta(seconds=_approval_grant_ttl_seconds(decision.metadata))
        grant = ControlPlaneApprovalGrantRead(
            grant_id=create_resource_id("grant"),
            requested_by=task.requested_by,
            actor_user_id=_task_actor_user_id(task),
            canonical_task_type="source_collect.collect",
            source_kind="x_bookmarks",
            downstream_capability_id="content_kb",
            status=ControlPlaneApprovalGrantStatus.ACTIVE,
            source_approval_id=approval.approval_id,
            created_at=current,
            updated_at=current,
            expires_at=expires_at,
            metadata={
                "session_id": task.session_id,
                "task_id": task.task_id,
                "capability_id": task.capability_id,
                "created_via": decision.metadata.get("resolved_via") or "control_plane_v2",
                "grant_kind": "annual",
                **dict(decision.metadata),
            },
        )
        saved = self._repositories.approval_grants.save(grant.grant_id, grant)
        self._record(
            session_id=task.session_id,
            subject_type="approval_grant",
            subject_id=saved.grant_id,
            event_type="approval.grant_created",
            message="Annual approval grant created.",
            task_id=task.task_id,
            approval_id=approval.approval_id,
            metadata={
                "grant_id": saved.grant_id,
                "canonical_task_type": saved.canonical_task_type,
                "source_kind": saved.source_kind,
                "downstream_capability_id": saved.downstream_capability_id,
                "expires_at": saved.expires_at.isoformat(),
            },
        )
        return saved

    def _normalize_approval_grant_expiration(
        self,
        grant: ControlPlaneApprovalGrantRead,
    ) -> ControlPlaneApprovalGrantRead:
        if grant.status != ControlPlaneApprovalGrantStatus.ACTIVE:
            return grant
        if grant.expires_at > utc_now():
            return grant
        current = utc_now()
        expired = grant.model_copy(
            update={
                "status": ControlPlaneApprovalGrantStatus.EXPIRED,
                "updated_at": current,
            }
        )
        return self._repositories.approval_grants.save(expired.grant_id, expired)

    def _record(
        self,
        *,
        session_id: str,
        subject_type: str,
        subject_id: str,
        event_type: str,
        message: str,
        task_id: str | None = None,
        run_id: str | None = None,
        approval_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ControlPlaneAuditEventRead:
        event = ControlPlaneAuditEventRead(
            event_id=create_resource_id("audit"),
            session_id=session_id,
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
            message=message,
            task_id=task_id,
            run_id=run_id,
            approval_id=approval_id,
            metadata=metadata or {},
        )
        saved = self._repositories.audit_events.save(event.event_id, event)
        try:
            self._session_events.append(
                SessionEventCreateRequest(
                    session_id=session_id,
                    source="control_plane_v2",
                    event_type=event_type,
                    role="status",
                    content=message,
                    status=event_type.rsplit(".", 1)[-1],
                    run_id=run_id,
                    approval_id=approval_id,
                    idempotency_key=f"cpv2:{event_type}:{subject_id}:{run_id or ''}:{approval_id or ''}",
                    metadata={
                        "subject_type": subject_type,
                        "subject_id": subject_id,
                        "task_id": task_id,
                        **dict(metadata or {}),
                    },
                )
            )
        except Exception:
            logger.warning("Failed to append v2 session event %s", event.event_id, exc_info=True)
        return saved


def _run_status_from_worker(status: JobStatus) -> ControlPlaneRunStatus:
    if status == JobStatus.COMPLETED:
        return ControlPlaneRunStatus.SUCCEEDED
    if status == JobStatus.FAILED:
        return ControlPlaneRunStatus.FAILED
    if status == JobStatus.CANCELLED:
        return ControlPlaneRunStatus.CANCELLED
    if status == JobStatus.RUNNING:
        return ControlPlaneRunStatus.RUNNING
    return ControlPlaneRunStatus.QUEUED


def _task_status_from_run(status: ControlPlaneRunStatus) -> ControlPlaneTaskStatus:
    if status == ControlPlaneRunStatus.SUCCEEDED:
        return ControlPlaneTaskStatus.SUCCEEDED
    if status == ControlPlaneRunStatus.FAILED:
        return ControlPlaneTaskStatus.FAILED
    if status == ControlPlaneRunStatus.CANCELLED:
        return ControlPlaneTaskStatus.CANCELLED
    if status == ControlPlaneRunStatus.RUNNING:
        return ControlPlaneTaskStatus.RUNNING
    return ControlPlaneTaskStatus.QUEUED


def _matches_annual_grant_scope(task: ControlPlaneTaskRead) -> bool:
    params = task.parameters or {}
    return (
        task.capability_id == "source_collect"
        and str(params.get("canonical_task_type") or "").strip().lower() == "source_collect.collect"
        and str(params.get("source_kind") or "").strip().lower() == "x_bookmarks"
        and str(params.get("downstream_capability_id") or "").strip().lower() == "content_kb"
    )


def _task_actor_user_id(task: ControlPlaneTaskRead) -> str | None:
    for source in (task.parameters or {}, task.metadata or {}):
        value = source.get("actor_user_id")
        if value is not None and str(value).strip():
            return str(value).strip()
    return task.requested_by or None


def _butler_route_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in dict(metadata or {}).items()
        if key.startswith("butler_")
        or key
        in {
            "capability_id",
            "failure_kind",
            "route_repair_suggestion",
            "tool_broker",
        }
    }


def _worker_recovery_metadata_projection(metadata: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "xreach_recovery_queued",
        "xreach_recovery_kind",
        "xreach_recovery_worker_run_id",
        "xreach_auth_recovery_worker_run_id",
        "xreach_setup_recovery_worker_run_id",
        "xreach_recovery_summary",
        "telegram_xreach_auth_recovery_sent",
    }
    return {
        key: value
        for key, value in dict(metadata or {}).items()
        if key in allowed and value not in (None, "")
    }


def _optional_metadata_string(metadata: dict[str, Any], key: str) -> str | None:
    value = dict(metadata or {}).get(key)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _requests_annual_approval_grant(metadata: dict[str, Any], note: str | None) -> bool:
    values = {
        str(metadata.get("approval_grant") or "").strip().lower(),
        str(metadata.get("grant_kind") or "").strip().lower(),
        str(metadata.get("approval_scope") or "").strip().lower(),
    }
    if values & {"annual", "year", "yearly", "one_year", "1year"}:
        return True
    return str(note or "").strip().lower() in {"annual", "year", "yearly", "授权一年", "按年授权"}


def _approval_grant_ttl_seconds(metadata: dict[str, Any]) -> int:
    raw = metadata.get("approval_grant_ttl_seconds") or metadata.get("grant_ttl_seconds")
    try:
        ttl = int(raw) if raw is not None else _ANNUAL_APPROVAL_GRANT_SECONDS
    except (TypeError, ValueError):
        ttl = _ANNUAL_APPROVAL_GRANT_SECONDS
    return max(24 * 60 * 60, min(ttl, _ANNUAL_APPROVAL_GRANT_SECONDS))


def _terminal_event_type_from_worker(status: JobStatus) -> str | None:
    if status == JobStatus.COMPLETED:
        return "run.succeeded"
    if status in {JobStatus.FAILED, JobStatus.INTERRUPTED}:
        return "run.failed"
    if status == JobStatus.CANCELLED:
        return "run.cancelled"
    return None


def _next_retry_sequence(
    run: ControlPlaneRunRead,
    worker_run: WorkerQueueItemRead,
) -> int:
    for raw in (run.metadata.get("retry_sequence"), worker_run.metadata.get("retry_sequence")):
        if raw is None:
            continue
        try:
            return int(raw) + 1
        except (TypeError, ValueError):
            continue
    return 1


def _retry_worker_metadata(
    *,
    task: ControlPlaneTaskRead,
    previous_run: ControlPlaneRunRead,
    previous_worker_run: WorkerQueueItemRead,
    request: ControlPlaneOperatorActionRequest,
    retry_sequence: int,
) -> dict[str, Any]:
    preserved: dict[str, Any] = {}
    for key, value in (previous_worker_run.metadata or {}).items():
        if key in _RETRY_TELEGRAM_DROP_KEYS:
            continue
        if key in _RETRY_METADATA_PRESERVE_KEYS or key.startswith("telegram_"):
            preserved[key] = value

    return {
        **preserved,
        "control_plane_task_id": task.task_id,
        "control_plane_session_id": task.session_id,
        "capability_id": task.capability_id,
        "retry_of_run_id": previous_run.run_id,
        "retry_of_worker_run_id": previous_worker_run.run_id,
        "retry_sequence": retry_sequence,
        "retry_reason": request.reason,
        "retry_requested_by": request.requested_by,
        "operator_metadata": dict(request.metadata),
    }


def _append_previous_run_id(raw_value: Any, run_id: str) -> list[str]:
    if isinstance(raw_value, list):
        previous = [str(item).strip() for item in raw_value if str(item).strip()]
    elif isinstance(raw_value, tuple):
        previous = [str(item).strip() for item in raw_value if str(item).strip()]
    elif raw_value is None:
        previous = []
    else:
        previous = [str(raw_value).strip()] if str(raw_value).strip() else []
    if run_id not in previous:
        previous.append(run_id)
    return previous
