"""Excel audit deterministic engine.

Parse Excel files, evaluate structured rules, reconcile cross-sheet data,
and produce diff reports. No LLM is used for computation.
"""

from excel_audit.contracts import (
    AuditFinding,
    AuditReport,
    AuditResult,
    AuditSeverity,
    ExcelAuditRule,
    RuleDsl,
    SheetMapping,
)
from excel_audit.parser import parse_workbook
from excel_audit.reconcile import reconcile
from excel_audit.report import generate_report
from excel_audit.rules_engine import evaluate_rules
from excel_audit.workbook_runner import run_audit

__all__ = [
    "AuditFinding",
    "AuditReport",
    "AuditResult",
    "AuditSeverity",
    "ExcelAuditRule",
    "RuleDsl",
    "SheetMapping",
    "evaluate_rules",
    "generate_report",
    "parse_workbook",
    "reconcile",
    "run_audit",
]
