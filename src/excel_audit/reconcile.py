"""Cross-sheet reconciliation for Excel audit.

Compares source data against target/expected data at the row level,
detecting mismatches and computing diff amounts.

Pure deterministic logic — no LLM.
"""
from __future__ import annotations

import logging
from typing import Any

from excel_audit.contracts import (
    AuditFinding,
    AuditResult,
    AuditSeverity,
    ParsedSheet,
    SheetMapping,
)

logger = logging.getLogger(__name__)

_DEFAULT_TOLERANCE = 1e-6


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_key_index(
    rows: list[dict[str, Any]],
    key_column: str,
) -> dict[str, dict[str, Any]]:
    """Index rows by key column value for O(1) lookup."""
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        key_val = str(row.get(key_column, ""))
        if key_val:
            index[key_val] = row
    return index


def reconcile(
    source: ParsedSheet,
    target: ParsedSheet,
    mapping: SheetMapping,
    *,
    compare_columns: list[str] | None = None,
    tolerance: float = _DEFAULT_TOLERANCE,
) -> AuditResult:
    """Reconcile source sheet against target sheet.

    For each row in source, look up the matching row in target by key_column.
    Compare the specified columns and emit findings for mismatches.

    Args:
        source: Parsed source sheet (e.g. sales detail).
        target: Parsed target sheet (e.g. commission calculation).
        mapping: Sheet mapping with key_column for joining.
        compare_columns: Columns to compare. If None, compare all common columns.
        tolerance: Numeric comparison tolerance.

    Returns:
        AuditResult with findings for all mismatches.
    """
    key_col = mapping.key_column
    if not key_col:
        logger.warning("No key_column specified in mapping, skipping reconciliation")
        return AuditResult(rows_checked=len(source.rows))

    target_index = _build_key_index(target.rows, key_col)

    # Determine columns to compare
    if compare_columns:
        cols = compare_columns
    else:
        source_set = set(source.headers)
        target_set = set(target.headers)
        cols = [h for h in source.headers if h in target_set and h != key_col]

    findings: list[AuditFinding] = []
    rows_checked = 0

    for idx, src_row in enumerate(source.rows):
        key_val = str(src_row.get(key_col, ""))
        if not key_val:
            continue

        tgt_row = target_index.get(key_val)
        rows_checked += 1

        if tgt_row is None:
            findings.append(AuditFinding(
                row_index=idx,
                rule_id="reconcile_missing_target",
                severity=AuditSeverity.WARNING,
                key_value=key_val,
                cause=f"Key '{key_val}' found in source but missing in target",
            ))
            continue

        for col in cols:
            src_val = src_row.get(col)
            tgt_val = tgt_row.get(col)

            # Try numeric comparison
            src_num = _to_float(src_val)
            tgt_num = _to_float(tgt_val)

            if src_num is not None and tgt_num is not None:
                diff = abs(src_num - tgt_num)
                if diff > tolerance:
                    findings.append(AuditFinding(
                        row_index=idx,
                        rule_id=f"reconcile_diff_{col}",
                        severity=AuditSeverity.WARNING if diff < 100 else AuditSeverity.ERROR,
                        key_value=key_val,
                        expected=round(src_num, 2),
                        actual=round(tgt_num, 2),
                        difference=round(diff, 2),
                        cause=f"Column '{col}' mismatch for key '{key_val}': source={src_num:.2f}, target={tgt_num:.2f}",
                    ))
            else:
                # String comparison
                if str(src_val) != str(tgt_val):
                    findings.append(AuditFinding(
                        row_index=idx,
                        rule_id=f"reconcile_diff_{col}",
                        severity=AuditSeverity.INFO,
                        key_value=key_val,
                        expected=src_val,
                        actual=tgt_val,
                        cause=f"Column '{col}' mismatch for key '{key_val}'",
                    ))

    return AuditResult(
        rules_evaluated=len(cols),
        rows_checked=rows_checked,
        findings=findings,
    )
