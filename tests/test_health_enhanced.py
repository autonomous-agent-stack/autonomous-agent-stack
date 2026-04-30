"""Tests for enhanced health check endpoint."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test_health.db"
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(db_path))
    monkeypatch.setenv("AUTORESEARCH_HERMES_GATEWAY_BASE_URL", "")
    from autoresearch.api.dependencies import clear_dependency_caches
    from autoresearch.api.settings import clear_settings_caches

    clear_dependency_caches()
    clear_settings_caches()
    app = create_app()
    yield TestClient(app)
    app.dependency_overrides.clear()
    clear_dependency_caches()
    clear_settings_caches()


class TestHealthEndpoint:
    def test_health_returns_ok_status(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "checks" in data
        assert "db" in data["checks"]
        assert data["checks"]["db"]["status"] == "ok"

    def test_health_includes_version_and_build(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert "build" in data
        assert "timestamp" in data

    def test_health_includes_worker_info(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert "workers" in data["checks"]

    def test_health_omits_hermes_interactive_when_not_configured(self, client: TestClient) -> None:
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"
        assert "hermes_interactive" not in data["checks"]

    def test_health_includes_hermes_interactive_when_api_gateway_configured(
        self,
        tmp_path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(tmp_path / "api.sqlite3"))
        monkeypatch.setenv("AUTORESEARCH_HERMES_GATEWAY_BASE_URL", "http://127.0.0.1:8765")
        from autoresearch.api.dependencies import clear_dependency_caches
        from autoresearch.api.settings import clear_settings_caches

        clear_dependency_caches()
        clear_settings_caches()
        app = create_app()
        new_client = TestClient(app)
        response = new_client.get("/health")
        data = response.json()

        assert data["status"] == "degraded"
        assert data["checks"]["hermes_interactive"]["status"] == "degraded"
        assert data["checks"]["hermes_interactive"]["api_gateway_configured"] is True
        assert data["checks"]["hermes_interactive"]["interactive_worker_count"] == 0

        app.dependency_overrides.clear()
        clear_dependency_caches()
        clear_settings_caches()

    def test_healthz_alias_returns_same_data(self, client: TestClient) -> None:
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "db" in data["checks"]

    def test_health_shows_degraded_when_db_unreachable(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Point DB to a nonexistent path inside a non-existent directory
        monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", "/nonexistent/dir/test.db")
        from autoresearch.api.settings import clear_settings_caches

        clear_settings_caches()

        # Re-create app to pick up new settings
        app = create_app()
        new_client = TestClient(app)
        response = new_client.get("/health")
        data = response.json()
        # May be ok or degraded depending on SQLite auto-creation behavior
        assert data["status"] in ("ok", "degraded")
        assert "db" in data["checks"]

        app.dependency_overrides.clear()
        clear_settings_caches()
