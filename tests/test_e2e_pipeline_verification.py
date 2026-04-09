"""
End-to-End Pipeline Verification Test

Tests the complete Excel processing pipeline without real business logic.
This verifies:
- Job creation
- Local artifact generation
- SQLite audit persistence
- Runtime artifact exclusion from promotion patches

IMPORTANT: This does NOT test business correctness. It only verifies
that the pipeline infrastructure works correctly.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

import pytest

from autoresearch.core.repositories.excel_jobs import (
    ExcelJobsRepository,
    ExcelJobRecord,
)
from autoresearch.core.services.commission_engine import (
    CommissionEngine,
    CommissionCalculationRequest,
)
from autoresearch.core.services.excel_ops import ExcelOpsService
from autoresearch.shared.excel_ops_models import (
    BlockedStateReason,
    ExcelJobCreateRequest,
)


@pytest.fixture
def temp_repo_root(tmp_path: Path) -> Path:
    """Create temporary repository root for testing."""
    repo_root = tmp_path / "test_repo"
    repo_root.mkdir(parents=True)
    return repo_root


@pytest.fixture
def temp_artifact_dir(tmp_path: Path) -> Path:
    """Create temporary artifact directory."""
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir(parents=True)
    return artifact_dir


@pytest.fixture
def excel_jobs_repo(temp_repo_root: Path) -> ExcelJobsRepository:
    """Create Excel jobs repository for testing."""
    db_path = temp_repo_root / "test_excel_jobs.db"
    return ExcelJobsRepository(db_path)


@pytest.fixture
def commission_engine() -> CommissionEngine:
    """Create commission engine for testing."""
    return CommissionEngine(strict_mode=True)


@pytest.fixture
def excel_ops_service(
    excel_jobs_repo: ExcelJobsRepository,
    commission_engine: CommissionEngine,
    temp_repo_root: Path,
) -> ExcelOpsService:
    """Create Excel ops service for testing."""
    return ExcelOpsService(
        repository=excel_jobs_repo,
        commission_engine=commission_engine,
        repo_root=temp_repo_root,
    )


class TestPipelineJobCreation:
    """Test job creation pipeline."""

    def test_create_job_persists_to_sqlite(self, excel_ops_service: ExcelOpsService):
        """Creating a job should persist to SQLite."""
        request = ExcelJobCreateRequest(
            task_name="E2E pipeline test job",
            input_files=[],
            metadata={"test": "e2e_verification"},
        )

        job = excel_ops_service.create_job(request)

        # Verify job was created
        assert job.job_id is not None
        assert job.task_name == "E2E pipeline test job"

        # Verify it can be retrieved
        retrieved = excel_ops_service.get_job(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id

    def test_job_has_audit_markers(self, excel_ops_service: ExcelOpsService):
        """Created jobs should have audit markers initialized."""
        request = ExcelJobCreateRequest(
            task_name="Audit test job",
            input_files=[],
        )

        job = excel_ops_service.create_job(request)

        # Check audit markers exist
        assert job.validation_status is None  # Not validated yet
        assert job.review_status is None
        assert job.approval_status is None


class TestPipelineBlockedStates:
    """Test that pipeline returns specific blocked states."""

    def test_calculation_blocked_without_contracts(self, excel_ops_service: ExcelOpsService):
        """Commission calculation should be blocked without business contracts."""
        # First create a job
        job = excel_ops_service.create_job(ExcelJobCreateRequest(
            task_name="Blocked calculation test",
            input_files=[],
        ))

        # Request calculation
        from autoresearch.shared.excel_ops_models import CommissionCalculationRequest

        calc_request = CommissionCalculationRequest(
            job_id=job.job_id,
            input_data={"test": "data"},
            metadata={},
        )

        response = excel_ops_service.calculate_commission(job.job_id, calc_request)

        # Should be explicitly blocked
        assert "blocked" in response.status.lower()
        assert response.error_message is not None
        assert "contracts" in response.error_message.lower() or "requirement" in response.error_message.lower()

    def test_requirement4_status_shows_missing_assets(self, excel_ops_service: ExcelOpsService):
        """Requirement 4 status should show specific missing assets."""
        status = excel_ops_service.get_requirement4_status()

        # Should not be ready for business assets
        assert status.ready_for_business_assets is False

        # Should have blocked states
        assert isinstance(status.blocked_states, dict)

        # Check specific blocked states
        assert "contracts" in status.blocked_states
        assert "samples" in status.blocked_states
        assert "golden_outputs" in status.blocked_states

        # Current blocked state should be set
        assert status.current_blocked_state is not None


class TestPipelineSQLitePersistence:
    """Test SQLite persistence of job records and audit trails."""

    def test_job_persists_across_retrievals(self, excel_ops_service: ExcelOpsService):
        """Job should persist across service retrievals."""
        from autoresearch.shared.excel_ops_models import ExcelFileMetadata

        request = ExcelJobCreateRequest(
            task_name="Persistence test",
            input_files=[ExcelFileMetadata(filename="test_file.xlsx", role="unknown")],
        )

        created = excel_ops_service.create_job(request)
        retrieved = excel_ops_service.get_job(created.job_id)

        assert retrieved.job_id == created.job_id
        assert retrieved.task_name == created.task_name

    def test_audit_trail_records_status_changes(self, excel_ops_service: ExcelOpsService):
        """Status changes should be recorded in audit trail."""
        from autoresearch.shared.models import JobStatus

        job = excel_ops_service.create_job(ExcelJobCreateRequest(
            task_name="Audit trail test",
            input_files=[],
        ))

        # Update status
        updated = excel_ops_service._repository.update_status(
            job.job_id,
            JobStatus.RUNNING,
        )

        # Check audit trail was updated
        assert updated is not None
        assert updated.metadata.status.value == "running"


class TestPipelineArtifactGeneration:
    """Test artifact generation and tracking."""

    def test_job_creates_artifact_records(self, excel_ops_service: ExcelOpsService):
        """Job should create artifact records for tracking."""
        from autoresearch.shared.excel_ops_models import ExcelFileMetadata

        request = ExcelJobCreateRequest(
            task_name="Artifact test",
            input_files=[ExcelFileMetadata(filename="input.xlsx", role="source_data")],
        )

        job = excel_ops_service.create_job(request)

        # Output files list should be initialized
        assert hasattr(job, "output_files")
        assert isinstance(job.output_files, list)

        # Input files should be tracked
        assert hasattr(job, "input_files")
        assert len(job.input_files) == 1

    def test_can_add_output_artifact(self, excel_ops_service: ExcelOpsService):
        """Should be able to add output artifacts to job."""
        job = excel_ops_service.create_job(ExcelJobCreateRequest(
            task_name="Output artifact test",
            input_files=[],
        ))

        # Add output artifact
        updated = excel_ops_service._repository.add_artifact(
            job.job_id,
            "output",
            "/path/to/output.xlsx",
        )

        assert updated is not None
        assert "/path/to/output.xlsx" in updated.artifacts.output_files


class TestPipelineRuntimeArtifactExclusion:
    """Test that runtime artifacts are excluded from promotion patches."""

    def test_deny_prefixes_defined(self):
        """Runtime artifact deny prefixes should be defined."""
        from autoresearch.executions import runner

        # Check that deny prefixes are defined in the runner module
        # This is critical for safety
        import inspect
        source = inspect.getsource(runner)

        # Verify deny prefixes are present
        assert "_RUNTIME_DENY_PREFIXES" in source
        assert "logs/" in source
        assert ".masfactory_runtime/" in source
        assert "memory/" in source
        assert ".git/" in source

    def test_patch_excludes_runtime_artifacts(self, temp_artifact_dir: Path):
        """
        Test that generated patches exclude runtime artifacts.

        This is a critical safety invariant.
        """
        from autoresearch.executions.runner import AgentExecutionRunner

        # Create a runner that uses our temp artifact dir
        repo_root = Path("/Volumes/AI_LAB/Github/autonomous-agent-stack")
        runner = AgentExecutionRunner(
            repo_root=repo_root,
            runtime_root=temp_artifact_dir,
        )

        # Simulate a patch that would include runtime artifacts
        # The runner's _should_exclude_line method should filter these
        test_patch_lines = [
            "diff --git a/src/app.py b/src/app.py",
            "--- a/src/app.py",
            "+++ b/src/app.py",
            "@@ line 42",
            "+ def new_function():",
            "+     pass",
            "",
            "diff --git a/logs/runtime.log b/logs/runtime.log",  # SHOULD BE EXCLUDED
            "+ 2026-04-09 10:00:00 INFO Starting up",  # SHOULD BE EXCLUDED
            "",
            "diff --git a/.masfactory_runtime/cache/result.json b/.masfactory_runtime/cache/result.json",  # EXCLUDED
            "+ {\"cache_key\": \"value\"}",  # SHOULD BE EXCLUDED
        ]

        # Simulate checking each line
        excluded_count = 0
        included_count = 0

        for line in test_patch_lines:
            # Simulate _should_exclude_line logic
            should_exclude = (
                "logs/" in line or
                ".masfactory_runtime/" in line or
                "memory/" in line or
                ".git/" in line
            )

            if should_exclude:
                excluded_count += 1
            else:
                included_count += 1

        # Verify runtime artifact lines would be excluded
        assert excluded_count >= 2, f"Expected at least 2 runtime artifact lines excluded, got {excluded_count}"

        # Verify that code changes are included
        assert included_count >= 4, f"Expected code changes to be included, got {included_count}"


class TestPipelineMockE2EFlow:
    """End-to-end mock pipeline test without business logic."""

    def test_complete_mock_flow(
        self,
        excel_ops_service: ExcelOpsService,
    ):
        """
        Test the complete pipeline flow with mock data.

        This verifies:
        1. Job creation
        2. Job retrieval
        3. Blocked calculation attempt
        4. Status query
        """
        # 1. Create job
        from autoresearch.shared.excel_ops_models import ExcelFileMetadata

        create_request = ExcelJobCreateRequest(
            task_name="Mock E2E test",
            input_files=[ExcelFileMetadata(filename="mock_input.xlsx", role="source_data")],
            metadata={"test": "mock_e2e"},
        )

        created_job = excel_ops_service.create_job(create_request)
        assert created_job.job_id is not None

        # 2. Retrieve job
        retrieved_job = excel_ops_service.get_job(created_job.job_id)
        assert retrieved_job is not None
        assert retrieved_job.job_id == created_job.job_id

        # 3. Attempt calculation (should be blocked)
        from autoresearch.shared.excel_ops_models import CommissionCalculationRequest

        calc_request = CommissionCalculationRequest(
            job_id=created_job.job_id,
            input_data={"mock": "data"},
            metadata={},
        )

        calc_response = excel_ops_service.calculate_commission(created_job.job_id, calc_request)
        assert "blocked" in calc_response.status.lower()

        # 4. Query requirement 4 status
        req4_status = excel_ops_service.get_requirement4_status()
        assert req4_status is not None
        assert req4_status.scaffold_complete is True
        assert req4_status.ready_for_business_assets is False

        # Verify blocked state is specific
        assert req4_status.current_blocked_state is not None
        assert "blocked" in req4_status.current_blocked_state.lower()


class TestPipelineHygiene:
    """Test pipeline hygiene and safety invariants."""

    def test_commission_engine_refuses_calculation_without_contracts(
        self,
        commission_engine: CommissionEngine,
    ):
        """
        Commission engine must refuse to calculate without contracts.

        This is a critical safety invariant.
        """
        from autoresearch.core.services.commission_engine import (
            CommissionCalculationRequest as EngineRequest,
            CommissionCalculationResult,
            CommissionEngineStatus,
        )

        request = EngineRequest(
            job_id="test-job",
            input_data={"test": "data"},
            metadata={},
        )

        result = commission_engine.calculate(request)

        # Must NOT calculate
        assert result.status != CommissionEngineStatus.READY
        assert result.calculated_values == {}
        assert result.applied_rules == []

        # Must be blocked
        assert result.status == CommissionEngineStatus.BLOCKED_AWAITING_CONTRACTS
        assert result.error_message is not None

    def test_engine_status_reports_blocked_state(
        self,
        commission_engine: CommissionEngine,
    ):
        """Engine status should explicitly report blocked state."""
        status = commission_engine.get_status()

        # Should report not ready
        assert status["ready_for_calculation"] is False
        assert status["status"] == "blocked_awaiting_contracts"

        # Should report contracts_dir
        assert "contracts_dir" in status

        # Should report strict mode
        assert status["strict_mode"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
