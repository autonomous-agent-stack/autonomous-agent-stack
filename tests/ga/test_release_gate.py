from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from autoresearch.api.routers.connectors import router as connectors_router
from autoresearch.api.routers.ga import router as ga_router
from autoresearch.api.routers.health_evergreen import router as health_router
from autoresearch.api.routers.models import router as models_router
from autoresearch.api.routers.packages import router as packages_router
from autoresearch.api.routers.secrets import router as secrets_router
from autoresearch.core.services.release_gate import ReleaseGateService


ROOT = Path(__file__).resolve().parents[2]


def test_release_gate_fails_without_full_ga_evidence() -> None:
    report = ReleaseGateService(repo_root=ROOT).run()

    assert report.status == "failed"
    assert {check.check_id for check in report.checks} >= {
        "ga.required_docs",
        "ga.gap_report",
        "ga.adapter_certification",
        "ga.bypass_ga",
        "ga.storage_profiles",
        "ga.postgres_event_store",
        "ga.runtime_isolation",
        "ga.connector_registry",
        "ga.v1_compat_shims",
        "ga.direct_secret_model_tool_paths",
        "ga.furniture_e2e",
        "ga.external_write_dry_run",
    }
    failed = {check.check_id for check in report.failed_checks}
    assert "ga.adapter_certification" in failed
    assert "ga.direct_secret_model_tool_paths" in failed


def test_v2_ga_surfaces_are_real_api_routes() -> None:
    app = FastAPI()
    for router in (ga_router, models_router, secrets_router, connectors_router, packages_router, health_router):
        app.include_router(router)
    client = TestClient(app)

    assert client.get("/api/v2/ga/adapters").status_code == 200
    assert client.get("/api/v2/models/providers").status_code == 200
    assert client.get("/api/v2/connectors").status_code == 200
    assert client.get("/api/v2/packages").status_code == 200
    assert client.get("/api/v2/health/evergreen").status_code == 200
