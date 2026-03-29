from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from autoresearch.agent_protocol.models import DriverResult, JobSpec, RunSummary, ValidationReport
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.api.dependencies import get_manager_agent_service
from autoresearch.api.main import app
from autoresearch.shared.manager_agent_contract import (
    ManagerDispatchRequest,
    ManagerPlanStrategy,
)
from autoresearch.shared.models import JobStatus
from autoresearch.shared.store import InMemoryRepository


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _successful_run_summary(job: JobSpec) -> RunSummary:
    return RunSummary(
        run_id=job.run_id,
        final_status="ready_for_promotion",
        driver_result=DriverResult(
            run_id=job.run_id,
            agent_id=job.agent_id,
            status="succeeded",
            summary="manager dispatch completed successfully",
            changed_paths=list(job.policy.allowed_paths),
            recommended_action="promote",
        ),
        validation=ValidationReport(run_id=job.run_id, passed=True),
        promotion_patch_uri="/tmp/manager-dispatch.patch",
    )


def _seed_basic_panel_repo(repo_root: Path) -> None:
    _write(repo_root / "panel" / "app.tsx", "export const App = () => null;\n")
    _write(repo_root / "src" / "autoresearch" / "api" / "routers" / "panel.py", "router = object()\n")
    _write(repo_root / "src" / "autoresearch" / "api" / "routers" / "openclaw.py", "router = object()\n")
    _write(repo_root / "tests" / "test_panel_security.py", "def test_ok():\n    assert True\n")


def _seed_admin_dashboard_repo(repo_root: Path) -> None:
    _seed_basic_panel_repo(repo_root)
    _write(repo_root / "src" / "autoresearch" / "api" / "routers" / "admin.py", "router = object()\n")
    _write(
        repo_root / "src" / "autoresearch" / "core" / "services" / "metrics_dashboard.py",
        "def collect_metrics() -> dict[str, int]:\n    return {'cpu': 1}\n",
    )
    _write(repo_root / "tests" / "test_admin_managed_skills.py", "def test_admin_ok():\n    assert True\n")


def test_manager_agent_translates_fuzzy_game_prompt_into_worker_contract(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_basic_panel_repo(repo_root)

    service = ManagerAgentService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
    )

    dispatch = service.create_dispatch(
        ManagerDispatchRequest(
            prompt="我想做个小游戏，先在现有 panel 里做一个最小可玩的版本。",
            auto_dispatch=False,
        )
    )

    assert dispatch.status is JobStatus.CREATED
    assert dispatch.selected_intent is not None
    assert dispatch.selected_intent.intent_id == "game_prototype"
    assert dispatch.execution_plan is not None
    assert dispatch.execution_plan.strategy is ManagerPlanStrategy.SINGLE_TASK
    assert len(dispatch.execution_plan.tasks) == 1
    assert "panel/**" in dispatch.worker_spec.allowed_paths
    assert "tests/test_panel_security.py" in dispatch.worker_spec.allowed_paths
    assert dispatch.worker_spec.test_command == "pytest -q tests/test_panel_security.py"
    assert dispatch.agent_job is not None
    assert dispatch.agent_job.metadata["manager_intent_label"] == "game_prototype"
    assert "小游戏" in dispatch.worker_spec.metadata["manager_prompt"]


def test_manager_agent_decomposes_complex_prompt_into_task_dag(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_admin_dashboard_repo(repo_root)

    service = ManagerAgentService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
    )

    dispatch = service.create_dispatch(
        ManagerDispatchRequest(
            prompt="在 Admin Panel 里加一个带图表的实时服务器资源监控大屏。",
            auto_dispatch=False,
        )
    )

    assert dispatch.execution_plan is not None
    assert dispatch.execution_plan.strategy is ManagerPlanStrategy.TASK_DAG
    assert len(dispatch.execution_plan.tasks) == 3

    backend_task, tests_task, frontend_task = dispatch.execution_plan.tasks
    assert backend_task.stage.value == "backend"
    assert tests_task.stage.value == "tests"
    assert frontend_task.stage.value == "frontend"
    assert tests_task.depends_on == [backend_task.task_id]
    assert frontend_task.depends_on == [backend_task.task_id, tests_task.task_id]
    assert any(path.startswith("src/autoresearch/api/routers/admin.py") for path in backend_task.worker_spec.allowed_paths)
    assert tests_task.worker_spec.allowed_paths == [
        "tests/test_panel_security.py",
        "tests/test_admin_managed_skills.py",
    ]
    assert "panel/**" in frontend_task.worker_spec.allowed_paths
    assert frontend_task.worker_spec.metadata["manager_task_stage"] == "frontend"


def test_manager_agent_api_dispatch_executes_background_plan(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    _seed_admin_dashboard_repo(repo_root)

    service = ManagerAgentService(
        repository=InMemoryRepository(),
        repo_root=repo_root,
        dispatch_runner=_successful_run_summary,
    )

    app.dependency_overrides[get_manager_agent_service] = lambda: service
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agents/manager/dispatch",
            json={"prompt": "在 Admin Panel 里加一个带图表的实时服务器资源监控大屏。"},
        )
        assert response.status_code == 202
        payload = response.json()
        assert payload["status"] == "queued"
        dispatch_id = payload["dispatch_id"]

        get_response = client.get(f"/api/v1/agents/manager/dispatches/{dispatch_id}")
        assert get_response.status_code == 200
        current = get_response.json()

    app.dependency_overrides.clear()

    assert current["status"] == "completed"
    assert current["run_summary"]["final_status"] == "ready_for_promotion"
    assert current["execution_plan"]["strategy"] == "task_dag"
    assert len(current["execution_plan"]["tasks"]) == 3
    assert all(task["status"] == "completed" for task in current["execution_plan"]["tasks"])
    assert current["execution_plan"]["tasks"][0]["run_summary"]["final_status"] == "ready_for_promotion"
    assert current["execution_plan"]["tasks"][2]["metadata"]["manager_stage"] == "frontend"
