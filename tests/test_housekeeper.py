from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from autoresearch.agent_protocol.models import DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.housekeeper import HousekeeperService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.housekeeper_contract import (
    HousekeeperChangeReason,
    HousekeeperMode,
    HousekeeperModeUpdateRequest,
)
from autoresearch.shared.manager_agent_contract import ManagerDispatchRequest
from autoresearch.shared.models import ApprovalRequestCreateRequest
from autoresearch.shared.store import InMemoryRepository


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _seed_admin_dashboard_repo(repo_root: Path) -> None:
    _write(repo_root / "panel" / "app.tsx", "export const App = () => null;\n")
    _write(repo_root / "src" / "autoresearch" / "api" / "routers" / "panel.py", "router = object()\n")
    _write(repo_root / "src" / "autoresearch" / "api" / "routers" / "admin.py", "router = object()\n")
    _write(repo_root / "src" / "autoresearch" / "core" / "services" / "metrics_dashboard.py", "def ok():\n    return True\n")
    _write(repo_root / "tests" / "test_panel_security.py", "def test_ok():\n    assert True\n")
    _write(repo_root / "tests" / "test_admin_managed_skills.py", "def test_admin_ok():\n    assert True\n")


def _successful_run_summary(job: JobSpec) -> RunSummary:
    return RunSummary(
        run_id=job.run_id,
        final_status="ready_for_promotion",
        driver_result=DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status="succeeded",
            summary="ok",
            changed_paths=list(job.policy.allowed_paths),
            recommended_action="promote",
        ),
        validation=ValidationReport(run_id=job.run_id, passed=True),
        promotion_patch_uri="/tmp/demo.patch",
    )


def _service() -> HousekeeperService:
    return HousekeeperService(
        state_repository=InMemoryRepository(),
        budget_repository=InMemoryRepository(),
        exploration_repository=InMemoryRepository(),
    )


def test_housekeeper_manual_override_replaces_prior_override() -> None:
    service = _service()
    base_now = datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc)
    state = service.get_state(now=base_now)
    assert state.scheduled_mode is HousekeeperMode.DAY_SAFE

    first = service.update_mode(
        HousekeeperModeUpdateRequest(
            action="set_manual_override",
            target_mode=HousekeeperMode.NIGHT_READONLY_EXPLORE,
            changed_by="test",
            reason=HousekeeperChangeReason.MANUAL_API,
        ),
        now=base_now,
    )
    assert first.manual_override_mode is HousekeeperMode.NIGHT_READONLY_EXPLORE
    assert first.effective_mode is HousekeeperMode.NIGHT_READONLY_EXPLORE

    replaced = service.update_mode(
        HousekeeperModeUpdateRequest(
            action="set_manual_override",
            target_mode=HousekeeperMode.DAY_SAFE,
            changed_by="test",
            reason=HousekeeperChangeReason.MANUAL_API,
        ),
        now=base_now,
    )
    assert replaced.manual_override_mode is HousekeeperMode.DAY_SAFE
    assert replaced.effective_mode is HousekeeperMode.DAY_SAFE


def test_housekeeper_prepare_manager_request_defers_heavy_dispatch_in_day_mode(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_admin_dashboard_repo(repo_root)
    manager_service = ManagerAgentService(repository=InMemoryRepository(), repo_root=repo_root)
    housekeeper = _service()

    prepared, assessment, state = housekeeper.prepare_manager_request(
        ManagerDispatchRequest(
            prompt="在 Admin Panel 里加一个带图表的实时服务器资源监控大屏。",
            auto_dispatch=True,
        ),
        manager_service=manager_service,
        trigger_source="test",
        now=datetime(2026, 3, 31, 12, 0, tzinfo=timezone.utc),
    )

    assert state.effective_mode is HousekeeperMode.DAY_SAFE
    assert assessment.plan_shape == "task_dag"
    assert assessment.fanout_count == 3
    assert prepared.auto_dispatch is False
    assert prepared.pipeline_target == "patch"
    assert prepared.metadata["deferred_reason"] == "deferred_to_night"
    assert prepared.metadata["execution_profile"]["profile_name"] == "day_safe"


def test_housekeeper_morning_summary_uses_four_sections(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_admin_dashboard_repo(repo_root)
    manager_service = ManagerAgentService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
        dispatch_runner=_successful_run_summary,
    )
    dispatch = manager_service.create_dispatch(
        ManagerDispatchRequest(
            prompt="在 Admin Panel 里加一个带图表的实时服务器资源监控大屏。",
            auto_dispatch=False,
        )
    )
    manager_service.execute_dispatch(dispatch.dispatch_id)

    approval_service = ApprovalStoreService(repository=InMemoryRepository())
    approval_service.create_request(
        ApprovalRequestCreateRequest(
            title="Review manager result",
            telegram_uid="10001",
        )
    )
    housekeeper = _service()
    summary = housekeeper.create_morning_summary(
        manager_service=manager_service,
        planner_service=type("PlannerStub", (), {"list": lambda self: [], "list_pending": lambda self, limit=20: []})(),
        approval_service=approval_service,
        notifier=TelegramNotifierService(bot_token=None),
        media_jobs=[],
        now=datetime(2026, 4, 1, 0, 30, tzinfo=timezone.utc),
    )

    assert "昨夜完成了什么" in summary.summary_text
    assert "失败/阻塞了什么" in summary.summary_text
    assert "今天需要你决定什么" in summary.summary_text
    assert "系统当前模式与待执行队列" in summary.summary_text
    assert summary.decision_items
