from __future__ import annotations

from dataclasses import dataclass

from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.agent_package_registry import AgentPackageRegistryService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.linux_supervisor import LinuxSupervisorService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.housekeeper_contract import (
    AgentPackageRecordRead,
    ControlPlaneTaskRead,
    HousekeeperApprovalRequest,
    HousekeeperBackendKind,
    HousekeeperTaskDraftRead,
    HousekeeperTaskStatus,
)
from autoresearch.shared.linux_supervisor_bridge import (
    supervisor_conclusion_to_gate_outcome,
    supervisor_conclusion_to_run_status,
    supervisor_summary_to_gate_checks,
    supervisor_summary_to_run_record,
)
from autoresearch.shared.linux_supervisor_contract import LinuxSupervisorTaskCreateRequest
from autoresearch.shared.task_gate_contract import make_gate_verdict
from autoresearch.shared.manager_agent_contract import ManagerDispatchRequest
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalStatus,
    ApprovalRisk,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id


@dataclass(frozen=True, slots=True)
class _FinalSelection:
    package: AgentPackageRecordRead
    worker_id: str


class ControlPlaneClarificationRequired(ValueError):
    def __init__(self, *, reason_code: str, message: str, questions: tuple[str, ...] = ()) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.questions = questions


class ControlPlaneService:
    """Authoritative task adjudication and dispatch for housekeeper requests."""

    def __init__(
        self,
        repository: Repository[ControlPlaneTaskRead],
        *,
        package_registry: AgentPackageRegistryService,
        worker_registry: WorkerRegistryService,
        approval_store: ApprovalStoreService,
        manager_service: ManagerAgentService,
        linux_supervisor_service: LinuxSupervisorService,
    ) -> None:
        self._repository = repository
        self._package_registry = package_registry
        self._worker_registry = worker_registry
        self._approval_store = approval_store
        self._manager_service = manager_service
        self._linux_supervisor_service = linux_supervisor_service

    def list_tasks(
        self, *, session_id: str | None = None, limit: int = 100
    ) -> list[ControlPlaneTaskRead]:
        normalized_session_id = (session_id or "").strip() or None
        items = self._repository.list()
        if normalized_session_id is not None:
            items = [item for item in items if item.session_id == normalized_session_id]
        items.sort(key=lambda item: item.updated_at, reverse=True)
        return items[: max(1, limit)]

    def get_task(self, task_id: str) -> ControlPlaneTaskRead | None:
        return self._repository.get(task_id)

    def submit_housekeeper_draft(
        self,
        draft: HousekeeperTaskDraftRead,
        *,
        housekeeper_task_id: str,
        dry_run: bool,
    ) -> ControlPlaneTaskRead:
        selection = self._finalize_selection(draft)
        now = utc_now()
        control_task = ControlPlaneTaskRead(
            task_id=create_resource_id("cptask"),
            source_kind="housekeeper",
            source_ref=housekeeper_task_id,
            session_id=draft.session_id,
            draft_id=draft.draft_id,
            housekeeper_task_id=housekeeper_task_id,
            agent_package_id=selection.package.package_id,
            selected_worker_id=selection.worker_id,
            backend_kind=selection.package.execution_backend,
            status=HousekeeperTaskStatus.CREATED,
            approval_status=None,
            approval_id=None,
            backend_ref=None,
            summary="Control plane accepted the housekeeper draft.",
            result_payload={},
            metadata={
                "routing_reason": draft.routing_reason,
                "dry_run": dry_run,
                "source_message": draft.source_message,
                "candidate_package_ids": list(draft.candidate_package_ids),
            },
            created_at=now,
            updated_at=now,
            error=None,
        )

        if self._requires_approval(selection.package):
            approval = self._approval_store.create_request(
                ApprovalRequestCreateRequest(
                    title=f"Approve control-plane task {selection.package.name}",
                    summary=draft.source_message,
                    risk=ApprovalRisk.WRITE,
                    source="control_plane",
                    session_id=draft.session_id,
                    metadata={
                        "housekeeper_task_id": housekeeper_task_id,
                        "control_plane_task_id": control_task.task_id,
                        "draft_id": draft.draft_id,
                        "agent_package_id": selection.package.package_id,
                    },
                )
            )
            control_task = control_task.model_copy(
                update={
                    "status": HousekeeperTaskStatus.APPROVAL_REQUIRED,
                    "approval_status": ApprovalStatus.PENDING,
                    "approval_id": approval.approval_id,
                    "summary": "Control plane requires approval before dispatch.",
                    "updated_at": utc_now(),
                }
            )
            return self._repository.save(control_task.task_id, control_task)

        saved = self._repository.save(control_task.task_id, control_task)
        if dry_run:
            dry = saved.model_copy(
                update={
                    "summary": "Control plane accepted the draft and stopped before execution because dry_run=true.",
                    "updated_at": utc_now(),
                }
            )
            return self._repository.save(dry.task_id, dry)
        return self._execute(saved)

    def approve_task(
        self, task_id: str, request: HousekeeperApprovalRequest
    ) -> ControlPlaneTaskRead:
        task = self._require_task(task_id)
        if task.approval_id is None:
            raise ValueError("control-plane task does not have a pending approval")
        approval = self._approval_store.resolve_request(
            task.approval_id,
            ApprovalDecisionRequest(
                decision="approved",
                decided_by=request.decided_by,
                note=request.note,
                metadata={"control_plane_task_id": task_id},
            ),
        )
        queued = task.model_copy(
            update={
                "approval_status": approval.status,
                "status": HousekeeperTaskStatus.QUEUED,
                "updated_at": utc_now(),
            }
        )
        saved = self._repository.save(queued.task_id, queued)
        return self._execute(saved)

    def reject_task(
        self, task_id: str, request: HousekeeperApprovalRequest
    ) -> ControlPlaneTaskRead:
        task = self._require_task(task_id)
        if task.approval_id is None:
            raise ValueError("control-plane task does not have a pending approval")
        approval = self._approval_store.resolve_request(
            task.approval_id,
            ApprovalDecisionRequest(
                decision="rejected",
                decided_by=request.decided_by,
                note=request.note,
                metadata={"control_plane_task_id": task_id},
            ),
        )
        rejected = task.model_copy(
            update={
                "approval_status": approval.status,
                "status": HousekeeperTaskStatus.REJECTED,
                "summary": "Control plane task was rejected during approval.",
                "updated_at": utc_now(),
                "error": request.note or "approval rejected",
            }
        )
        return self._repository.save(rejected.task_id, rejected)

    def _execute(self, task: ControlPlaneTaskRead) -> ControlPlaneTaskRead:
        running = task.model_copy(
            update={"status": HousekeeperTaskStatus.RUNNING, "updated_at": utc_now()}
        )
        running = self._repository.save(running.task_id, running)
        package = self._package_registry.get_package(running.agent_package_id)
        if package is None:
            failed = running.model_copy(
                update={
                    "status": HousekeeperTaskStatus.FAILED,
                    "updated_at": utc_now(),
                    "error": "package metadata missing during dispatch",
                }
            )
            return self._repository.save(failed.task_id, failed)

        if running.backend_kind is HousekeeperBackendKind.MANAGER_AGENT:
            dispatch = self._manager_service.create_dispatch(
                ManagerDispatchRequest(
                    prompt=running.metadata.get("source_message", "") or "",
                    auto_dispatch=False,
                    approval_granted=running.approval_status is ApprovalStatus.APPROVED,
                    metadata={
                        "source": "control_plane",
                        "control_plane_task_id": running.task_id,
                        "housekeeper_task_id": running.housekeeper_task_id,
                    },
                )
            )
            completed_dispatch = self._manager_service.execute_dispatch(dispatch.dispatch_id)
            updated = running.model_copy(
                update={
                    "status": HousekeeperTaskStatus.from_job_status(completed_dispatch.status),
                    "backend_ref": completed_dispatch.dispatch_id,
                    "summary": completed_dispatch.summary,
                    "result_payload": completed_dispatch.model_dump(mode="json"),
                    "updated_at": utc_now(),
                    "error": completed_dispatch.error,
                }
            )
            return self._repository.save(updated.task_id, updated)

        if running.backend_kind is HousekeeperBackendKind.LINUX_SUPERVISOR:
            linux_task = self._linux_supervisor_service.enqueue_task(
                LinuxSupervisorTaskCreateRequest(
                    prompt=running.metadata.get("source_message", "") or "",
                    metadata={
                        "control_plane_task_id": running.task_id,
                        "housekeeper_task_id": running.housekeeper_task_id,
                    },
                )
            )
            summary = self._linux_supervisor_service.run_once()
            if summary is None or summary.task_id != linux_task.task_id:
                failed = running.model_copy(
                    update={
                        "status": HousekeeperTaskStatus.FAILED,
                        "backend_ref": linux_task.task_id,
                        "updated_at": utc_now(),
                        "error": "linux supervisor did not return a summary for the queued task",
                    }
                )
                return self._repository.save(failed.task_id, failed)
            # Evaluate gate through unified contracts
            gate_outcome = supervisor_conclusion_to_gate_outcome(summary.conclusion)
            gate_checks = supervisor_summary_to_gate_checks(summary)
            run_status = supervisor_conclusion_to_run_status(summary.conclusion)
            verdict = make_gate_verdict(
                gate_outcome,
                reason=summary.message or f"conclusion={summary.conclusion.value}",
                checks=gate_checks,
            )
            result_payload = summary.model_dump(mode="json")
            result_payload["gate_evaluation"] = {
                "gate_outcome": gate_outcome.value,
                "gate_action": verdict.action.value,
                "run_status": run_status.value,
                "gate_checks": [c.model_dump() for c in gate_checks],
                "gate_verdict_reason": verdict.reason,
            }

            # Unified run record from bridge
            from dataclasses import asdict

            bridge_run = supervisor_summary_to_run_record(
                summary,
                worker_id=running.selected_worker_id or "linux_housekeeper",
                retry_attempt=1,
            )
            result_payload["run_record"] = asdict(bridge_run)
            # Serialize datetime fields to ISO strings for JSON compatibility
            run_rec = result_payload["run_record"]
            if run_rec.get("started_at") is not None:
                run_rec["started_at"] = run_rec["started_at"].isoformat()
            if run_rec.get("completed_at") is not None:
                run_rec["completed_at"] = run_rec["completed_at"].isoformat()
            run_rec["run_status"] = bridge_run.status.value

            updated = running.model_copy(
                update={
                    "status": (
                        HousekeeperTaskStatus.COMPLETED
                        if summary.success
                        else HousekeeperTaskStatus.FAILED
                    ),
                    "backend_ref": linux_task.task_id,
                    "summary": summary.message,
                    "result_payload": result_payload,
                    "updated_at": utc_now(),
                    "error": None if summary.success else summary.conclusion.value,
                }
            )
            return self._repository.save(updated.task_id, updated)

        failed = running.model_copy(
            update={
                "status": HousekeeperTaskStatus.FAILED,
                "updated_at": utc_now(),
                "error": f"backend {running.backend_kind.value} is not implemented in v0",
                "summary": "Backend is registered but not implemented in v0.",
            }
        )
        return self._repository.save(failed.task_id, failed)

    def _finalize_selection(self, draft: HousekeeperTaskDraftRead) -> _FinalSelection:
        for package_id in draft.candidate_package_ids:
            package = self._package_registry.get_package(package_id)
            if package is None:
                continue
            self._enforce_package_scope(package, draft.source_message)
            worker = self._worker_registry.find_worker_for_package(package)
            if worker is None:
                continue
            return _FinalSelection(package=package, worker_id=worker.worker_id)
        raise ControlPlaneClarificationRequired(
            reason_code="no_safe_match",
            message="control plane could not finalize a worker/package match from the draft",
            questions=(
                "请确认你希望走哪类执行链：代码改动、Linux 运维，还是影刀业务执行？",
                "如果任务需要特定执行节点，请补充目标环境或约束。",
            ),
        )

    def _enforce_package_scope(self, package: AgentPackageRecordRead, prompt: str) -> None:
        validation = self._package_registry.validate_prompt_for_package(package, prompt)
        if validation.allowed:
            return
        raise ControlPlaneClarificationRequired(
            reason_code=validation.reason_code or "clarification_required",
            message=validation.message or "package validator requested clarification",
            questions=validation.clarification_questions,
        )

    def _requires_approval(self, package: AgentPackageRecordRead) -> bool:
        if package.requires_approval:
            return True
        return package.risk_level in {"high", "critical"}

    def _require_task(self, task_id: str) -> ControlPlaneTaskRead:
        task = self._repository.get(task_id)
        if task is None:
            raise KeyError(f"control-plane task not found: {task_id}")
        return task
