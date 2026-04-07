"""Top-level audit driver: orchestrates parse → rules → reconcile → report.

This is the single entry-point called by the API service / worker.
"""
from __future__ import annotations

import logging
from pathlib import Path

from excel_audit.contracts import (
    AuditReport,
    AuditResult,
    RuleDsl,
)
from excel_audit.parser import parse_workbook
from excel_audit.reconcile import reconcile
from excel_audit.report import generate_report
from excel_audit.rules_engine import evaluate_rules

logger = logging.getLogger(__name__)


def run_audit(
    dsl: RuleDsl,
    *,
    job_id: str = "",
    output_dir: str | Path | None = None,
) -> AuditReport:
    """Run a full audit pipeline from DSL to report.

    Steps:
        1. Parse source and target workbooks
        2. Evaluate rules against source data
        3. Reconcile source against target
        4. Merge findings
        5. Generate report artifacts

    Args:
        dsl: Structured task specification.
        job_id: Unique job identifier.
        output_dir: Directory for report artifacts. If None, uses ./artifacts/{job_id}.

    Returns:
        AuditReport with summary, findings, and artifact paths.
    """
    source_files = dsl.inputs.get("source_files", [])
    sheet_mapping = dsl.sheet_mapping

    if not source_files:
        return AuditReport(
            job_id=job_id,
            status="failed",
            result=AuditResult(),
            next_action="retry",
        )

    # Step 1: Parse workbooks
    workbooks = []
    for fp in source_files:
        path = Path(fp)
        if not path.exists():
            logger.warning("Source file not found: %s", fp)
            continue
        wb = parse_workbook(fp, sheet_names=[sheet_mapping.source, sheet_mapping.target] if sheet_mapping.source else None)
        workbooks.append(wb)

    if not workbooks:
        return AuditReport(
            job_id=job_id,
            status="failed",
            result=AuditResult(),
            next_action="retry",
        )

    # Collect source and target sheets across all workbooks
    source_rows: list[dict] = []
    target_rows: list[dict] = []
    source_sheet_obj = None
    target_sheet_obj = None

    for wb in workbooks:
        for name, sheet in wb.sheets.items():
            if name == sheet_mapping.source or not sheet_mapping.source:
                source_rows.extend(sheet.rows)
                source_sheet_obj = sheet
            if name == sheet_mapping.target:
                target_rows.extend(sheet.rows)
                target_sheet_obj = sheet

    # Step 2: Evaluate rules (if we have expected column in outputs config)
    expected_column = dsl.outputs.get("expected_column", "")
    rules_result = evaluate_rules(
        dsl.rules,
        source_rows,
        expected_column=expected_column,
    )

    # Step 3: Reconcile (if target sheet exists)
    reconcile_result = AuditResult()
    if target_sheet_obj and source_sheet_obj and sheet_mapping.key_column:
        compare_columns = dsl.outputs.get("compare_columns")
        reconcile_result = reconcile(
            source_sheet_obj,
            target_sheet_obj,
            sheet_mapping,
            compare_columns=compare_columns,
        )

    # Step 4: Merge findings
    merged = AuditResult(
        rules_evaluated=rules_result.rules_evaluated + reconcile_result.rules_evaluated,
        rows_checked=max(rules_result.rows_checked, reconcile_result.rows_checked),
        findings=rules_result.findings + reconcile_result.findings,
    )

    report = AuditReport(
        job_id=job_id,
        status="completed",
        result=merged,
        next_action="human_review",
    )

    # Step 5: Generate report artifacts
    if output_dir is None:
        output_dir = Path("artifacts") / (job_id or "latest")
    report = generate_report(report, output_dir)

    return report
