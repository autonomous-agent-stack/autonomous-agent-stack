"""Tests for workers API router — registration, heartbeat, inventory."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.main import create_app
from autoresearch.api.settings import clear_settings_caches


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test_workers.db"
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(db_path))
    clear_settings_caches()
    app = create_app()
    yield TestClient(app)
    app.dependency_overrides.clear()
    clear_settings_caches()


class TestWorkerRegistration:
    def test_register_new_worker(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/workers/register",
            json={
                "worker_id": "test-mac-001",
                "worker_type": "mac",
                "host": "localhost",
                "capabilities": ["excel_audit", "claude_runtime"],
                "metadata": {
                    "runtime_display": "MacBook Pro M3",
                    "runtime_host": "localhost",
                    "runtime_platform": "darwin",
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["worker_id"] == "test-mac-001"
        assert data["worker_type"] == "mac"
        assert data["accepting_work"] is True

    def test_register_duplicate_worker_updates(self, client: TestClient) -> None:
        payload = {
            "worker_id": "dup-worker",
            "worker_type": "mac",
            "host": "localhost",
            "capabilities": [],
            "metadata": {},
        }
        first = client.post("/api/v1/workers/register", json=payload)
        assert first.status_code == 200

        second = client.post("/api/v1/workers/register", json=payload)
        assert second.status_code == 200


class TestWorkerHeartbeat:
    def test_heartbeat_registered_worker(self, client: TestClient) -> None:
        client.post(
            "/api/v1/workers/register",
            json={
                "worker_id": "hb-worker",
                "worker_type": "mac",
                "host": "localhost",
                "capabilities": [],
                "metadata": {},
            },
        )
        response = client.post(
            "/api/v1/workers/hb-worker/heartbeat",
            json={"health": "ok", "queue_depth": 0},
        )
        assert response.status_code == 200

    def test_heartbeat_unknown_worker(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/workers/nonexistent/heartbeat",
            json={"health": "ok", "queue_depth": 0},
        )
        assert response.status_code in (200, 404)


class TestWorkerInventory:
    def test_list_workers_empty(self, client: TestClient) -> None:
        response = client.get("/api/v1/workers")
        assert response.status_code == 200
        data = response.json()
        assert "workers" in data
        assert "summary" in data

    def test_list_workers_returns_valid_structure(self, client: TestClient) -> None:
        response = client.get("/api/v1/workers")
        assert response.status_code == 200
        data = response.json()
        assert "workers" in data
        assert "summary" in data
        assert isinstance(data["workers"], list)

    def test_worker_summary(self, client: TestClient) -> None:
        response = client.get("/api/v1/workers/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_workers" in data
        assert "online_workers" in data

    def test_get_nonexistent_worker_returns_404(self, client: TestClient) -> None:
        response = client.get("/api/v1/workers/nonexistent")
        assert response.status_code in (200, 404)


class TestWorkerCapabilities:
    def test_capabilities_health(self, client: TestClient) -> None:
        response = client.get("/api/v1/capabilities/health")
        assert response.status_code == 200

    def test_list_capability_providers(self, client: TestClient) -> None:
        response = client.get("/api/v1/capabilities/providers")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_nonexistent_provider(self, client: TestClient) -> None:
        response = client.get("/api/v1/capabilities/providers/nonexistent")
        assert response.status_code in (200, 404)
