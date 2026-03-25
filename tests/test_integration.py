from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import (
    get_evaluation_service,
    get_execution_service,
    get_experiment_service,
    get_optimization_service,
    get_report_service,
    get_variant_service,
)
from autoresearch.api.main import app
from autoresearch.core.repositories import SQLiteEvaluationRepository
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.core.services.executions import ExecutionService
from autoresearch.core.services.reports import ReportService
from autoresearch.core.services.variants import VariantService
from autoresearch.shared.models import ExecutionRead, ExperimentRead, OptimizationRead, ReportRead, VariantRead
from autoresearch.shared.store import SQLiteModelRepository
from autoresearch.train.services.experiments import ExperimentService
from autoresearch.train.services.optimizations import OptimizationService


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "integration.sqlite3"

    app.dependency_overrides[get_evaluation_service] = lambda: EvaluationService(
        repository=SQLiteEvaluationRepository(db_path=db_path),
        repo_root=tmp_path,
    )
    app.dependency_overrides[get_variant_service] = lambda: VariantService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="variant_runs_it",
            model_cls=VariantRead,
        )
    )
    app.dependency_overrides[get_report_service] = lambda: ReportService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="report_runs_it",
            model_cls=ReportRead,
        )
    )
    app.dependency_overrides[get_optimization_service] = lambda: OptimizationService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="optimization_runs_it",
            model_cls=OptimizationRead,
        )
    )
    app.dependency_overrides[get_experiment_service] = lambda: ExperimentService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="experiment_runs_it",
            model_cls=ExperimentRead,
        )
    )
    app.dependency_overrides[get_execution_service] = lambda: ExecutionService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="execution_runs_it",
            model_cls=ExecutionRead,
        ),
        repo_root=tmp_path,
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_generator_api_contract(client: TestClient) -> None:
    response = client.post(
        "/api/v1/generators",
        json={
            "base_prompt": "Write a test plan",
            "strategy_hint": "baseline",
            "max_variants": 2,
        },
    )
    assert response.status_code == 202
    payload = response.json()
    generator_id = payload["variant_id"]
    assert payload["status"] == "completed"

    fetched = client.get(f"/api/v1/generators/{generator_id}")
    assert fetched.status_code == 200
    assert fetched.json()["variant_id"] == generator_id

    listed = client.get("/api/v1/generators")
    assert listed.status_code == 200
    assert len(listed.json()) >= 1


def test_synthesis_api_contract(client: TestClient) -> None:
    response = client.post(
        "/api/v1/synthesis",
        json={
            "format": "markdown",
            "sections": ["summary", "metrics"],
            "metadata": {"source": "integration_test"},
        },
    )
    assert response.status_code == 202
    payload = response.json()
    synthesis_id = payload["report_id"]
    assert payload["status"] == "completed"

    fetched = client.get(f"/api/v1/synthesis/{synthesis_id}")
    assert fetched.status_code == 200
    assert fetched.json()["report_id"] == synthesis_id


def test_loop_control_api_contract(client: TestClient) -> None:
    response = client.post(
        "/api/v1/loops",
        json={
            "experiment_id": "exp_demo",
            "objective": "maximize quality",
            "max_iterations": 8,
        },
    )
    assert response.status_code == 202
    payload = response.json()
    loop_id = payload["optimization_id"]
    assert payload["status"] == "queued"

    fetched = client.get(f"/api/v1/loops/{loop_id}")
    assert fetched.status_code == 200
    assert fetched.json()["optimization_id"] == loop_id


def test_executor_api_runs_command(client: TestClient) -> None:
    response = client.post(
        "/api/v1/executors",
        json={
            "name": "echo_test",
            "command": [sys.executable, "-c", "print('executor-ok')"],
            "timeout_seconds": 5,
            "work_dir": ".",
        },
    )
    assert response.status_code == 202
    payload = response.json()
    execution_id = payload["execution_id"]
    assert payload["status"] == "queued"

    final_payload = None
    for _ in range(20):
        fetched = client.get(f"/api/v1/executors/{execution_id}")
        assert fetched.status_code == 200
        final_payload = fetched.json()
        if final_payload["status"] in {"completed", "failed"}:
            break
        time.sleep(0.05)

    assert final_payload is not None
    assert final_payload["status"] == "completed"
    assert final_payload["returncode"] == 0
    assert "executor-ok" in (final_payload["stdout_preview"] or "")


def test_sse_health_endpoint(client: TestClient) -> None:
    response = client.get(
        "/api/v1/stream/health",
        params={"interval_seconds": 0.01, "limit": 2},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: ready" in response.text
    assert "event: heartbeat" in response.text
    assert "event: complete" in response.text
