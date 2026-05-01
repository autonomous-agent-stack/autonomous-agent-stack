from __future__ import annotations

from autoresearch.core.services.approval_decisions import ApprovalDecisionService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.worker_orchestration import WorkerOrchestrationService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalStatus,
    WorkerQueueItemCreateRequest,
    WorkerTaskType,
)
from autoresearch.shared.store import InMemoryRepository


def _build_services() -> tuple[WorkerOrchestrationService, ApprovalStoreService, WorkerSchedulerService]:
    approval_store = ApprovalStoreService(repository=InMemoryRepository())
    scheduler = WorkerSchedulerService(
        worker_registry=WorkerRegistryService(repository=InMemoryRepository()),
        queue_repository=InMemoryRepository(),
        lease_repository=InMemoryRepository(),
    )
    return (
        WorkerOrchestrationService(approval_store=approval_store, worker_scheduler=scheduler),
        approval_store,
        scheduler,
    )


def test_worker_orchestration_auto_policy_queues_immediately() -> None:
    orchestration, _approval_store, scheduler = _build_services()
    request = WorkerQueueItemCreateRequest(
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"prompt": "总结一下这个方案"},
    )
    decision = orchestration.decide(
        prompt="总结一下这个方案",
        selected_worker="claude_runtime",
        approval_policy="auto",
    )

    run, approval = orchestration.queue_or_request_approval(
        queue_request=request,
        decision=decision,
        prompt="总结一下这个方案",
        title="summary",
        telegram_uid="9527",
        session_id="sess_1",
    )

    assert approval is None
    assert run is not None
    assert scheduler.get_run(run.run_id) is not None


def test_worker_orchestration_high_risk_approval_resumes_queue() -> None:
    orchestration, approval_store, scheduler = _build_services()
    request = WorkerQueueItemCreateRequest(
        task_type=WorkerTaskType.CLAUDE_RUNTIME,
        payload={"prompt": "请修复 src/demo_fix.py 并直接合并到 main"},
        metadata={"chat_id": "9527"},
    )
    decision = orchestration.decide(
        prompt="请修复 src/demo_fix.py 并直接合并到 main",
        selected_worker="claude_runtime",
        approval_policy="auto",
    )

    run, approval = orchestration.queue_or_request_approval(
        queue_request=request,
        decision=decision,
        prompt="请修复 src/demo_fix.py 并直接合并到 main",
        title="dangerous worker task",
        telegram_uid="9527",
        session_id="sess_1",
    )

    assert run is None
    assert approval is not None
    assert approval.status == ApprovalStatus.PENDING
    assert approval.metadata["worker_orchestration_replay"]["queue_request"]["task_type"] == "claude_runtime"
    assert scheduler.list_queue() == []

    decision_service = ApprovalDecisionService(
        approval_store=approval_store,
        worker_scheduler=scheduler,
        worker_orchestration_service=orchestration,
    )
    resolved = decision_service.resolve_request(
        approval.approval_id,
        ApprovalDecisionRequest(decision="approved", decided_by="boss"),
    )

    assert resolved.status == ApprovalStatus.APPROVED
    queued = scheduler.list_queue()
    assert len(queued) == 1
    assert queued[0].task_type == WorkerTaskType.CLAUDE_RUNTIME
    assert queued[0].metadata["approval_id"] == approval.approval_id
    refreshed = approval_store.get_request(approval.approval_id)
    assert refreshed is not None
    assert refreshed.metadata["resumed_worker_run_id"] == queued[0].run_id


def test_worker_orchestration_reject_does_not_resume_queue() -> None:
    orchestration, approval_store, scheduler = _build_services()
    decision = orchestration.decide(
        prompt="delete production data",
        selected_worker="claude_runtime",
        approval_policy="auto",
    )
    _run, approval = orchestration.queue_or_request_approval(
        queue_request=WorkerQueueItemCreateRequest(task_type=WorkerTaskType.CLAUDE_RUNTIME),
        decision=decision,
        prompt="delete production data",
        title="blocked until approval",
        telegram_uid="9527",
        session_id="sess_1",
    )
    assert approval is not None

    decision_service = ApprovalDecisionService(
        approval_store=approval_store,
        worker_scheduler=scheduler,
        worker_orchestration_service=orchestration,
    )
    resolved = decision_service.resolve_request(
        approval.approval_id,
        ApprovalDecisionRequest(decision="rejected", decided_by="boss"),
    )

    assert resolved.status == ApprovalStatus.REJECTED
    assert scheduler.list_queue() == []
