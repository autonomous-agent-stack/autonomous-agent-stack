from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_evaluation_service
from autoresearch.api.main import app
from autoresearch.core.repositories import SQLiteEvaluationRepository
from autoresearch.core.services.evaluations import EvaluationService


def test_health_endpoints_return_ok() -> None:
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/healthz").status_code == 200
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/healthz").json() == {"status": "ok"}


def test_create_and_read_evaluation_with_current_contract(tmp_path: Path) -> None:
    task_path = tmp_path / "task.json"
    task_path.write_text(
        json.dumps(
            {
                "name": "api-real",
                "evaluate": {
                    "command": ["__PYTHON__", "-c", "import json, os; open(os.environ['AUTORESEARCH_OUTPUT_JSON'], 'w').write('{\"score\": 1, \"status\": \"pass\", \"summary\": \"ok\"}')"],
                    "timeout_seconds": 10,
                    "score_direction": "maximize",
                },
                "artifacts_dir": "artifacts/api-real",
            }
        ),
        encoding="utf-8",
    )

    service = EvaluationService(
        repository=SQLiteEvaluationRepository(db_path=tmp_path / "evaluations.sqlite3"),
        repo_root=tmp_path,
    )
    app.dependency_overrides[get_evaluation_service] = lambda: service

    try:
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/evaluations",
                json={
                    "task_name": "api_real",
                    "config_path": str(task_path),
                    "description": "integration smoke",
                },
            )
            assert created.status_code == 202
            body = created.json()
            assert "evaluation_id" in body
            assert body["status"] == "queued"

            evaluation_id = body["evaluation_id"]
            fetched = client.get(f"/api/v1/evaluations/{evaluation_id}")
            assert fetched.status_code == 200
            assert fetched.json()["evaluation_id"] == evaluation_id
    finally:
        app.dependency_overrides.clear()
