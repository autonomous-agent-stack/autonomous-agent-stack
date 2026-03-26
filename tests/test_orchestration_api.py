from __future__ import annotations

from fastapi.testclient import TestClient

from autoresearch.api.main import app


def test_orchestration_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/orchestration/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert "prompt/execute" in payload["entrypoints"]


def test_prompt_execute_endpoint_completes_graph() -> None:
    prompt = """
goal: 生成一个最小执行计划
nodes: planner -> generator -> executor -> evaluator
retry: evaluator -> generator when decision == 'retry'
max_steps: 12
max_concurrency: 3
"""
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orchestration/prompt/execute",
            json={
                "prompt": prompt,
                "max_concurrency": 3,
                "context": {"timestamp": "2026-03-26T00:00:00Z"},
                "include_graph": True,
            },
        )
        assert response.status_code == 200
        payload = response.json()

    assert payload["status"] == "completed"
    assert payload["goal"] == "生成一个最小执行计划"
    assert payload["max_steps"] == 12
    assert payload["max_concurrency"] == 3
    assert set(payload["results"].keys()) == {"planner", "generator", "executor", "evaluator"}
    assert payload["graph"]["graph_id"] == payload["graph_id"]


def test_prompt_execute_endpoint_returns_failed_when_step_budget_too_small() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/orchestration/prompt/execute",
            json={
                "prompt": "goal: 预算不足测试",
                "max_steps": 1,
            },
        )
        assert response.status_code == 200
        payload = response.json()

    assert payload["status"] == "failed"
    assert payload["error"] is not None
    assert "max_steps=1" in payload["error"]
