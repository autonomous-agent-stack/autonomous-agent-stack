"""Golden test group 4: Deliberate mismatches.

Creates data with known differences, verifies detection accuracy.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from excel_audit.contracts import (
    AuditSeverity,
    ExcelAuditRule,
    ParsedSheet,
    SheetMapping,
)
from excel_audit.parser import parse_workbook
from excel_audit.reconcile import reconcile
from excel_audit.rules_engine import evaluate_rules

pytest.importorskip("openpyxl")
from openpyxl import Workbook


@pytest.fixture()
def mismatch_dir(tmp_path: Path) -> Path:
    d = tmp_path / "mismatch"
    d.mkdir()

    # Source: exact known values
    wb = Workbook()
    ws = wb.active
    ws.title = "source"
    ws.append(["订单编号", "销售额", "提成金额"])
    ws.append(["M001", 10000, 500])
    ws.append(["M002", 20000, 1000])
    ws.append(["M003", 15000, 900])
    ws.append(["M004", 5000, 250])
    ws.append(["M005", 8000, 400])
    wb.save(d / "source.xlsx")
    wb.close()

    # Target: with deliberate differences
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.title = "target"
    ws2.append(["订单编号", "销售额", "提成金额"])
    ws2.append(["M001", 10000, 500])     # exact match
    ws2.append(["M002", 20000, 950])     # 50 short
    ws2.append(["M003", 15000, 900])     # match
    # M004 missing entirely
    ws2.append(["M005", 8000, 350])      # 50 short
    wb2.save(d / "target.xlsx")
    wb2.close()

    return d


class TestMismatchCases:
    """Group 4: deliberate mismatch detection."""

    def test_reconcile_finds_value_diffs(self, mismatch_dir: Path) -> None:
        src = parse_workbook(str(mismatch_dir / "source.xlsx"), sheet_names=["source"])
        tgt = parse_workbook(str(mismatch_dir / "target.xlsx"), sheet_names=["target"])

        result = reconcile(
            src.sheets["source"],
            tgt.sheets["target"],
            SheetMapping(source="source", target="target", key_column="订单编号"),
        )
        # M002: 提成金额 diff (1000 vs 950)
        # M004: missing in target
        # M005: 提成金额 diff (400 vs 350)
        assert result.rows_mismatched >= 3

    def test_reconcile_computes_correct_diff_amount(self, mismatch_dir: Path) -> None:
        src = parse_workbook(str(mismatch_dir / "source.xlsx"), sheet_names=["source"])
        tgt = parse_workbook(str(mismatch_dir / "target.xlsx"), sheet_names=["target"])

        result = reconcile(
            src.sheets["source"],
            tgt.sheets["target"],
            SheetMapping(source="source", target="target", key_column="订单编号"),
            compare_columns=["提成金额"],
        )

        # M002: 1000 - 950 = 50, M005: 400 - 350 = 50 → total 100
        total = result.mismatch_amount_total
        assert total == pytest.approx(100.0, abs=0.01)

    def test_reconcile_missing_key_flagged(self, mismatch_dir: Path) -> None:
        src = parse_workbook(str(mismatch_dir / "source.xlsx"), sheet_names=["source"])
        tgt = parse_workbook(str(mismatch_dir / "target.xlsx"), sheet_names=["target"])

        result = reconcile(
            src.sheets["source"],
            tgt.sheets["target"],
            SheetMapping(source="source", target="target", key_column="订单编号"),
        )
        missing_findings = [f for f in result.findings if "missing" in f.cause.lower()]
        assert len(missing_findings) >= 1
        assert any(f.key_value == "M004" for f in missing_findings)

    def test_rules_engine_detects_formula_mismatch(self) -> None:
        rows = [
            {"订单编号": "X1", "状态": "已完成", "金额": 1000, "比率": 0.1, "提成": 100},
            {"订单编号": "X2", "状态": "已完成", "金额": 2000, "比率": 0.1, "提成": 150},  # should be 200
            {"订单编号": "X3", "状态": "已取消", "金额": 500, "比率": 0.1, "提成": 50},    # skipped
        ]

        rules = [ExcelAuditRule(id="r1", name="commission", when="状态 == 已完成", formula="金额 * 比率")]
        result = evaluate_rules(rules, rows, expected_column="提成")

        # X1: 1000*0.1=100, actual=100 → match
        # X2: 2000*0.1=200, actual=150 → mismatch
        # X3: condition false → skipped
        assert len(result.findings) == 1
        assert result.findings[0].key_value == "X2"
        assert result.findings[0].difference == pytest.approx(50.0, abs=0.01)

    def test_large_diff_gets_error_severity(self) -> None:
        rows = [
            {"订单编号": "L1", "状态": "已完成", "金额": 100000, "比率": 0.1, "提成": 0},  # diff = 10000
        ]
        rules = [ExcelAuditRule(id="r1", name="commission", when="状态 == 已完成", formula="金额 * 比率")]
        result = evaluate_rules(rules, rows, expected_column="提成")
        assert result.findings[0].severity == AuditSeverity.ERROR
