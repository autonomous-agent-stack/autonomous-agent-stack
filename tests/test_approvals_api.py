from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_admin_auth_service, get_approval_store_service
from autoresearch.api.main import app
from autoresearch.core.services.admin_auth import AdminAuthService
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalRequestRead,
)
from autoresearch.shared.store import SQLiteModelRepository


@pytest.fixture
def approvals_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "approvals.sqlite3"
    auth_service = AdminAuthService(
        secret="test-approvals-jwt-secret",
        bootstrap_key="approvals-bootstrap-key",
    )
    approval_store = ApprovalStoreService(
        repository=SQLiteModelRepository(
            db_path=db_path,
            table_name="approval_requests_api_it",
            model_cls=ApprovalRequestRead,
        )
    )

    app.dependency_overrides[get_admin_auth_service] = lambda: auth_service
    app.dependency_overrides[get_approval_store_service] = lambda: approval_store

    with TestClient(app) as client:
        token_response = client.post(
            "/api/v1/admin/auth/token",
            json={"subject": "approval-owner", "roles": ["owner"], "ttl_seconds": 3600},
            headers={"x-admin-bootstrap-key": "approvals-bootstrap-key"},
        )
        assert token_response.status_code == 200
        token = token_response.json()["token"]
        client.headers.update({"authorization": f"Bearer {token}"})
        setattr(client, "_approval_store", approval_store)
        yield client

    app.dependency_overrides.clear()


def test_approvals_health_returns_ok(approvals_client: TestClient) -> None:
    response = approvals_client.get("/api/v1/approvals/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_approvals_api_requires_bearer_token(approvals_client: TestClient) -> None:
    existing = approvals_client.headers.pop("authorization", None)
    response = approvals_client.get("/api/v1/approvals")
    assert response.status_code == 401
    if existing is not None:
        approvals_client.headers["authorization"] = existing


def test_approvals_api_lists_and_reads_requests(approvals_client: TestClient) -> None:
    approval_store = getattr(approvals_client, "_approval_store")
    pending = approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Promote tested branch",
            summary="Regression has passed and branch is ready for review",
            telegram_uid="10001",
            session_id="oc_session_a",
            agent_run_id="run_a",
            source="git_policy",
        )
    )
    approved = approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Install signed skill",
            telegram_uid="20002",
            session_id="oc_session_b",
            agent_run_id="run_b",
            source="skill_registry",
        )
    )
    approval_store.resolve_request(
        approved.approval_id,
        ApprovalDecisionRequest(
            decision="approved",
            decided_by="owner",
            note="looks good",
        ),
    )

    response = approvals_client.get("/api/v1/approvals?status=pending&telegram_uid=10001")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["approval_id"] == pending.approval_id
    assert payload[0]["status"] == "pending"

    detail = approvals_client.get(f"/api/v1/approvals/{pending.approval_id}")
    assert detail.status_code == 200
    detail_payload = detail.json()
    assert detail_payload["title"] == "Promote tested branch"
    assert detail_payload["agent_run_id"] == "run_a"


def test_approvals_api_can_resolve_request(approvals_client: TestClient) -> None:
    approval_store = getattr(approvals_client, "_approval_store")
    pending = approval_store.create_request(
        ApprovalRequestCreateRequest(
            title="Approve deployment window",
            telegram_uid="30003",
            source="ops",
        )
    )

    response = approvals_client.post(
        f"/api/v1/approvals/{pending.approval_id}/decision",
        json={
            "decision": "approved",
            "decided_by": "owner",
            "note": "window confirmed",
            "metadata": {"source": "admin_api"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["decided_by"] == "owner"
    assert payload["decision_note"] == "window confirmed"
