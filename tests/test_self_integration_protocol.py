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
            "ref": "0123456789abcdef0123456789abcdef01234567",
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


def test_discover_rejects_untrusted_repository_host(
    self_integration_client: TestClient,
) -> None:
    response = self_integration_client.post(
        "/api/v1/integrations/discover",
        json={
            "source_url": "https://github.com.evil.example/openclaw/openclaw",
            "source_kind": "repository",
            "ref": "0123456789abcdef0123456789abcdef01234567",
        },
    )
    assert response.status_code == 400
    assert "untrusted repository host" in response.json()["detail"]


def test_discover_rejects_unpinned_repository_ref(
    self_integration_client: TestClient,
) -> None:
    response = self_integration_client.post(
        "/api/v1/integrations/discover",
        json={
            "source_url": "https://github.com/openclaw/openclaw",
            "source_kind": "repository",
            "ref": "main",
        },
    )
    assert response.status_code == 400
    assert "full commit SHA" in response.json()["detail"]


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


def test_prototype_with_dependencies_requires_secure_fetch_before_promote(
    self_integration_client: TestClient,
) -> None:
    discovered = self_integration_client.post(
        "/api/v1/integrations/discover",
        json={
            "source_url": "https://github.com/openclaw/openclaw",
            "source_kind": "repository",
            "ref": "0123456789abcdef0123456789abcdef01234567",
        },
    )
    discovery_payload = discovered.json()

    prototyped = self_integration_client.post(
        "/api/v1/integrations/prototype",
        json={
            "discovery_id": discovery_payload["discovery_id"],
            "adapter_name": "secure adapter",
            "sandbox_backend": "docker",
            "dry_run": True,
            "dependency_requests": [
                {"package": "scipy", "version_spec": "==1.13.1", "reason": "matrix compute"}
            ],
        },
    )
    assert prototyped.status_code == 202
    prototype_payload = prototyped.json()
    assert prototype_payload["secure_fetch_plan"]["status"] == "pending"
    assert "pip-compile --require-hashes" in " ".join(
        prototype_payload["secure_fetch_plan"]["audit_commands"]
    )

    promoted = self_integration_client.post(
        "/api/v1/integrations/promote",
        json={
            "prototype_id": prototype_payload["prototype_id"],
            "rollout_mode": "shadow",
        },
    )
    assert promoted.status_code == 400
    assert "secure fetch is incomplete" in promoted.json()["detail"]


def test_secure_fetch_enables_full_auto_promotion(
    self_integration_client: TestClient,
) -> None:
    discovered = self_integration_client.post(
        "/api/v1/integrations/discover",
        json={
            "source_url": "https://github.com/openclaw/openclaw",
            "source_kind": "repository",
            "ref": "0123456789abcdef0123456789abcdef01234567",
        },
    )
    discovery_payload = discovered.json()

    prototyped = self_integration_client.post(
        "/api/v1/integrations/prototype",
        json={
            "discovery_id": discovery_payload["discovery_id"],
            "adapter_name": "secure adapter",
            "sandbox_backend": "docker",
            "dry_run": True,
            "dependency_requests": [
                {"package": "scipy", "version_spec": "==1.13.1", "reason": "matrix compute"},
                {"package": "numpy", "version_spec": "==2.0.0", "reason": "array runtime"},
            ],
            "policy_version": "sep-v1",
        },
    )
    prototype_payload = prototyped.json()
    prototype_id = prototype_payload["prototype_id"]

    secure_fetch = self_integration_client.post(
        f"/api/v1/integrations/prototype/{prototype_id}/secure-fetch",
        json={
            "auditor": "Security_Auditor",
            "policy_version": "sep-v1",
            "mount_dir": "/opt/secure-deps/trace-001",
            "audited_artifacts": [
                {
                    "package": "scipy",
                    "version_spec": "==1.13.1",
                    "wheel_filename": "scipy-1.13.1-cp312-cp312-manylinux.whl",
                    "sha256": "a" * 64,
                },
                {
                    "package": "numpy",
                    "version_spec": "==2.0.0",
                    "wheel_filename": "numpy-2.0.0-cp312-cp312-manylinux.whl",
                    "sha256": "b" * 64,
                },
            ],
        },
    )
    assert secure_fetch.status_code == 202
    secure_payload = secure_fetch.json()
    assert secure_payload["secure_fetch_plan"]["status"] == "audited"
    assert secure_payload["offline_sandbox_policy"]["network"] == "none"
    assert secure_payload["offline_sandbox_policy"]["readonly_mounts"] == [
        "/opt/secure-deps/trace-001"
    ]

    required_checks = secure_payload["evaluation_gate"]["required_checks"]
    evaluation_results = {check: True for check in required_checks}
    promoted = self_integration_client.post(
        "/api/v1/integrations/promote",
        json={
            "prototype_id": prototype_id,
            "rollout_mode": "full",
            "approval_mode": "auto_if_green",
            "evaluation_results": evaluation_results,
        },
    )
    assert promoted.status_code == 202
    promotion_payload = promoted.json()
    assert promotion_payload["status"] == "completed"
    assert promotion_payload["decision"] == "approved"
    assert promotion_payload["gate_status"] == "passed"
    assert promotion_payload["trace_id"]


def test_secure_fetch_rejects_artifact_dependency_mismatch(
    self_integration_client: TestClient,
) -> None:
    discovered = self_integration_client.post(
        "/api/v1/integrations/discover",
        json={
            "source_url": "https://github.com/openclaw/openclaw",
            "source_kind": "repository",
            "ref": "0123456789abcdef0123456789abcdef01234567",
        },
    )
    discovery_payload = discovered.json()

    prototyped = self_integration_client.post(
        "/api/v1/integrations/prototype",
        json={
            "discovery_id": discovery_payload["discovery_id"],
            "adapter_name": "secure adapter",
            "sandbox_backend": "docker",
            "dry_run": True,
            "dependency_requests": [
                {"package": "scipy", "version_spec": "==1.13.1", "reason": "matrix compute"}
            ],
        },
    )
    prototype_id = prototyped.json()["prototype_id"]

    secure_fetch = self_integration_client.post(
        f"/api/v1/integrations/prototype/{prototype_id}/secure-fetch",
        json={
            "audited_artifacts": [
                {
                    "package": "numpy",
                    "version_spec": "==2.0.0",
                    "wheel_filename": "numpy-2.0.0-cp312-cp312-manylinux.whl",
                    "sha256": "b" * 64,
                }
            ]
        },
    )
    assert secure_fetch.status_code == 400
    assert "audited artifacts do not match requested dependencies" in secure_fetch.json()["detail"]
