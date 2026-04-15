"""Deterministic rules engine for Excel audit.

Evaluates structured rules (from RuleDsl) against parsed data.
Supports:
  - Conditional matching (``when`` clauses)
  - Simple arithmetic formulas (``formula`` fields)
  - Numeric comparison with configurable tolerance

LLM is NEVER used for computation. All evaluation is pure Python.
"""
from __future__ import annotations

import logging
import math
import operator
import re
from typing import Any

from excel_audit.contracts import (
    AuditFinding,
    AuditResult,
    AuditSeverity,
    ExcelAuditRule,
)

logger = logging.getLogger(__name__)

# Tolerance for floating-point comparisons
_DEFAULT_TOLERANCE = 1e-6

# Supported binary operators in formula expressions
_BINARY_OPS: dict[str, Any] = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
}


def _to_float(value: Any) -> float | None:
    """Attempt to convert a value to float."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _eval_simple_formula(formula: str, row: dict[str, Any]) -> float | None:
    """Evaluate a simple arithmetic formula against a row.

    Supports expressions like ``销售额 * 提成比例`` or ``原提成 - 退款金额 * 提成比例``.
    Operator precedence follows Python rules (* and / before + and -).
    Only column name references and numeric literals are allowed.
    """
    if not formula or not formula.strip():
        return None

    # Tokenise: split on operators while keeping them
    tokens = re.split(r"\s*([+\-*/])\s*", formula.strip())
    if not tokens:
        return None

    def resolve(token: str) -> float | None:
        token = token.strip()
        if not token:
            return None
        # Try as number literal
        try:
            return float(token)
        except ValueError:
            pass
        # Resolve as column name
        val = row.get(token)
        return _to_float(val)

    # Shunting-yard style: handle * / first pass, then + -
    values: list[float | None] = []
    ops: list[str] = []

    for i, token in enumerate(tokens):
        token = token.strip()
        if not token:
            continue
        if token in _BINARY_OPS:
            ops.append(token)
        else:
            values.append(resolve(token))

    if not values:
        return None

    # First pass: * and /
    i = 0
    while i < len(ops):
        if ops[i] in ("*", "/"):
            left = values[i]
            right = values[i + 1]
            if left is None or right is None:
                values[i] = None
            elif ops[i] == "/" and right == 0:
                values[i] = None
            else:
                values[i] = _BINARY_OPS[ops[i]](left, right)
            del values[i + 1]
            del ops[i]
        else:
            i += 1

    # Second pass: + and -
    result = values[0]
    for i, op in enumerate(ops):
        right = values[i + 1]
        if result is None or right is None:
            result = None
        else:
            result = _BINARY_OPS[op](result, right)

    return result


def _eval_condition(condition: str, row: dict[str, Any]) -> bool:
    """Evaluate a simple condition like ``订单状态 == 已完成``."""
    if not condition or not condition.strip():
        return True  # no condition means always apply

    condition = condition.strip()

    for op_str in ("==", "!=", ">=", "<=", ">", "<"):
        if op_str in condition:
            parts = condition.split(op_str, 1)
            if len(parts) != 2:
                continue
            left_name = parts[0].strip()
            right_literal = parts[1].strip()
            left_val = row.get(left_name)

            # Try numeric comparison first
            left_num = _to_float(left_val)
            right_num: float | None = None
            try:
                right_num = float(right_literal)
            except ValueError:
                pass

            if left_num is not None and right_num is not None:
                cmp_ops: dict[str, Any] = {
                    "==": operator.eq, "!=": operator.ne,
                    ">": operator.gt, "<": operator.lt,
                    ">=": operator.ge, "<=": operator.le,
                }
                return cmp_ops[op_str](left_num, right_num)

            # String comparison
            left_str = str(left_val) if left_val is not None else ""
            right_str = right_literal
            if op_str == "==":
                return left_str == right_str
            if op_str == "!=":
                return left_str != right_str
            return False

    return True


def evaluate_rule(
    rule: ExcelAuditRule,
    rows: list[dict[str, Any]],
    *,
    expected_column: str = "",
    tolerance: float = _DEFAULT_TOLERANCE,
) -> list[AuditFinding]:
    """Evaluate a single rule against all rows.

    For each row:
      1. Check the ``when`` condition — skip if false.
      2. Evaluate the ``formula`` to get the *computed* value.
      3. Compare against ``expected_column`` in the row (if provided).
      4. Emit an AuditFinding if values differ beyond tolerance.

    Args:
        rule: The rule to evaluate.
        rows: Parsed data rows.
        expected_column: Column name holding the expected value.
        tolerance: Max acceptable difference for numeric comparison.

    Returns:
        List of findings for rows that mismatch.
    """
    findings: list[AuditFinding] = []

    for idx, row in enumerate(rows):
        if not _eval_condition(rule.when, row):
            continue

        computed = _eval_simple_formula(rule.formula, row)
        if computed is None:
            continue

        if not expected_column:
            continue

        actual_raw = row.get(expected_column)
        actual = _to_float(actual_raw)

        if actual is None:
            findings.append(AuditFinding(
                row_index=idx,
                rule_id=rule.id,
                severity=AuditSeverity.WARNING,
                key_value=str(row.get("订单编号", "")),
                expected=computed,
                actual=actual_raw,
                cause=f"Expected column '{expected_column}' is non-numeric or missing",
            ))
            continue

        diff = abs(computed - actual)
        if diff > tolerance:
            findings.append(AuditFinding(
                row_index=idx,
                rule_id=rule.id,
                severity=AuditSeverity.WARNING if diff < 100 else AuditSeverity.ERROR,
                key_value=str(row.get("订单编号", "")),
                expected=round(computed, 2),
                actual=round(actual, 2),
                difference=round(diff, 2),
                cause=f"Rule '{rule.name}' mismatch: expected {computed:.2f}, got {actual:.2f}",
            ))

    return findings


def evaluate_rules(
    rules: list[ExcelAuditRule],
    rows: list[dict[str, Any]],
    *,
    expected_column: str = "",
    tolerance: float = _DEFAULT_TOLERANCE,
) -> AuditResult:
    """Evaluate all rules and return an AuditResult."""
    all_findings: list[AuditFinding] = []

    for rule in rules:
        findings = evaluate_rule(rule, rows, expected_column=expected_column, tolerance=tolerance)
        all_findings.extend(findings)

    return AuditResult(
        rules_evaluated=len(rules),
        rows_checked=len(rows),
        findings=all_findings,
    )
