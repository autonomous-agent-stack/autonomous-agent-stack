from __future__ import annotations

from pathlib import Path

from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.worker_orchestrator import WorkerOrchestratorService
from autoresearch.shared.models import ApprovalRequestRead, ClaudeAgentRunRead, OpenClawSessionRead
from autoresearch.shared.store import SQLiteModelRepository


def _build_service(tmp_path: Path) -> WorkerOrchestratorService:
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
    return WorkerOrchestratorService(
        agent_service=claude_service,
        approval_service=approval_service,
    )


def test_worker_orchestrator_selects_autoresearch_for_analysis_tasks(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    decision = service.decide(prompt="请分析当前记忆层设计的风险和方案", metadata={})

    assert decision.route == "autoresearch"
    assert decision.selected_worker == "autoresearch"
    assert decision.requires_approval is False
    assert decision.allowed_paths == ["docs/worker_notes.md"]


def test_worker_orchestrator_selects_chain_for_analysis_then_fix(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    decision = service.decide(
        prompt="先分析 src/demo_fix.py 的问题，再修复这个 bug 并补测试",
        metadata={},
    )

    assert decision.route == "autoresearch_then_openhands"
    assert decision.worker_chain == ["autoresearch", "openhands"]
    assert "src/demo_fix.py" in decision.allowed_paths


def test_worker_orchestrator_requires_approval_for_main_branch_write(tmp_path: Path) -> None:
    service = _build_service(tmp_path)

    decision = service.decide(
        prompt="请修复 src/demo_fix.py 并直接合并到 main",
        metadata={},
    )

    assert decision.route == "openhands"
    assert decision.requires_approval is True
    assert decision.approval_reason is not None
