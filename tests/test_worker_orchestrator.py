from __future__ import annotations

from pathlib import Path

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.autoresearch_controlled_backend import AutoResearchControlledBackendService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openhands_controlled_backend import OpenHandsControlledBackendService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.worker_orchestrator import WorkerOrchestratorService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestRead,
    ClaudeAgentCreateRequest,
    ClaudeAgentRunRead,
    OpenClawSessionCreateRequest,
    OpenClawSessionRead,
)
from autoresearch.shared.store import SQLiteModelRepository


def _build_services(
    tmp_path: Path,
) -> tuple[WorkerOrchestratorService, ClaudeAgentService, ApprovalStoreService, OpenClawCompatService]:
    db_path = tmp_path / "orchestrator.sqlite3"
    openclaw_service = OpenClawCompatService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="openclaw_sessions_orchestrator_it",
            model_cls=OpenClawSessionRead,
        )
    )
    claude_service = ClaudeAgentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="claude_agent_runs_orchestrator_it",
            model_cls=ClaudeAgentRunRead,
        ),
        openclaw_service=openclaw_service,
        repo_root=tmp_path,
    )
    approval_service = ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="approval_requests_orchestrator_it",
            model_cls=ApprovalRequestRead,
        )
    )
    service = WorkerOrchestratorService(
        agent_service=claude_service,
        approval_service=approval_service,
        openhands_backend=OpenHandsControlledBackendService(
            repo_root=tmp_path,
            run_root=tmp_path / "oh-runs",
        ),
        autoresearch_backend=AutoResearchControlledBackendService(
            repo_root=tmp_path,
            run_root=tmp_path / "ar-runs",
        ),
    )
    return service, claude_service, approval_service, openclaw_service


def test_worker_orchestrator_selects_autoresearch_for_analysis_tasks(tmp_path: Path) -> None:
    service, _, _, _ = _build_services(tmp_path)

    decision = service.decide(prompt="请分析当前记忆层设计的风险和方案", metadata={})

    assert decision.route == "autoresearch"
    assert decision.selected_worker == "autoresearch"
    assert decision.requires_approval is False
    assert decision.allowed_paths == ["docs/worker_notes.md"]


def test_worker_orchestrator_selects_chain_for_analysis_then_fix(tmp_path: Path) -> None:
    service, _, _, _ = _build_services(tmp_path)

    decision = service.decide(
        prompt="先分析 src/demo_fix.py 的问题，再修复这个 bug 并补测试",
        metadata={},
    )

    assert decision.route == "autoresearch_then_openhands"
    assert decision.worker_chain == ["autoresearch", "openhands"]
    assert "src/demo_fix.py" in decision.allowed_paths


def test_worker_orchestrator_requires_approval_for_main_branch_write(tmp_path: Path) -> None:
    service, _, _, _ = _build_services(tmp_path)

    decision = service.decide(
        prompt="请修复 src/demo_fix.py 并直接合并到 main",
        metadata={},
    )

    assert decision.route == "openhands"
    assert decision.requires_approval is True
    assert decision.approval_reason is not None


def test_worker_orchestrator_resume_after_approval_requeues_worker_run(tmp_path: Path) -> None:
    service, claude_service, approval_service, openclaw_service = _build_services(tmp_path)
    session = openclaw_service.create_session(
        OpenClawSessionCreateRequest(channel="telegram", external_id="9527", title="resume-run")
    )
    request = ClaudeAgentCreateRequest(
        task_name="Fix with approval",
        prompt="请修复 src/demo_fix.py 并直接合并到 main",
        session_id=session.session_id,
        metadata={
            "source": "telegram_webhook",
            "chat_id": "9527",
            "actor_user_id": "9527",
        },
    )

    decision, run, approval = service.queue_for_telegram(request=request)

    assert decision.requires_approval is True
    assert run is None
    assert approval is not None
    assert approval.metadata["worker_orchestration_replay"]["request"]["prompt"] == request.prompt

    approved = approval_service.resolve_request(
        approval.approval_id,
        ApprovalDecisionRequest(
            decision="approved",
            decided_by="9527",
            note="looks good",
            metadata={"resolved_via": "test"},
        ),
    )
    resumed = service.resume_approved_telegram_run(approval_id=approved.approval_id)

    assert resumed is not None
    assert resumed.agent_run_id
    queued = claude_service.get(resumed.agent_run_id)
    assert queued is not None
    assert queued.metadata["orchestration"]["approval_id"] == approved.approval_id
    assert queued.metadata["orchestration"]["approval_status"] == "approved"
    assert queued.metadata["orchestration"]["resume_state"] == "queued"


def test_worker_orchestrator_chain_keeps_analysis_stage_artifact_only(tmp_path: Path) -> None:
    service, _, _, openclaw_service = _build_services(tmp_path)
    session = openclaw_service.create_session(
        OpenClawSessionCreateRequest(channel="telegram", external_id="9527", title="chain-run")
    )
    request = ClaudeAgentCreateRequest(
        task_name="Analyze then fix",
        prompt="先分析 src/demo_fix.py 的问题，再修复这个 bug 并补测试",
        session_id=session.session_id,
        metadata={
            "source": "telegram_webhook",
            "chat_id": "9527",
            "actor_user_id": "9527",
        },
    )

    decision, run, approval = service.queue_for_telegram(request=request)

    assert approval is None
    assert run is not None
    summary = service.execute_telegram_run(
        agent_run_id=run.agent_run_id,
        request=request,
        decision=decision,
    )

    assert summary.status == "completed"
    assert summary.route == "autoresearch_then_openhands"
    assert summary.metadata["analysis_promotion_finalize_skipped"] is True
    assert summary.metadata["analysis_run_id"]
    assert summary.metadata["execution_run_id"]
    assert "execution_plan" in summary.metadata["analysis_deliverables"]
