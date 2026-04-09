"""
Excel Operations Router API Tests

API-level tests for the excel_ops router endpoints.
These tests verify the HTTP contract, response structures, and blocked states.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from autoresearch.api.routers.excel_ops import router, get_excel_ops_service
from autoresearch.shared.excel_ops_models import (
    CommissionCalculationRequest,
    ExcelJobCreateRequest,
    ExcelInputRole,
)


@pytest.fixture
def test_app() -> FastAPI:
    """Create test FastAPI app with excel_ops router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    """Test client for API requests."""
    # Mock the service dependency to return 501 Not Implemented
    # This verifies the router is registered but service is not wired
    from fastapi import HTTPException, status

    def mock_get_service():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Excel ops service not yet wired. This is expected - service requires business assets first.",
        )

    test_app.dependency_overrides[get_excel_ops_service] = mock_get_service

    return TestClient(test_app)


class TestExcelOpsRouterRegistration:
    """Test that excel_ops router is properly registered."""

    def test_router_included(self, test_app: FastAPI):
        """Router should be included in app."""
        routes = [route for route in test_app.routes]
        excel_ops_routes = [r for r in routes if hasattr(r, 'path') and r.path.startswith("/api/v1/excel-ops")]

        assert len(excel_ops_routes) > 0, "excel_ops routes should be registered"

    def test_router_prefix_correct(self, test_app: FastAPI):
        """Router should have correct prefix."""
        routes = [r for r in test_app.routes if hasattr(r, 'path') and r.path.startswith("/api/v1/excel-ops")]
        assert any(r.path == "/api/v1/excel-ops/jobs" for r in routes), "jobs endpoint should exist"
        assert any(r.path == "/api/v1/excel-ops/status/requirement4" for r in routes), "status endpoint should exist"

    def test_router_tag(self, test_app: FastAPI):
        """Router should have excel-ops tag."""
        routes = [r for r in test_app.routes if hasattr(r, 'tags')]
        excel_ops_routes = [r for r in routes if r.tags and "excel-ops" in r.tags]
        assert len(excel_ops_routes) > 0, "router should have excel-ops tag"


class TestExcelOpsRouterEndpoints:
    """Test excel_ops router HTTP endpoints."""

    def test_requirement4_status_endpoint(self, client: TestClient):
        """GET /api/v1/excel-ops/status/requirement4 should return scaffold status."""
        response = client.get("/api/v1/excel-ops/status/requirement4")

        assert response.status_code == 501, \
            f"Expected 501 Not Implemented (service not wired), got {response.status_code}"

        # When service is properly wired, should return 200 with Requirement4StatusResponse
        # For now, 501 confirms router is registered but service is not ready

    def test_create_job_endpoint_returns_501(self, client: TestClient):
        """POST /api/v1/excel-ops/jobs should return 501 (service not wired)."""
        request = ExcelJobCreateRequest(
            task_name="Test job",
            input_files=[],
        )

        response = client.post(
            "/api/v1/excel-ops/jobs",
            json=request.model_dump(mode="json"),
        )

        assert response.status_code == 501, \
            f"Expected 501 Not Implemented, got {response.status_code}"

    def test_get_job_endpoint_returns_501(self, client: TestClient):
        """GET /api/v1/excel-ops/jobs/{id} should return 501."""
        response = client.get("/api/v1/excel-ops/jobs/test-job-id")

        assert response.status_code == 501, \
            f"Expected 501 Not Implemented, got {response.status_code}"


class TestExcelOpsRouterContractVerification:
    """Verify router HTTP contract without needing wired service."""

    def test_post_jobs_accepts_valid_payload(self, test_app: FastAPI):
        """Router should accept valid job creation payload."""
        # Test that the route exists and accepts POST
        routes = [r for r in test_app.routes if hasattr(r, 'path')]
        create_route = [r for r in routes if r.path == "/api/v1/excel-ops/jobs" and "POST" in r.methods]

        assert len(create_route) > 0, "POST /jobs route should exist"

    def test_get_jobs_endpoint_exists(self, test_app: FastAPI):
        """GET /api/v1/excel-ops/jobs endpoint should exist."""
        routes = [r for r in test_app.routes if hasattr(r, 'path')]
        list_route = [r for r in routes if r.path == "/api/v1/excel-ops/jobs" and "GET" in r.methods]

        assert len(list_route) > 0, "GET /jobs route should exist"

    def test_calculate_commission_endpoint_exists(self, test_app: FastAPI):
        """POST /api/v1/excel-ops/jobs/{id}/calculate endpoint should exist."""
        routes = [r for r in test_app.routes if hasattr(r, 'path')]
        calc_routes = [r for r in routes if r.path.startswith("/api/v1/excel-ops/jobs/") and "calculate" in r.path]

        assert len(calc_routes) > 0, "POST /jobs/{id}/calculate route should exist"

    def test_status_endpoint_exists(self, test_app: FastAPI):
        """GET /api/v1/excel-ops/status/requirement4 endpoint should exist."""
        routes = [r for r in test_app.routes if hasattr(r, 'path')]
        status_route = [r for r in routes if r.path == "/api/v1/excel-ops/status/requirement4" and "GET" in r.methods]

        assert len(status_route) > 0, "GET /status/requirement4 route should exist"


class TestExcelOpsRouterResponseModels:
    """Verify response models are properly defined."""

    def test_requirement4_status_response_model_exists(self):
        """Requirement4StatusResponse model should be importable."""
        from autoresearch.shared.excel_ops_models import Requirement4StatusResponse

        # Verify model has expected fields
        model_fields = Requirement4StatusResponse.model_fields
        assert "ready_for_business_assets" in model_fields
        assert "scaffold_complete" in model_fields
        assert "blocked_states" in model_fields
        assert "current_blocked_state" in model_fields
        assert "router_registered" in model_fields
        assert "verification_status" in model_fields

    def test_blocked_state_reasons_exist(self):
        """BlockedStateReason enum should have all required states."""
        from autoresearch.shared.excel_ops_models import BlockedStateReason

        expected_states = {
            "blocked_awaiting_contracts",
            "blocked_awaiting_ambiguity_decisions",
            "blocked_awaiting_samples",
            "blocked_awaiting_golden_outputs",
            "blocked_awaiting_audit_workflow",
            "ready",
            "completed",
            "blocked_invalid_contracts",
            "blocked_router_not_wired",
        }

        actual_states = {state.value for state in BlockedStateReason}

        for expected in expected_states:
            assert expected in actual_states, f"Missing blocked state: {expected}"

    def test_excel_job_read_model_has_blocked_state_fields(self):
        """ExcelJobRead should have fields for blocked state tracking."""
        from autoresearch.shared.excel_ops_models import ExcelJobRead

        model_fields = ExcelJobRead.model_fields
        assert "status" in model_fields
        assert "error_message" in model_fields


class TestExcelOpsRouterBlockingBehavior:
    """Test that router properly handles blocked states when service is wired."""

    @pytest.fixture
    def wired_service(self, tmp_path: Path):
        """Create a mock wired service for testing."""
        from autoresearch.core.services.excel_ops import ExcelOpsService
        from autoresearch.core.repositories.excel_jobs import ExcelJobsRepository
        from autoresearch.core.services.commission_engine import CommissionEngine

        # Create real service components
        db_path = tmp_path / "test_excel_jobs.db"
        repository = ExcelJobsRepository(db_path)
        engine = CommissionEngine()

        service = ExcelOpsService(
            repository=repository,
            commission_engine=engine,
            repo_root=Path("/tmp/test"),
        )

        return service

    def test_requirement4_status_shows_blocked_states(self, wired_service):
        """When service is wired, /status/requirement4 should show specific blocked states."""
        from autoresearch.shared.excel_ops_models import BlockedStateReason

        status = wired_service.get_requirement4_status()

        # Should not be ready
        assert status.ready_for_business_assets is False

        # Should show scaffold is complete
        assert status.scaffold_complete is True

        # Should have blocked states
        assert isinstance(status.blocked_states, dict)

        # Should identify specific missing assets
        # (These will be False until business provides assets)
        assert "contracts" in status.blocked_states
        assert "samples" in status.blocked_states

        # Should have current blocked state
        assert status.current_blocked_state is not None
        assert "blocked" in status.current_blocked_state.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
