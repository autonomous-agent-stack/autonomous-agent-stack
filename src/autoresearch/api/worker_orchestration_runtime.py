from __future__ import annotations

from typing import Any

from fastapi import BackgroundTasks

from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_orchestrator import WorkerOrchestratorService
from autoresearch.shared.models import ApprovalRequestRead, ClaudeAgentCreateRequest
from autoresearch.shared.worker_orchestration_contract import (
    WorkerApprovalResumeRead,
    WorkerRoutingDecision,
)


def maybe_resume_approved_worker_run(
    *,
    background_tasks: BackgroundTasks,
    approval: ApprovalRequestRead,
    worker_orchestrator: WorkerOrchestratorService,
    notifier: TelegramNotifierService | None,
    announce_start: bool = True,
    schedule_execution: bool = True,
) -> WorkerApprovalResumeRead | None:
    resumed = worker_orchestrator.resume_approved_telegram_run(approval_id=approval.approval_id)
    if resumed is None:
        return None

    chat_id = resumed.chat_id or approval.telegram_uid or ""
    if announce_start and notifier is not None and notifier.enabled and chat_id:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=(
                "审批已通过，开始恢复 worker pipeline。\n"
                f"worker: {resumed.decision.selected_worker}\n"
                f"run: {resumed.agent_run_id}\n"
                f"approval: {approval.approval_id}"
            ),
        )
    if schedule_execution:
        background_tasks.add_task(
            execute_orchestrated_run_and_notify,
            worker_orchestrator=worker_orchestrator,
            notifier=notifier,
            chat_id=chat_id,
            agent_run_id=resumed.agent_run_id,
            request_payload=resumed.request,
            decision_payload=resumed.decision.model_dump(mode="json"),
        )
    return resumed


def execute_orchestrated_run_and_notify(
    *,
    worker_orchestrator: WorkerOrchestratorService,
    notifier: TelegramNotifierService | None,
    chat_id: str,
    agent_run_id: str,
    request_payload: ClaudeAgentCreateRequest,
    decision_payload: dict[str, Any],
) -> None:
    decision = WorkerRoutingDecision.model_validate(decision_payload)
    summary = worker_orchestrator.execute_telegram_run(
        agent_run_id=agent_run_id,
        request=request_payload,
        decision=decision,
    )
    if notifier is None or not notifier.enabled or not chat_id:
        return
    lines = [
        f"[Worker 结果] {request_payload.task_name}",
        f"route: {summary.route}",
        f"worker: {summary.selected_worker}",
        f"status: {summary.status}",
        "",
        summary.summary_text,
    ]
    if summary.error_text:
        lines.extend(["", f"error: {summary.error_text}"])
    notifier.send_message(chat_id=chat_id, text="\n".join(lines)[:3900])
