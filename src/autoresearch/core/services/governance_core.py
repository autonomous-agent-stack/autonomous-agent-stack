from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from autoresearch.core.services.governance_adapters import GovernanceAdapterRegistry
from autoresearch.shared.governance_core import (
    GovernanceApprovalDecisionRequest,
    GovernanceApprovalRead,
    GovernanceApprovalStatus,
    GovernanceArtifactRead,
    GovernanceAuditEventRead,
    GovernanceRunRead,
    GovernanceRunStatus,
    GovernanceTaskCreateRequest,
    GovernanceTaskRead,
    GovernanceTaskStatus,
)
from autoresearch.shared.models import utc_now
from autoresearch.shared.store import Repository, create_resource_id


logger = logging.getLogger(__name__)

_APPROVAL_REQUIRED_TAGS = {"shell", "filesystem_write", "external_api"}


@dataclass(frozen=True)
class GovernanceRepositories:
    tasks: Repository[GovernanceTaskRead]
    runs: Repository[GovernanceRunRead]
    approvals: Repository[GovernanceApprovalRead]
    artifacts: Repository[GovernanceArtifactRead]
    audit_events: Repository[GovernanceAuditEventRead]


class InProcessTaskQueue:
    """Small single-process queue for MVP execution.

    This intentionally does not provide multi-process safety. It is a local
    bridge that can later be replaced by Redis/Celery without changing the API
    service contract.
    """

    def __init__(self, max_workers: int = 1) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="aas-governance")

    def submit(self, callback: Any, *args: Any) -> None:
        self._executor.submit(callback, *args)


class GovernanceCoreService:
    def __init__(
        self,
        *,
        repositories: GovernanceRepositories,
        adapters: GovernanceAdapterRegistry | None = None,
        queue: InProcessTaskQueue | None = None,
    ) -> None:
        self._repositories = repositories
        self._adapters = adapters or GovernanceAdapterRegistry()
        self._queue = queue or InProcessTaskQueue()

    def create_task(self, request: GovernanceTaskCreateRequest) -> GovernanceTaskRead:
        now = utc_now()
        task = GovernanceTaskRead(
            task_id=create_resource_id("task"),
            name=request.name,
            status=GovernanceTaskStatus.CREATED,
            parameters=request.parameters,
            risk_tags=request.risk_tags,
            adapter_id=request.adapter_id,
            owner=request.owner,
            created_at=now,
            updated_at=now,
            metadata=request.metadata,
        )
        self._repositories.tasks.save(task.task_id, task)
        self._audit(
            subject_type="task",
            subject_id=task.task_id,
            event_type="task.created",
            message=f"Task {task.name!r} created.",
            task_id=task.task_id,
            metadata={"adapter_id": task.adapter_id, "risk_tags": task.risk_tags},
        )

        if self._requires_approval(task):
            approval = self._create_approval(task)
            awaiting = task.model_copy(
                update={
                    "status": GovernanceTaskStatus.AWAITING_APPROVAL,
                    "approval_id": approval.approval_id,
                    "updated_at": utc_now(),
                }
            )
            self._repositories.tasks.save(awaiting.task_id, awaiting)
            self._audit(
                subject_type="approval",
                subject_id=approval.approval_id,
                event_type="approval.requested",
                message="Task requires approval before execution.",
                task_id=awaiting.task_id,
                metadata={"approval_id": approval.approval_id, "risk_tags": awaiting.risk_tags},
            )
            return awaiting

        self._audit(
            subject_type="task",
            subject_id=task.task_id,
            event_type="policy.auto_approved",
            message="Task risk policy allowed automatic execution.",
            task_id=task.task_id,
            metadata={"risk_tags": task.risk_tags},
        )
        return self._queue_task(task)

    def list_tasks(self) -> list[GovernanceTaskRead]:
        return self._repositories.tasks.list()

    def get_task(self, task_id: str) -> GovernanceTaskRead | None:
        return self._repositories.tasks.get(task_id)

    def get_run(self, run_id: str) -> GovernanceRunRead | None:
        return self._repositories.runs.get(run_id)

    def list_adapters(self):
        return self._adapters.list_descriptors()

    def list_run_events(self, run_id: str) -> list[GovernanceAuditEventRead]:
        run = self._repositories.runs.get(run_id)
        task_id = run.task_id if run is not None else None
        events = [
            event
            for event in self._repositories.audit_events.list()
            if event.run_id == run_id or (task_id is not None and event.task_id == task_id)
        ]
        return sorted(events, key=lambda item: item.created_at)

    def decide_task(
        self,
        task_id: str,
        request: GovernanceApprovalDecisionRequest,
    ) -> GovernanceTaskRead | None:
        task = self._repositories.tasks.get(task_id)
        if task is None:
            return None
        if task.approval_id is None:
            raise ValueError("task does not have a pending approval")
        approval = self._repositories.approvals.get(task.approval_id)
        if approval is None:
            raise ValueError("approval record not found")
        if approval.status != GovernanceApprovalStatus.PENDING:
            raise ValueError("approval has already been decided")
        if task.status != GovernanceTaskStatus.AWAITING_APPROVAL:
            raise ValueError(f"task is not awaiting approval: {task.status.value}")

        status = (
            GovernanceApprovalStatus.APPROVED
            if request.decision == "approved"
            else GovernanceApprovalStatus.REJECTED
        )
        resolved = approval.model_copy(
            update={
                "status": status,
                "approver": request.approver,
                "note": request.note,
                "updated_at": utc_now(),
                "metadata": {**approval.metadata, **request.metadata},
            }
        )
        self._repositories.approvals.save(resolved.approval_id, resolved)
        self._audit(
            subject_type="approval",
            subject_id=resolved.approval_id,
            event_type=f"approval.{status.value}",
            message=f"Approval {status.value}.",
            task_id=task.task_id,
            metadata={"approver": request.approver, "note": request.note},
        )

        if status == GovernanceApprovalStatus.REJECTED:
            rejected = task.model_copy(
                update={
                    "status": GovernanceTaskStatus.REJECTED,
                    "updated_at": utc_now(),
                    "error": request.note or "Task rejected by approver.",
                }
            )
            self._repositories.tasks.save(rejected.task_id, rejected)
            self._audit(
                subject_type="task",
                subject_id=rejected.task_id,
                event_type="task.rejected",
                message="Task rejected and will not run.",
                task_id=rejected.task_id,
            )
            return rejected

        return self._queue_task(task)

    def execute_run(self, run_id: str) -> None:
        run = self._repositories.runs.get(run_id)
        if run is None:
            logger.warning("Governance run %s disappeared before execution.", run_id)
            return
        task = self._repositories.tasks.get(run.task_id)
        if task is None:
            logger.warning("Governance task %s disappeared before execution.", run.task_id)
            return

        now = utc_now()
        running_run = run.model_copy(
            update={"status": GovernanceRunStatus.RUNNING, "started_at": now, "updated_at": now}
        )
        running_task = task.model_copy(
            update={"status": GovernanceTaskStatus.RUNNING, "updated_at": now}
        )
        self._repositories.runs.save(running_run.run_id, running_run)
        self._repositories.tasks.save(running_task.task_id, running_task)
        self._audit(
            subject_type="run",
            subject_id=running_run.run_id,
            event_type="run.started",
            message="Run started by local deterministic queue.",
            run_id=running_run.run_id,
            task_id=running_task.task_id,
            metadata={"adapter_id": running_run.adapter_id},
        )

        try:
            adapter = self._adapters.get(running_run.adapter_id)
            if not adapter.descriptor.enabled:
                raise RuntimeError(f"adapter {running_run.adapter_id!r} is disabled")
            self._audit(
                subject_type="adapter",
                subject_id=adapter.descriptor.adapter_id,
                event_type="adapter.called",
                message=f"Adapter {adapter.descriptor.name} invoked.",
                run_id=running_run.run_id,
                task_id=running_task.task_id,
                metadata={"adapter_type": adapter.descriptor.type},
            )
            result = adapter.execute(running_task)
            artifact_ids = self._save_artifacts(running_run.run_id, result.artifacts)
            completed_at = utc_now()
            succeeded_run = running_run.model_copy(
                update={
                    "status": GovernanceRunStatus.SUCCEEDED,
                    "output": result.output,
                    "completed_at": completed_at,
                    "updated_at": completed_at,
                    "metadata": {**running_run.metadata, "artifact_ids": artifact_ids},
                }
            )
            succeeded_task = running_task.model_copy(
                update={
                    "status": GovernanceTaskStatus.SUCCEEDED,
                    "result": result.output,
                    "updated_at": completed_at,
                }
            )
            self._repositories.runs.save(succeeded_run.run_id, succeeded_run)
            self._repositories.tasks.save(succeeded_task.task_id, succeeded_task)
            self._audit(
                subject_type="run",
                subject_id=succeeded_run.run_id,
                event_type="run.succeeded",
                message="Run completed successfully.",
                run_id=succeeded_run.run_id,
                task_id=succeeded_task.task_id,
                metadata={"artifact_ids": artifact_ids},
            )
        except Exception as exc:
            completed_at = utc_now()
            failed_run = running_run.model_copy(
                update={
                    "status": GovernanceRunStatus.FAILED,
                    "error": str(exc),
                    "completed_at": completed_at,
                    "updated_at": completed_at,
                }
            )
            failed_task = running_task.model_copy(
                update={
                    "status": GovernanceTaskStatus.FAILED,
                    "error": str(exc),
                    "updated_at": completed_at,
                }
            )
            self._repositories.runs.save(failed_run.run_id, failed_run)
            self._repositories.tasks.save(failed_task.task_id, failed_task)
            self._audit(
                subject_type="run",
                subject_id=failed_run.run_id,
                event_type="run.failed",
                message=str(exc),
                run_id=failed_run.run_id,
                task_id=failed_task.task_id,
            )

    def _queue_task(self, task: GovernanceTaskRead) -> GovernanceTaskRead:
        now = utc_now()
        run = GovernanceRunRead(
            run_id=create_resource_id("run"),
            task_id=task.task_id,
            adapter_id=task.adapter_id,
            status=GovernanceRunStatus.QUEUED,
            queued_at=now,
            updated_at=now,
        )
        queued = task.model_copy(
            update={
                "status": GovernanceTaskStatus.QUEUED,
                "run_id": run.run_id,
                "updated_at": now,
                "error": None,
            }
        )
        self._repositories.runs.save(run.run_id, run)
        self._repositories.tasks.save(queued.task_id, queued)
        self._audit(
            subject_type="run",
            subject_id=run.run_id,
            event_type="run.queued",
            message="Run queued in local process queue.",
            run_id=run.run_id,
            task_id=queued.task_id,
            metadata={"queue": "in_process", "multi_process_safe": False},
        )
        self._queue.submit(self.execute_run, run.run_id)
        return queued

    def _create_approval(self, task: GovernanceTaskRead) -> GovernanceApprovalRead:
        now = utc_now()
        approval = GovernanceApprovalRead(
            approval_id=create_resource_id("approval"),
            task_id=task.task_id,
            requested_by=task.owner,
            status=GovernanceApprovalStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata={"risk_tags": task.risk_tags},
        )
        return self._repositories.approvals.save(approval.approval_id, approval)

    def _save_artifacts(self, run_id: str, artifacts: list[dict[str, Any]]) -> list[str]:
        artifact_ids: list[str] = []
        for item in artifacts:
            artifact = GovernanceArtifactRead(
                artifact_id=create_resource_id("artifact"),
                run_id=run_id,
                type=str(item.get("type") or "unknown"),
                uri=str(item.get("uri") or ""),
                metadata=dict(item.get("metadata") or {}),
            )
            self._repositories.artifacts.save(artifact.artifact_id, artifact)
            artifact_ids.append(artifact.artifact_id)
            self._audit(
                subject_type="artifact",
                subject_id=artifact.artifact_id,
                event_type="artifact.created",
                message=f"Artifact {artifact.type!r} recorded.",
                run_id=run_id,
                metadata={"uri": artifact.uri},
            )
        return artifact_ids

    def _requires_approval(self, task: GovernanceTaskRead) -> bool:
        tags = {tag.strip().lower() for tag in task.risk_tags}
        return bool(tags & _APPROVAL_REQUIRED_TAGS)

    def _audit(
        self,
        *,
        subject_type: str,
        subject_id: str,
        event_type: str,
        message: str,
        run_id: str | None = None,
        task_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> GovernanceAuditEventRead:
        event = GovernanceAuditEventRead(
            event_id=create_resource_id("audit"),
            subject_type=subject_type,
            subject_id=subject_id,
            event_type=event_type,
            message=message,
            run_id=run_id,
            task_id=task_id,
            metadata=metadata or {},
        )
        return self._repositories.audit_events.save(event.event_id, event)
