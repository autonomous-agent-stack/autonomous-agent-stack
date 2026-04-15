from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.paperclip_router import _budget_store, _callback_store, router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_budget_endpoint_records_in_memory_request() -> None:
    _budget_store.clear()

    with _client() as client:
        response = client.post(
            "/api/v1/paperclip/budget",
            json={"department": "Marketing", "target_budget": 12345.0},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert body["department"] == "Marketing"
    assert body["target_budget"] == 12345.0
    assert body["request_id"] in _budget_store
    assert _budget_store[body["request_id"]]["status"] == "accepted"


def test_callback_endpoint_records_metrics_in_memory() -> None:
    _callback_store.clear()

    with _client() as client:
        response = client.post(
            "/api/v1/paperclip/callback",
            json={
                "roi": 2.5,
                "token_used": 50000,
                "timestamp": "2026-03-25T23:15:00Z",
                "department": "Marketing",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "received"
    assert "ROI: 2.5x" in body["message"]
    assert len(_callback_store) == 1
    assert _callback_store[0]["department"] == "Marketing"


def test_debug_endpoints_expose_current_process_state() -> None:
    _budget_store.clear()
    _callback_store.clear()

    with _client() as client:
        budget = client.post(
            "/api/v1/paperclip/budget",
            json={"department": "Ops", "target_budget": 1000.0},
        ).json()
        client.post(
            "/api/v1/paperclip/callback",
            json={
                "roi": 1.2,
                "token_used": 2000,
                "timestamp": "2026-03-25T23:20:00Z",
            },
        )

        budgets_response = client.get("/api/v1/paperclip/budgets")
        callbacks_response = client.get("/api/v1/paperclip/callbacks")

    assert budgets_response.status_code == 200
    assert budgets_response.json()["total"] == 1
    assert budget["request_id"] in budgets_response.json()["budgets"]

    assert callbacks_response.status_code == 200
    assert callbacks_response.json()["total"] == 1


def test_default_main_app_does_not_mount_paperclip_router(monkeypatch) -> None:
    monkeypatch.setenv("AUTORESEARCH_MODE", "minimal")

    from autoresearch.api.main import create_app

    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/v1/paperclip/budget" not in paths
    assert "/api/v1/paperclip/callback" not in paths
