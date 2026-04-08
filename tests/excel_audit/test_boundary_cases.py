"""Golden test group 2: Boundary cases.

Tests zero values, empty rows, missing columns, single-row data.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from excel_audit.contracts import ExcelAuditRule, ParsedSheet, SheetMapping
from excel_audit.parser import parse_workbook
from excel_audit.reconcile import reconcile
from excel_audit.rules_engine import evaluate_rules, _eval_simple_formula, _eval_condition

pytest.importorskip("openpyxl")
from openpyxl import Workbook


@pytest.fixture()
def boundary_dir(tmp_path: Path) -> Path:
    d = tmp_path / "boundary"
    d.mkdir()

    wb = Workbook()
    ws = wb.active
    ws.title = "数据"
    ws.append(["订单编号", "销售额", "提成比例"])
    ws.append(["B001", 0, 0.05])
    ws.append(["B002", 100, 0])
    ws.append(["B003", 0, 0])
    # Empty row
    ws.append([None, None, None])
    ws.append(["B004", 500, 0.10])
    wb.save(d / "boundary.xlsx")
    wb.close()

    return d


class TestBoundaryCases:
    """Group 2: boundary conditions."""

    def test_zero_sales_zero_rate(self) -> None:
        result = _eval_simple_formula("销售额 * 提成比例", {"销售额": 0, "提成比例": 0.05})
        assert result == 0.0

    def test_zero_rate(self) -> None:
        result = _eval_simple_formula("销售额 * 提成比例", {"销售额": 100, "提成比例": 0})
        assert result == 0.0

    def test_both_zero(self) -> None:
        result = _eval_simple_formula("销售额 * 提成比例", {"销售额": 0, "提成比例": 0})
        assert result == 0.0

    def test_empty_formula(self) -> None:
        result = _eval_simple_formula("", {"销售额": 100})
        assert result is None

    def test_missing_column_returns_none(self) -> None:
        result = _eval_simple_formula("不存在的列 * 0.1", {})
        assert result is None

    def test_condition_always_true_when_empty(self) -> None:
        assert _eval_condition("", {"状态": "任意"}) is True

    def test_condition_string_match(self) -> None:
        assert _eval_condition("状态 == 完成", {"状态": "完成"}) is True
        assert _eval_condition("状态 == 完成", {"状态": "取消"}) is False

    def test_condition_numeric_comparison(self) -> None:
        assert _eval_condition("金额 > 100", {"金额": 200}) is True
        assert _eval_condition("金额 > 100", {"金额": 50}) is False

    def test_parse_skips_blank_rows(self, boundary_dir: Path) -> None:
        wb = parse_workbook(str(boundary_dir / "boundary.xlsx"))
        rows = wb.sheets["数据"].rows
        # 4 data rows (blank row skipped)
        assert len(rows) == 4

    def test_evaluate_rules_with_zero_values(self, boundary_dir: Path) -> None:
        wb = parse_workbook(str(boundary_dir / "boundary.xlsx"))
        rows = wb.sheets["数据"].rows

        rules = [ExcelAuditRule(id="r1", name="calc", formula="销售额 * 提成比例")]
        result = evaluate_rules(rules, rows, expected_column="提成金额")
        # Source doesn't have 提成金额 column, so no comparisons happen
        assert result.rules_evaluated == 1

    def test_reconcile_empty_target(self) -> None:
        source = ParsedSheet(
            sheet_name="src",
            headers=["key", "val"],
            rows=[{"key": "K1", "val": 100}],
        )
        target = ParsedSheet(sheet_name="tgt", headers=["key", "val"], rows=[])
        mapping = SheetMapping(source="src", target="tgt", key_column="key")
        result = reconcile(source, target, mapping)
        assert result.rows_checked == 1
        # K1 exists in source but not in target
        assert len(result.findings) == 1
        assert "missing" in result.findings[0].cause.lower()
