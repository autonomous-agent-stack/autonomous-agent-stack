"""
Excel Operations Service - Orchestration Layer

Orchestrates Excel processing pipeline stages:
- Ingest: Accept and register Excel input files
- Normalize: Transform inputs to standard format
- Validate: Check against business rules
- Calculate: Execute commission calculations
- Export: Generate output files
- Audit: Maintain audit trail

IMPORTANT: This is orchestration only. Business logic implementation
is blocked until requirement #4 business assets arrive.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from autoresearch.core.repositories.excel_jobs import (
    ExcelJobsRepository,
    ExcelJobRecord,
)
from autoresearch.core.services.commission_engine import (
    CommissionCalculationRequest,
    CommissionCalculationResult,
    CommissionEngine,
)
from autoresearch.shared.excel_ops_models import (
    CommissionCalculationResponse,
    ExcelJobCreateRequest,
    ExcelJobRead,
    ExcelJobStatusResponse,
    ExcelValidationResult,
    Requirement4StatusResponse,
)
from autoresearch.shared.models import JobStatus

logger = logging.getLogger(__name__)


class ExcelOpsService:
    """
    Service for Excel processing operations.

    Provides orchestration for the complete Excel processing pipeline.
    Currently in scaffold mode - awaits business rule contracts.
    """

    def __init__(
        self,
        repository: ExcelJobsRepository,
        commission_engine: CommissionEngine,
        repo_root: Path,
    ) -> None:
        """
        Initialize Excel operations service.

        Args:
            repository: Excel jobs repository for persistence
            commission_engine: Deterministic commission calculation engine
            repo_root: Repository root path for file operations
        """
        self._repository = repository
        self._commission_engine = commission_engine
        self._repo_root = repo_root
        logger.info("ExcelOpsService initialized")

    def create_job(self, request: ExcelJobCreateRequest) -> ExcelJobRead:
        """
        Create a new Excel processing job.

        Args:
            request: Job creation request

        Returns:
            Created job record
        """
        # Extract file paths from metadata
        input_file_paths = [
            str(f.filename) for f in request.input_files
        ]

        # Create job in repository
        record = self._repository.create(
            task_name=request.task_name,
            input_files=input_file_paths,
            metadata=request.metadata,
        )

        return self._record_to_read(record)

    def get_job(self, job_id: str) -> ExcelJobRead | None:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job record, or None if not found
        """
        record = self._repository.get(job_id)
        if record is None:
            return None
        return self._record_to_read(record)

    def list_jobs(self, status: JobStatus | None = None) -> list[ExcelJobRead]:
        """
        List jobs, optionally filtered by status.

        Args:
            status: Optional status filter

        Returns:
            List of job records
        """
        if status is None:
            records = self._repository.list_all()
        else:
            records = self._repository.list_by_status(status)

        return [self._record_to_read(r) for r in records]

    def get_job_status(self, job_id: str) -> ExcelJobStatusResponse | None:
        """
        Get detailed job status with next steps.

        Args:
            job_id: Job ID

        Returns:
            Job status response, or None if not found
        """
        record = self._repository.get(job_id)
        if record is None:
            return None

        # Determine readiness based on status
        ready_for_calculation = record.metadata.status in {
            JobStatus.CREATED,
            JobStatus.QUEUED,
        }
        ready_for_validation = record.metadata.status == JobStatus.COMPLETED

        blocked_reason = None
        next_steps = []

        if record.metadata.status == JobStatus.CREATED:
            next_steps.append("Job created - awaiting input file processing")
        elif record.metadata.status == JobStatus.QUEUED:
            next_steps.append("Job queued - awaiting execution")
        elif record.metadata.status == JobStatus.RUNNING:
            next_steps.append("Job running - in progress")
        elif record.metadata.status == JobStatus.COMPLETED:
            next_steps.append("Job completed - ready for validation")
        elif record.metadata.status == JobStatus.FAILED:
            blocked_reason = record.metadata.error_message or "Unknown error"
            next_steps.append("Job failed - check error logs")
        elif record.metadata.status == JobStatus.CANCELLED:
            blocked_reason = "Job was cancelled"
            next_steps.append("Job cancelled - create new job to retry")

        return ExcelJobStatusResponse(
            job_id=job_id,
            status=record.metadata.status,
            ready_for_calculation=ready_for_calculation,
            ready_for_validation=ready_for_validation,
            blocked_reason=blocked_reason,
            next_steps=next_steps,
        )

    def calculate_commission(
        self,
        job_id: str,
        request: CommissionCalculationRequest,
    ) -> CommissionCalculationResponse:
        """
        Calculate commissions for a job.

        IMPORTANT: This is currently blocked awaiting business rule contracts.
        When requirement #4 assets arrive, this will execute deterministic
        calculations based on business-provided rules.

        Args:
            job_id: Job ID
            request: Calculation request

        Returns:
            Calculation response with status and results (or error)
        """
        record = self._repository.get(job_id)
        if record is None:
            return CommissionCalculationResponse(
                job_id=job_id,
                status="error",
                error_message=f"Job {job_id} not found",
            )

        # Update job status to running
        self._repository.update_status(job_id, JobStatus.RUNNING)

        try:
            # Prepare calculation request
            calc_request = CommissionCalculationRequest(
                job_id=job_id,
                input_data=request.input_data,
                metadata={},  # Required field
            )

            # Delegate to commission engine
            calc_result = self._commission_engine.calculate(calc_request)

            # Map result to response
            response = CommissionCalculationResponse(
                job_id=job_id,
                status=calc_result.status.value,
                calculated_values=calc_result.calculated_values,
                applied_rules=calc_result.applied_rules,
                intermediate_steps=calc_result.intermediate_steps,
                error_message=calc_result.error_message,
                calculated_at=None,
            )

            # Update job status based on result
            if calc_result.status.value == "ready":
                self._repository.update_status(job_id, JobStatus.COMPLETED)
            else:
                # Blocked or error
                self._repository.update_status(
                    job_id,
                    JobStatus.FAILED,
                    error_message=calc_result.error_message,
                )

            return response

        except Exception as exc:
            logger.exception("Commission calculation failed for job %s", job_id)
            self._repository.update_status(
                job_id,
                JobStatus.FAILED,
                error_message=str(exc),
            )
            return CommissionCalculationResponse(
                job_id=job_id,
                status="error",
                error_message=str(exc),
            )

    def validate_job(
        self,
        job_id: str,
        validation_type: str,
        options: dict[str, Any] | None = None,
    ) -> ExcelValidationResult:
        """
        Validate job outputs against business rules.

        IMPORTANT: Validation rules will be defined by business-provided
        contracts (requirement #4). Currently returns placeholder result.

        Args:
            job_id: Job ID
            validation_type: Type of validation to perform
            options: Optional validation options

        Returns:
            Validation result
        """
        record = self._repository.get(job_id)
        if record is None:
            return ExcelValidationResult(
                job_id=job_id,
                validation_type=validation_type,
                status="blocked",
                errors=[f"Job {job_id} not found"],
            )

        # TODO: Implement validation when business provides rules
        # For now, return blocked status
        return ExcelValidationResult(
            job_id=job_id,
            validation_type=validation_type,
            status="blocked",
            errors=[
                "Validation rules not yet provided. "
                "Awaiting requirement #4 business assets."
            ],
            warnings=[
                "This is a scaffold implementation. "
                "See docs/requirement4/ for what's needed."
            ],
        )

    def get_requirement4_status(self) -> Requirement4StatusResponse:
        """
        Get requirement #4 readiness status with granular blocked states.

        Returns:
            Status response showing what's in place and what's needed
        """
        from autoresearch.shared.excel_ops_models import BlockedStateReason

        # Check each business asset category
        repo_root = self._repo_root

        # Check for contracts
        contracts_dir = repo_root / "tests/fixtures/requirement4_contracts"
        contracts_excel_exists = (contracts_dir / "excel_contracts.json").exists()
        ambiguity_checklist_exists = (contracts_dir / "ambiguity_checklist.md").exists()

        # Check for samples
        samples_dir = repo_root / "tests/fixtures/requirement4_samples"
        samples_exist = any(
            f.suffix == ".xlsx" for f in samples_dir.glob("*.xlsx")
        ) if samples_dir.exists() else False

        # Check for golden outputs
        golden_dir = repo_root / "tests/fixtures/requirement4_golden"
        golden_excel_exists = any(
            f.suffix == ".xlsx" for f in golden_dir.glob("*.xlsx")
        ) if golden_dir.exists() else False
        golden_metadata_exists = (golden_dir / "golden_metadata.json").exists()

        # Check for audit workflow
        audit_workflow_defined = bool(
            golden_metadata_exists and
            "audit_loop" in (golden_dir / "golden_metadata.json").read_text()
        )

        # Build blocked states
        blocked_states = {
            "contracts": contracts_excel_exists and ambiguity_checklist_exists,
            "ambiguity_decisions": ambiguity_checklist_exists,
            "samples": samples_exist,
            "golden_outputs": golden_excel_exists and golden_metadata_exists,
            "audit_workflow": audit_workflow_defined,
        }

        # Determine if router is registered
        # This will be checked dynamically via try/except in the router
        router_registered = True  # Placeholder - will check via actual import
        router_wired = False  # Placeholder - not wired in dependencies.py yet

        # Calculate overall readiness
        ready_for_business_assets = all(blocked_states.values())

        # Find first blocked state for error message
        current_blocked_state = None
        if not ready_for_business_assets:
            if not blocked_states["contracts"]:
                current_blocked_state = BlockedStateReason.BLOCKED_AWAITING_CONTRACTS.value
            elif not blocked_states["ambiguity_decisions"]:
                current_blocked_state = BlockedStateReason.BLOCKED_AWAITING_AMBIGUITY_DECISIONS.value
            elif not blocked_states["samples"]:
                current_blocked_state = BlockedStateReason.BLOCKED_AWAITING_SAMPLES.value
            elif not blocked_states["golden_outputs"]:
                current_blocked_state = BlockedStateReason.BLOCKED_AWAITING_GOLDEN_OUTPUTS.value
            elif not blocked_states["audit_workflow"]:
                current_blocked_state = BlockedStateReason.BLOCKED_AWAITING_AUDIT_WORKFLOW.value

        return Requirement4StatusResponse(
            ready_for_business_assets=ready_for_business_assets,
            scaffold_complete=True,
            blocked_states=blocked_states,
            current_blocked_state=current_blocked_state,
            router_registered=router_registered,
            router_wired=router_wired,
            verification_status="not_verified",
        )

    def _record_to_read(self, record: ExcelJobRecord) -> ExcelJobRead:
        """Convert repository record to API response model."""
        from autoresearch.shared.excel_ops_models import ExcelFileMetadata

        # Convert input file metadata
        input_files = []
        for file_path in record.metadata.input_files:
            # Try to get hash from artifacts
            file_hash = record.artifacts.input_hashes.get(
                Path(file_path).name,
            )
            input_files.append(
                ExcelFileMetadata(
                    filename=Path(file_path).name,
                    role="unknown",  # Will be set when business defines roles
                    size_bytes=None,
                    sha256_hash=file_hash,
                )
            )

        # Convert output files
        output_files = []
        for file_path in record.artifacts.output_files:
            output_files.append(
                ExcelFileMetadata(
                    filename=Path(file_path).name,
                    role="unknown",
                )
            )

        return ExcelJobRead(
            job_id=record.metadata.job_id,
            task_name=record.metadata.task_name,
            status=record.metadata.status,
            input_files=input_files,
            output_files=output_files,
            validation_status=record.audit.validation_status,
            review_status=record.audit.review_status,
            approval_status=record.audit.approval_status,
            created_at=record.metadata.created_at,
            updated_at=record.metadata.updated_at,
            error_message=record.metadata.error_message,
            metadata=record.metadata.metadata,
            commission_results=None,  # Will be populated when business rules arrive
            validation_results=None,
        )
