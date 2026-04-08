"""Domain contracts for the excel_audit deterministic engine.

These models define the rule DSL, sheet mapping, and result structures.
They are intentionally separate from the API-layer models in
autoresearch.shared.excel_audit_contract to keep the engine self-contained.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Rule DSL
# ---------------------------------------------------------------------------

class ExcelAuditRule(StrictModel):
    """A single audit rule expressed in structured DSL."""
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    when: str = ""
    formula: str = ""
    description: str = ""


class SheetMapping(StrictModel):
    """Map logical names to physical sheet names in workbooks."""
    source: str = ""
    target: str = ""
    key_column: str = ""


class RuleDsl(StrictModel):
    """Full task specification in structured DSL form."""
    task_type: str = "excel_audit"
    business_case: str = "commission_check"
    inputs: dict[str, Any] = Field(default_factory=dict)
    sheet_mapping: SheetMapping = Field(default_factory=SheetMapping)
    rules: list[ExcelAuditRule] = Field(default_factory=list)
    outputs: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Parsed data structures
# ---------------------------------------------------------------------------

class ParsedSheet(StrictModel):
    """Rows extracted from a single Excel sheet."""
    sheet_name: str
    headers: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class ParsedWorkbook(StrictModel):
    """Collection of sheets parsed from one xlsx file."""
    file_path: str
    sheets: dict[str, ParsedSheet] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Evaluation & reconciliation results
# ---------------------------------------------------------------------------

class AuditSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AuditFinding(StrictModel):
    """A single row-level mismatch or issue."""
    row_index: int
    rule_id: str
    severity: AuditSeverity = AuditSeverity.WARNING
    key_value: str = ""
    expected: Any = None
    actual: Any = None
    difference: float | None = None
    cause: str = ""


class AuditResult(StrictModel):
    """Aggregated result of evaluating all rules against parsed data."""
    rules_evaluated: int = 0
    rows_checked: int = 0
    findings: list[AuditFinding] = Field(default_factory=list)

    @property
    def rows_mismatched(self) -> int:
        return len({f.row_index for f in self.findings})

    @property
    def mismatch_amount_total(self) -> float:
        return sum(f.difference or 0.0 for f in self.findings)


class AuditReport(StrictModel):
    """Full audit report with summary and row-level diffs."""
    job_id: str = ""
    status: str = "completed"
    result: AuditResult = Field(default_factory=AuditResult)
    artifacts: list[str] = Field(default_factory=list)
    next_action: str = "human_review"
