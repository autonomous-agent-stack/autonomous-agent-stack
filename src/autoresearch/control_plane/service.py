from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from autoresearch.control_plane.capabilities import ControlPlaneCapabilityRegistry
from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalDecisionRequest,
    ControlPlaneApprovalRead,
    ControlPlaneApprovalStatus,
    ControlPlaneArtifactRead,
    ControlPlaneAuditEventRead,
    ControlPlanePromotionRead,
    ControlPlaneRunRead,
    ControlPlaneRunStatus,
    ControlPlaneSessionRead,
    ControlPlaneTaskCreateRequest,
    ControlPlaneTaskRead,
    ControlPlaneTaskStatus,
)
from autoresearch.core.services.session_events import SessionEventService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import JobStatus, SessionEventCreateRequest, utc_now
from autoresearch.shared.models import WorkerQueueItemRead
from autoresearch.shared.store import Repository, create_resource_id


logger = logging.getLogger(__name__)

_APPROVAL_REQUIRED_TAGS = {"shell", "filesystem_write", "external_api"}


@dataclass(frozen=True)
class ControlPlaneRepositories:
    sessions: Repository[ControlPlaneSessionRead]
    tasks: Repository[ControlPlaneTaskRead]
    runs: Repository[ControlPlaneRunRead]
    approvals: Repository[ControlPlaneApprovalRead]
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
    ) -> None:
        self._repositories = repositories
        self._worker_scheduler = worker_scheduler
        self._session_events = session_events
        self._capabilities = capabilities or ControlPlaneCapabilityRegistry()

    def create_task(self, request: ControlPlaneTaskCreateRequest) -> ControlPlaneTaskRead:
        now = utc_now()
        capability = self._capabilities.get(request.capability_id).descriptor
        session = self._ensure_session(
            session_id=request.session_id,
            owner=request.requested_by,
            metadata={
                "created_by": "control_plane_v2",
                "first_task_name": request.name,
            },
        )
        effective_risk_tags = sorted({*request.risk_tags, *capability.risk_tags})
        task = ControlPlaneTaskRead(
            task_id=create_resource_id("task"),
            session_id=session.session_id,
            name=request.name,
            intent=request.intent,
            status=ControlPlaneTaskStatus.CREATED,
            capability_id=request.capability_id,
            parameters=request.parameters,
            risk_tags=effective_risk_tags,
            requested_by=request.requested_by,
            created_at=now,
            updated_at=now,
            metadata={
                **request.metadata,
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
        return self._dispatch_task(task)

    def sync_worker_run(self, worker_run: WorkerQueueItemRead) -> ControlPlaneTaskRead | None:
        task_id = str((worker_run.metadata or {}).get("control_plane_task_id") or "").strip()
        if not task_id:
            return None
        task = self._repositories.tasks.get(task_id)
        if task is None:
            logger.warning("Control Plane v2 task %s not found while syncing worker run %s", task_id, worker_run.run_id)
            return None

        run = self._repositories.runs.get(task.run_id or worker_run.run_id)
        if run is None:
            run = self._find_run_by_worker_run_id(worker_run.run_id)
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

        updated_task = task.model_copy(
            update={
                "status": task_status,
                "run_id": updated_run.run_id,
                "result": worker_run.result if worker_run.result is not None else task.result,
                "error": worker_run.error,
                "updated_at": max(task.updated_at, worker_run.updated_at, current),
            }
        )
        self._repositories.tasks.save(updated_task.task_id, updated_task)

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

    def _requires_approval(self, task: ControlPlaneTaskRead, *, capability_requires_approval: bool) -> bool:
        tags = {tag.strip().lower() for tag in task.risk_tags}
        return capability_requires_approval or bool(tags & _APPROVAL_REQUIRED_TAGS)

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


def _terminal_event_type_from_worker(status: JobStatus) -> str | None:
    if status == JobStatus.COMPLETED:
        return "run.succeeded"
    if status in {JobStatus.FAILED, JobStatus.INTERRUPTED}:
        return "run.failed"
    if status == JobStatus.CANCELLED:
        return "run.cancelled"
    return None
