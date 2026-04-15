"""
Excel Operations Service Tests

Contract-first tests for Excel operations service.
These verify the scaffold is in place and handles missing business assets gracefully.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import Mock

from autoresearch.core.services.excel_ops import ExcelOpsService
from autoresearch.core.repositories.excel_jobs import ExcelJobsRepository
from autoresearch.core.services.commission_engine import CommissionEngine
from autoresearch.shared.excel_ops_models import (
    ExcelJobCreateRequest,
    ExcelInputRole,
    CommissionCalculationRequest,
)
from autoresearch.shared.models import JobStatus


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Create temporary database path."""
    return tmp_path / "test_excel_jobs.db"


@pytest.fixture
def repository(temp_db_path: Path) -> ExcelJobsRepository:
    """Create Excel jobs repository."""
    return ExcelJobsRepository(temp_db_path)


@pytest.fixture
def commission_engine() -> CommissionEngine:
    """Create commission engine."""
    return CommissionEngine(strict_mode=True)


@pytest.fixture
def service(
    repository: ExcelJobsRepository,
    commission_engine: CommissionEngine,
) -> ExcelOpsService:
    """Create Excel ops service."""
    return ExcelOpsService(
        repository=repository,
        commission_engine=commission_engine,
        repo_root=Path("/tmp/test_repo"),
    )


class TestExcelOpsServiceScaffold:
    """Test that Excel ops service scaffold is in place."""

    def test_service_initialization(self, service: ExcelOpsService):
        """Service should initialize successfully."""
        assert service is not None
        assert service._repository is not None
        assert service._commission_engine is not None

    def test_create_job(self, service: ExcelOpsService):
        """Should create job successfully."""
        request = ExcelJobCreateRequest(
            task_name="Test job",
            input_files=[],
        )

        job = service.create_job(request)

        assert job.job_id is not None
        assert job.task_name == "Test job"
        assert job.status.value == "created"

    def test_get_job(self, service: ExcelOpsService):
        """Should retrieve created job."""
        request = ExcelJobCreateRequest(
            task_name="Test job",
            input_files=[],
        )

        created = service.create_job(request)
        retrieved = service.get_job(created.job_id)

        assert retrieved is not None
        assert retrieved.job_id == created.job_id

    def test_get_nonexistent_job(self, service: ExcelOpsService):
        """Should return None for nonexistent job."""
        result = service.get_job("nonexistent")
        assert result is None

    def test_list_jobs(self, service: ExcelOpsService):
        """Should list all jobs."""
        service.create_job(ExcelJobCreateRequest(task_name="Job 1", input_files=[]))
        service.create_job(ExcelJobCreateRequest(task_name="Job 2", input_files=[]))

        jobs = service.list_jobs()

        assert len(jobs) >= 2
        task_names = {j.task_name for j in jobs}
        assert "Job 1" in task_names
        assert "Job 2" in task_names

    def test_calculate_commission_blocked(self, service: ExcelOpsService):
        """
        Should return blocked status when business contracts missing.

        This is the critical test: without business rule contracts,
        calculation must be explicitly blocked, not silently fail or guess.
        """
        # Create a job first
        job = service.create_job(ExcelJobCreateRequest(task_name="Test", input_files=[]))

        # Request calculation
        calc_request = CommissionCalculationRequest(
            job_id=job.job_id,
            input_data={"test": "data"},
        )

        response = service.calculate_commission(job.job_id, calc_request)

        # Must be blocked - not calculated, not error, but explicit blocked
        assert response.status == "blocked_awaiting_contracts"
        assert "blocked" in response.status
        assert response.error_message is not None
        assert "contracts" in response.error_message.lower() or "requirement" in response.error_message.lower()

    def test_get_requirement4_status(self, service: ExcelOpsService):
        """Should show requirement #4 readiness status."""
        status = service.get_requirement4_status()

        # Scaffold should be complete
        assert status.scaffold_complete is True

        # But not ready for business assets
        assert status.ready_for_business_assets is False

        # Should list missing assets
        assert len(status.missing_assets) > 0
        assert any("contracts" in str(asset).lower() for asset in status.missing_assets)

        # Should list available components
        assert len(status.available_components) > 0
        assert any("repository" in str(comp).lower() for comp in status.available_components)
        assert any("engine" in str(comp).lower() for comp in status.available_components)

        # Should have next steps
        assert len(status.next_steps) > 0


class TestExcelJobsRepository:
    """Test Excel jobs repository functionality."""

    def test_create_and_retrieve(self, repository: ExcelJobsRepository):
        """Should create and retrieve job."""
        record = repository.create(
            task_name="Test job",
            input_files=["file1.xlsx"],
        )

        assert record.metadata.job_id is not None
        assert record.metadata.task_name == "Test job"

        retrieved = repository.get(record.metadata.job_id)
        assert retrieved is not None
        assert retrieved.metadata.job_id == record.metadata.job_id

    def test_update_status(self, repository: ExcelJobsRepository):
        """Should update job status."""
        record = repository.create(
            task_name="Test job",
            input_files=[],
        )

        updated = repository.update_status(
            record.metadata.job_id,
            JobStatus.RUNNING,  # Use JobStatus enum directly
        )

        assert updated is not None
        assert updated.metadata.status.value == "running"

    def test_set_validation_status(self, repository: ExcelJobsRepository):
        """Should set validation status."""
        record = repository.create(
            task_name="Test job",
            input_files=[],
        )

        updated = repository.set_validation_status(
            record.metadata.job_id,
            "passed",
        )

        assert updated is not None
        assert updated.audit.validation_status == "passed"
        assert len(updated.audit.audit_trail) > 0


class TestCommissionEngineScaffold:
    """Test commission engine scaffold."""

    def test_engine_initialization(self, commission_engine: CommissionEngine):
        """Should initialize successfully."""
        assert commission_engine is not None
        assert commission_engine._strict_mode is True

    def test_load_contracts_missing(self, commission_engine: CommissionEngine):
        """Should return blocked status when contracts missing."""
        status = commission_engine.load_contracts()

        # Contracts directory doesn't exist yet
        assert status.value == "blocked_awaiting_contracts"

    def test_calculate_blocked(self, commission_engine: CommissionEngine):
        """
        Should return blocked result when contracts missing.

        Critical: No silent calculation, no guessing, explicit blocking.
        """
        from autoresearch.core.services.commission_engine import (
            CommissionCalculationRequest as EngineRequest,
        )

        request = EngineRequest(
            job_id="test-job",
            input_data={"test": "data"},
            metadata={},  # Required field
        )

        result = commission_engine.calculate(request)

        # Must be blocked
        assert result.status.value == "blocked_awaiting_contracts"
        assert result.calculated_values == {}
        assert result.applied_rules == []
        assert result.error_message is not None
        assert "contracts" in result.error_message.lower()

    def test_get_status(self, commission_engine: CommissionEngine):
        """Should return engine status."""
        status = commission_engine.get_status()

        assert status["status"] == "blocked_awaiting_contracts"
        assert status["ready_for_calculation"] is False
        assert status["contracts_loaded"] is False
        assert "contracts_dir" in status


class TestFixtureDirectories:
    """Verify fixture directories exist with proper README files."""

    def test_samples_directory_exists(self):
        """Samples fixture directory should exist."""
        path = Path("tests/fixtures/requirement4_samples")
        assert path.exists()
        assert (path / "README.md").exists()

    def test_golden_directory_exists(self):
        """Golden fixture directory should exist."""
        path = Path("tests/fixtures/requirement4_golden")
        assert path.exists()
        assert (path / "README.md").exists()

    def test_contracts_directory_exists(self):
        """Contracts fixture directory should exist."""
        path = Path("tests/fixtures/requirement4_contracts")
        assert path.exists()
        assert (path / "README.md").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
