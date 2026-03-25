from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_self_integration_service
from autoresearch.api.main import app
from autoresearch.core.services.self_integration import SelfIntegrationService
from autoresearch.shared.models import (
    IntegrationDiscoveryRead,
    IntegrationPromotionRead,
    IntegrationPrototypeRead,
)
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def self_integration_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "self_integration.sqlite3"
    service = SelfIntegrationService(
        discovery_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="integration_discoveries_it",
            model_cls=IntegrationDiscoveryRead,
        ),
        prototype_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="integration_prototypes_it",
            model_cls=IntegrationPrototypeRead,
        ),
        promotion_repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="integration_promotions_it",
            model_cls=IntegrationPromotionRead,
        ),
    )
    app.dependency_overrides[get_self_integration_service] = lambda: service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_self_integration_discover_prototype_promote_flow(
    self_integration_client: TestClient,
) -> None:
    discovered = self_integration_client.post(
        "/api/v1/integrations/discover",
        json={
            "source_url": "https://github.com/openclaw/openclaw",
            "source_kind": "repository",
            "ref": "main",
            "metadata": {"trigger": "test"},
        },
    )
    assert discovered.status_code == 202
    discovery_payload = discovered.json()
    assert discovery_payload["status"] == "created"
    assert discovery_payload["candidate_adapter_id"] == "openclaw"
    assert "openclaw_compat_adapter" in discovery_payload["detected_capabilities"]

    prototyped = self_integration_client.post(
        "/api/v1/integrations/prototype",
        json={
            "discovery_id": discovery_payload["discovery_id"],
            "adapter_name": "OpenClaw V2 Adapter",
            "sandbox_backend": "docker",
            "dry_run": True,
        },
    )
    assert prototyped.status_code == 202
    prototype_payload = prototyped.json()
    assert prototype_payload["status"] == "created"
    assert prototype_payload["adapter_name"] == "openclaw_v2_adapter"
    assert any(
        path.endswith("/adapter_node.py")
        for path in prototype_payload["planned_files"]
    )

    promoted = self_integration_client.post(
        "/api/v1/integrations/promote",
        json={
            "prototype_id": prototype_payload["prototype_id"],
            "rollout_mode": "shadow",
        },
    )
    assert promoted.status_code == 202
    promotion_payload = promoted.json()
    assert promotion_payload["status"] == "created"
    assert promotion_payload["decision"] == "pending"
    assert promotion_payload["topology_patch_preview"]["rollout_mode"] == "shadow"


def test_prototype_requires_existing_discovery(self_integration_client: TestClient) -> None:
    response = self_integration_client.post(
        "/api/v1/integrations/prototype",
        json={
            "discovery_id": "disc_missing",
            "adapter_name": "missing",
            "sandbox_backend": "docker",
            "dry_run": True,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Discovery not found"


def test_promote_requires_existing_prototype(self_integration_client: TestClient) -> None:
    response = self_integration_client.post(
        "/api/v1/integrations/promote",
        json={
            "prototype_id": "proto_missing",
            "rollout_mode": "shadow",
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Prototype not found"
