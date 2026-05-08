from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoresearch.api import dependencies as api_dependencies
from autoresearch.api.main import create_app
from autoresearch.api.routers.packages import router as packages_router
from autoresearch.api.settings import clear_settings_caches


def test_personal_packages_default_to_installed_but_disabled(monkeypatch) -> None:
    monkeypatch.delenv("AUTORESEARCH_ENABLED_PERSONAL_PACKAGES", raising=False)
    clear_settings_caches()
    app = FastAPI()
    app.include_router(packages_router)

    response = TestClient(app).get("/api/v2/packages")

    assert response.status_code == 200
    packages = {item["package_id"]: item for item in response.json()}
    assert packages["personal.study_workspace"]["installed"] is True
    assert packages["personal.study_workspace"]["enabled"] is False
    assert packages["personal.study_workspace"]["route_prefixes"] == [
        "/api/v1/study-dashboard",
        "/api/v1/study-workbench",
    ]
    assert packages["personal.entertainment_curator"]["installed"] is True
    assert packages["personal.entertainment_curator"]["enabled"] is False
    assert packages["personal.entertainment_curator"]["capability_ids"] == ["entertainment_curator"]
    assert packages["personal.life_companion"]["installed"] is True
    assert packages["personal.life_companion"]["enabled"] is False
    assert packages["personal.life_companion"]["route_prefixes"] == ["/api/v1/personal"]
    assert packages["personal.life_companion"]["dependencies"] == [
        "personal.study_workspace",
        "personal.entertainment_curator",
    ]


def test_personal_package_routes_are_not_mounted_when_disabled(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AUTORESEARCH_ENABLED_PERSONAL_PACKAGES", raising=False)
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(tmp_path / "api.sqlite3"))
    clear_settings_caches()
    api_dependencies.get_life_companion_service.cache_clear()

    client = TestClient(create_app())

    assert client.get("/api/v1/study-workbench/health").status_code == 404
    assert client.get("/api/v1/study-dashboard/state").status_code == 404
    assert client.get("/api/v1/auth/youtube/profiles").status_code == 404
    assert client.get("/api/v1/personal/state").status_code == 404


def test_personal_package_routes_mount_when_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_ENABLED_PERSONAL_PACKAGES",
        "personal.study_workspace,personal.entertainment_curator",
    )
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(tmp_path / "api.sqlite3"))
    clear_settings_caches()
    api_dependencies.get_life_companion_service.cache_clear()

    client = TestClient(create_app())

    assert client.get("/api/v1/study-workbench/health").status_code == 200
    assert client.get("/api/v1/study-dashboard/state").status_code == 200
    assert client.get("/api/v1/auth/youtube/profiles").status_code == 200


def test_life_companion_route_reports_missing_dependencies(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AUTORESEARCH_ENABLED_PERSONAL_PACKAGES", "personal.life_companion")
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(tmp_path / "api.sqlite3"))
    clear_settings_caches()
    api_dependencies.get_life_companion_service.cache_clear()

    client = TestClient(create_app())

    response = client.get("/api/v1/personal/state")
    assert response.status_code == 200
    assert response.json()["status"] == "missing_dependency"


def test_life_companion_route_mounts_when_enabled_with_dependencies(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(
        "AUTORESEARCH_ENABLED_PERSONAL_PACKAGES",
        "personal.study_workspace,personal.entertainment_curator,personal.life_companion",
    )
    monkeypatch.setenv("AUTORESEARCH_API_DB_PATH", str(tmp_path / "api.sqlite3"))
    clear_settings_caches()
    api_dependencies.get_life_companion_service.cache_clear()

    client = TestClient(create_app())

    response = client.get("/api/v1/personal/state")
    assert response.status_code == 200
    assert response.json()["enabled"] is True
