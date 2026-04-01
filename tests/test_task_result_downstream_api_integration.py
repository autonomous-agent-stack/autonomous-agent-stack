"""Integration tests for downstream task APIs consuming unified run/gate data.

These tests dispatch real Linux supervisor tasks through the existing API
surfaces and assert that downstream task-reading endpoints start surfacing
selected unified fields from the persisted ``result_payload`` while keeping
their legacy response models unchanged.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import (
    get_agent_package_registry_service,
    get_approval_store_service,
    get_control_plane_service,
    get_linux_supervisor_service,
    get_manager_agent_service,
    get_openclaw_compat_service,
    get_openclaw_memory_service,
    get_personal_housekeeper_service,
    get_worker_registry_service,
)
from autoresearch.api.main import app
from tests.test_housekeeper import _build_services, _seed_agent_package_tree
from tests.test_linux_run_lifecycle_integration import (
    _linux_infra_error_helper,
    _linux_success_helper,
    _linux_timeout_helper,
    _linux_unknown_helper,
)


def _install_service_overrides(services: dict[str, object]) -> None:
    app.dependency_overrides[get_openclaw_compat_service] = lambda: services["openclaw"]
    app.dependency_overrides[get_openclaw_memory_service] = lambda: services["memory"]
    app.dependency_overrides[get_manager_agent_service] = lambda: services["manager"]
    app.dependency_overrides[get_linux_supervisor_service] = lambda: services["linux"]
    app.dependency_overrides[get_agent_package_registry_service] = lambda: services["packages"]
    app.dependency_overrides[get_worker_registry_service] = lambda: services["workers"]
    app.dependency_overrides[get_approval_store_service] = lambda: services["approval"]
    app.dependency_overrides[get_control_plane_service] = lambda: services["control"]
    app.dependency_overrides[get_personal_housekeeper_service] = lambda: services["housekeeper"]


def _create_linux_housekeeper_task(client: TestClient) -> dict[str, object]:
    session = client.post(
        "/api/v1/openclaw/sessions",
        json={"channel": "api", "title": "linux", "scope": "personal", "metadata": {}},
    )
    assert session.status_code == 201
    session_id = session.json()["session_id"]

    response = client.post(
        "/api/v1/openclaw/housekeeper/dispatch",
        json={
            "session_id": session_id,
            "message": "请巡检一下 Linux 服务状态并收集最近错误日志。",
        },
    )
    assert response.status_code == 202
    return response.json()


@pytest.mark.parametrize(
    (
        "helper_factory",
        "expected_task_status",
        "expected_run_status",
        "expected_outcome",
        "expected_action",
    ),
    [
        (_linux_success_helper, "completed", "succeeded", "success", "accept"),
        (_linux_timeout_helper, "failed", "failed", "timeout", "retry"),
        (_linux_unknown_helper, "failed", "needs_review", "needs_human_confirm", "needs_review"),
        (_linux_infra_error_helper, "failed", "failed", "needs_human_confirm", "needs_review"),
    ],
)
def test_control_plane_task_detail_consumes_run_and_gate_metadata(
    tmp_path: Path,
    helper_factory,
    expected_task_status: str,
    expected_run_status: str,
    expected_outcome: str,
    expected_action: str,
) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper.sqlite3"
    helper = helper_factory(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)
    _install_service_overrides(services)

    try:
        with TestClient(app) as client:
            dispatched = _create_linux_housekeeper_task(client)
            control_plane_task_id = dispatched["control_plane_task_id"]

            response = client.get(f"/api/v1/control-plane/tasks/{control_plane_task_id}")
            assert response.status_code == 200
            payload = response.json()

        assert payload["status"] == expected_task_status
        assert payload["agent_package_id"] == "linux_housekeeping_agent_v0"
        assert payload["selected_worker_id"] == "linux_housekeeper"
        assert payload["metadata"]["run_status"] == expected_run_status
        assert payload["metadata"]["gate_outcome"] == expected_outcome
        assert payload["metadata"]["gate_action"] == expected_action
        assert payload["result_payload"]["run_record"]["run_status"] == expected_run_status
        assert payload["result_payload"]["gate_evaluation"]["gate_outcome"] == expected_outcome
        assert payload["result_payload"]["gate_evaluation"]["gate_action"] == expected_action
        assert "conclusion" in payload["result_payload"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize(
    (
        "helper_factory",
        "expected_task_status",
        "expected_run_status",
        "expected_outcome",
        "expected_action",
    ),
    [
        (_linux_success_helper, "completed", "succeeded", "success", "accept"),
        (_linux_timeout_helper, "failed", "failed", "timeout", "retry"),
        (_linux_unknown_helper, "failed", "needs_review", "needs_human_confirm", "needs_review"),
        (_linux_infra_error_helper, "failed", "failed", "needs_human_confirm", "needs_review"),
    ],
)
def test_housekeeper_task_detail_consumes_run_and_gate_metadata_without_breaking_legacy_fields(
    tmp_path: Path,
    helper_factory,
    expected_task_status: str,
    expected_run_status: str,
    expected_outcome: str,
    expected_action: str,
) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper.sqlite3"
    helper = helper_factory(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)
    _install_service_overrides(services)

    try:
        with TestClient(app) as client:
            dispatched = _create_linux_housekeeper_task(client)
            task_id = dispatched["task_id"]

            response = client.get(f"/api/v1/openclaw/housekeeper/tasks/{task_id}")
            assert response.status_code == 200
            payload = response.json()

        assert payload["status"] == expected_task_status
        assert payload["control_plane_task_id"] == dispatched["control_plane_task_id"]
        assert payload["agent_package_id"] == "linux_housekeeping_agent_v0"
        assert payload["backend_kind"] == "linux_supervisor"
        assert payload["source_message"] == "请巡检一下 Linux 服务状态并收集最近错误日志。"
        assert payload["metadata"]["dry_run"] is False
        assert payload["metadata"]["run_status"] == expected_run_status
        assert payload["metadata"]["gate_outcome"] == expected_outcome
        assert payload["metadata"]["gate_action"] == expected_action
        assert payload["result_payload"]["run_record"]["run_status"] == expected_run_status
        assert payload["result_payload"]["gate_evaluation"]["gate_outcome"] == expected_outcome
        assert payload["result_payload"]["gate_evaluation"]["gate_action"] == expected_action
    finally:
        app.dependency_overrides.clear()


def test_housekeeper_task_detail_preserves_result_payload_and_summary_fields(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    db_path = tmp_path / "housekeeper.sqlite3"
    helper = _linux_success_helper(tmp_path / "linux_worker.py")
    _seed_agent_package_tree(repo_root)
    services = _build_services(repo_root, db_path, helper)
    _install_service_overrides(services)

    try:
        with TestClient(app) as client:
            dispatched = _create_linux_housekeeper_task(client)
            response = client.get(f"/api/v1/openclaw/housekeeper/tasks/{dispatched['task_id']}")
            assert response.status_code == 200
            payload = response.json()

        assert payload["result_summary"] is not None
        assert payload["result_payload"]["run_record"]["result_data"]["conclusion"] == "succeeded"
        assert "gate_evaluation" in payload["result_payload"]
        assert "run_record" in payload["result_payload"]
        assert "artifacts" in payload["result_payload"]
    finally:
        app.dependency_overrides.clear()
