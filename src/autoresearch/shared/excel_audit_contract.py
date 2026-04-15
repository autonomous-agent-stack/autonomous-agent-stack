"""API-layer contracts for excel_audit.

Follows the same Request/Read pattern as manager_agent_contract.py.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from autoresearch.shared.models import JobStatus, StrictModel


class ExcelAuditRulePayload(StrictModel):
    """A single rule in the request DSL."""
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    when: str = ""
    formula: str = ""
    description: str = ""


class SheetMappingPayload(StrictModel):
    source: str = ""
    target: str = ""
    key_column: str = ""


class ExcelAuditCreateRequest(StrictModel):
    """POST /api/v1/excel-audit payload."""
    task_brief: str = Field(..., min_length=1)
    source_files: list[str] = Field(default_factory=list)
    sheet_mapping: SheetMappingPayload = Field(default_factory=SheetMappingPayload)
    rules: list[ExcelAuditRulePayload] = Field(default_factory=list)
    options: dict[str, Any] = Field(default_factory=dict)


class ExcelAuditResultRead(StrictModel):
    rows_checked: int = 0
    rows_mismatched: int = 0
    mismatch_amount_total: float = 0.0
    findings_count: int = 0


class ExcelAuditRead(StrictModel):
    """Persisted audit record."""
    audit_id: str
    task_brief: str
    status: JobStatus = JobStatus.CREATED
    result: ExcelAuditResultRead = Field(default_factory=ExcelAuditResultRead)
    artifacts: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
