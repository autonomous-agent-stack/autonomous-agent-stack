from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_evaluation_service
from autoresearch.api.main import app
from autoresearch.core.repositories import SQLiteEvaluationRepository
from autoresearch.core.services.evaluations import EvaluationService
from autoresearch.shared.models import EvaluationCreateRequest


def test_get_evaluation_returns_persisted_record(tmp_path: Path) -> None:
    service = EvaluationService(
        repository=SQLiteEvaluationRepository(db_path=tmp_path / "evaluations.sqlite3"),
        repo_root=tmp_path,
    )
    created = service.create(
        EvaluationCreateRequest(
            task_name="demo-task",
            config_path=str(tmp_path / "task.json"),
            description="api lookup",
        )
    )
    app.dependency_overrides[get_evaluation_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get(f"/api/v1/evaluations/{created.evaluation_id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["evaluation_id"] == created.evaluation_id
    assert body["status"] == "queued"
    assert body["description"] == "api lookup"
