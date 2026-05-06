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


def test_release_gate_passes_when_no_uncertified_stable_claims_exist() -> None:
    report = ReleaseGateService(repo_root=ROOT).run()

    assert report.status == "passed"
    assert {check.check_id for check in report.checks} >= {
        "ga.required_docs",
        "ga.adapter_certification",
        "ga.storage_profiles",
        "ga.runtime_isolation",
        "ga.connector_registry",
    }


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

