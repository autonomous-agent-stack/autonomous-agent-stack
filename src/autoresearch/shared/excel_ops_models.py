"""
Excel Operations Models and Contracts

Defines request/response models for Excel processing operations.
These are contract-level definitions - actual business logic will be
implemented when requirement #4 business assets arrive.
"""
from __future__ import annotations

from enum import Enum

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from autoresearch.shared.models import JobStatus, StrictModel, utc_now


from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator

from autoresearch.shared.models import JobStatus, StrictModel, utc_now


class BlockedStateReason(str, Enum):
    """
    Granular blocked state reasons for requirement #4.

    Each reason corresponds to a specific missing business asset.
    This allows precise error messages about what's blocking operations.
    """
    # Business assets not yet provided
    BLOCKED_AWAITING_CONTRACTS = "blocked_awaiting_contracts"
    BLOCKED_AWAITING_AMBIGUITY_DECISIONS = "blocked_awaiting_ambiguity_decisions"
    BLOCKED_AWAITING_SAMPLES = "blocked_awaiting_samples"
    BLOCKED_AWAITING_GOLDEN_OUTPUTS = "blocked_awaiting_golden_outputs"
    BLOCKED_AWAITING_AUDIT_WORKFLOW = "blocked_awaiting_audit_workflow"

    # Technical blocks
    BLOCKED_INVALID_CONTRACTS = "blocked_invalid_contracts"
    BLOCKED_ROUTER_NOT_WIRED = "blocked_router_not_wired"

    # Success states
    READY = "ready"
    COMPLETED = "completed"

    def __str__(self) -> str:
        return self.value


class ExcelInputRole(str, Enum):
    """
    Input file roles for Excel processing.

    These roles will be defined by business-provided contracts.
    Current values are placeholders pending business specification.
    """
    SOURCE_DATA = "source_data"
    CONFIGURATION = "configuration"
    REFERENCE = "reference"
    RATE_TABLE = "rate_table"
    AGENT_LIST = "agent_list"
    UNKNOWN = "unknown"


class ExcelOutputRole(str, Enum):
    """
    Output file roles for Excel processing.

    These will be defined by business-provided contracts.
    """
    COMMISSION_REPORT = "commission_report"
    VALIDATION_REPORT = "validation_report"
    AUDIT_TRAIL = "audit_trail"
    OUTPUT_DATA = "output_data"
    UNKNOWN = "unknown"


class ExcelFileMetadata(StrictModel):
    """Metadata for an Excel file in a processing job."""
    filename: str
    role: ExcelInputRole | ExcelOutputRole
    sheet_name: str | None = None
    size_bytes: int | None = None
    sha256_hash: str | None = None
    uploaded_at: datetime = Field(default_factory=utc_now)


class ExcelJobCreateRequest(StrictModel):
    """
    Request to create a new Excel processing job.

    IMPORTANT: Schema is placeholder pending business requirements.
    When business assets arrive, this will be updated to match
    the actual input/output contracts.
    """
    task_name: str = Field(..., min_length=1, description="Human-readable task name")
    input_files: list[ExcelFileMetadata] = Field(
        default_factory=list,
        description="Input files with roles",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Processing options (TBD based on business requirements)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional job metadata",
    )

    @field_validator("input_files", mode="before")
    @classmethod
    def validate_input_files(cls, value: Any) -> list[ExcelFileMetadata]:
        """Validate input files have proper roles."""
        if isinstance(value, list):
            # Convert dicts to ExcelFileMetadata if needed
            result = []
            for item in value:
                if isinstance(item, dict):
                    result.append(ExcelFileMetadata(**item))
                elif isinstance(item, ExcelFileMetadata):
                    result.append(item)
                else:
                    raise ValueError(f"Invalid file metadata: {item}")
            return result
        return value or []


class ExcelJobRead(StrictModel):
    """Response model for Excel job read operations."""
    job_id: str
    task_name: str
    status: JobStatus
    input_files: list[ExcelFileMetadata]
    output_files: list[ExcelFileMetadata]
    validation_status: str | None = None
    review_status: str | None = None
    approval_status: str | None = None
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Business-specific fields will be added when contracts arrive
    commission_results: dict[str, Any] | None = Field(
        default=None,
        description="Commission calculation results (TBD)",
    )
    validation_results: dict[str, Any] | None = Field(
        default=None,
        description="Validation results (TBD)",
    )


class ExcelJobStatusResponse(StrictModel):
    """Response for job status queries."""
    job_id: str
    status: JobStatus
    ready_for_calculation: bool = False
    ready_for_validation: bool = False
    blocked_reason: str | None = None
    next_steps: list[str] = Field(default_factory=list)


class ExcelValidationRequest(StrictModel):
    """
    Request to validate Excel job outputs.

    Validation rules will be defined by business-provided contracts.
    """
    job_id: str
    validation_type: str = Field(
        ...,
        description="Type of validation to perform (TBD based on business requirements)",
    )
    options: dict[str, Any] = Field(default_factory=dict)


class ExcelValidationResult(StrictModel):
    """Result of Excel job validation."""
    job_id: str
    validation_type: str
    status: str  # 'passed', 'failed', 'blocked'
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    findings: list[dict[str, Any]] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=utc_now)


class CommissionCalculationRequest(StrictModel):
    """
    Request for commission calculation.

    IMPORTANT: This is a placeholder. Actual schema will be
    defined by business-provided Excel contracts.
    """
    job_id: str
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Normalized input data from Excel files",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the calculation",
    )
    rules_override: dict[str, Any] | None = Field(
        default=None,
        description="Optional rule overrides (for testing only)",
    )


class CommissionCalculationResponse(StrictModel):
    """Response for commission calculation."""
    job_id: str
    status: str  # 'calculated', 'blocked_awaiting_contracts', 'error'
    calculated_values: dict[str, Any] = Field(default_factory=dict)
    applied_rules: list[str] = Field(default_factory=list)
    intermediate_steps: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    calculated_at: datetime | None = None


class Requirement4StatusResponse(StrictModel):
    """
    Response for requirement #4 readiness status.

    Indicates what scaffolding is in place and what business
    assets are still required. Uses granular blocked states for clarity.
    """
    # Overall readiness
    ready_for_business_assets: bool = False
    scaffold_complete: bool = False

    # Granular blocked state tracking
    blocked_states: dict[str, bool] = Field(
        default_factory=lambda: {
            "contracts": False,  # Excel input/output contracts provided
            "ambiguity_decisions": False,  # 7-category checklist provided
            "samples": False,  # Real Excel sample files provided
            "golden_outputs": False,  # Golden outputs + audit loop provided
            "audit_workflow": False,  # Approval workflow defined
        }
    )

    # Detailed missing assets with descriptions
    missing_assets: list[dict[str, str]] = Field(
        default_factory=lambda: [
            {
                "asset": "Excel input/output contracts",
                "state": "blocked_awaiting_contracts",
                "location": "tests/fixtures/requirement4_contracts/",
                "description": "File schemas, column mappings, validation rules",
            },
            {
                "asset": "Ambiguity checklist (7 categories)",
                "state": "blocked_awaiting_ambiguity_decisions",
                "location": "tests/fixtures/requirement4_contracts/",
                "description": "Decisions for data completeness, validation, calculations, agent mapping, time periods, rate tiers, adjustments",
            },
            {
                "asset": "Real Excel sample files",
                "state": "blocked_awaiting_samples",
                "location": "tests/fixtures/requirement4_samples/",
                "description": "1-3 files with real or realistic data matching production use cases",
            },
            {
                "asset": "Golden outputs + audit loop",
                "state": "blocked_awaiting_golden_outputs",
                "location": "tests/fixtures/requirement4_golden/",
                "description": "Expected calculation results, tolerances, and approval criteria",
            },
            {
                "asset": "Audit workflow definition",
                "state": "blocked_awaiting_audit_workflow",
                "location": "docs/requirement4/",
                "description": "Approval process, sign-off criteria, and tolerance specifications",
            },
        ]
    )

    # Engineering scaffold components
    available_components: list[dict[str, str]] = Field(
        default_factory=lambda: [
            {
                "component": "Excel jobs repository",
                "file": "src/autoresearch/core/repositories/excel_jobs.py",
                "status": "complete",
            },
            {
                "component": "Commission engine interface",
                "file": "src/autoresearch/core/services/commission_engine.py",
                "status": "complete",
            },
            {
                "component": "Excel ops service",
                "file": "src/autoresearch/core/services/excel_ops.py",
                "status": "complete",
            },
            {
                "component": "Excel ops router",
                "file": "src/autoresearch/api/routers/excel_ops.py",
                "status": "complete",
            },
            {
                "component": "Fixture directories",
                "location": "tests/fixtures/requirement4_*/",
                "status": "complete",
            },
            {
                "component": "Contract tests",
                "file": "tests/test_excel_ops_service.py",
                "status": "complete",
            },
        ]
    )

    # Next steps for implementation
    next_steps: list[str] = Field(
        default_factory=lambda: [
            "1. Business provides 4 required assets",
            "2. Engineering maps samples to input roles",
            "3. Engineering encodes ambiguity decisions into rules",
            "4. Engineering adds golden fixtures",
            "5. Engineering implements deterministic rules in commission_engine",
            "6. Engineering runs fixture-vs-golden tests",
            "7. Business reviews results and provides approval",
            "8. Enable pilot workflow",
        ]
    )

    # Current blocked state (if any)
    current_blocked_state: str | None = None

    # Router registration status
    router_registered: bool = False
    router_wired: bool = False

    # Verification status
    verification_status: str = "not_verified"  # "verified", "failed", "not_verified"
