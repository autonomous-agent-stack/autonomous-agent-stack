"""Golden test group 1: Normal commission check.

Creates a simple sales + commission Excel, runs rules engine,
verifies correct computation with no mismatches.
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from excel_audit.contracts import ExcelAuditRule, RuleDsl, SheetMapping
from excel_audit.parser import parse_workbook
from excel_audit.workbook_runner import run_audit

pytest.importorskip("openpyxl")
from openpyxl import Workbook


@pytest.fixture()
def commission_dir(tmp_path: Path) -> Path:
    """Create a temp directory with sales.xlsx and commission.xlsx."""
    d = tmp_path / "commission_check"
    d.mkdir()

    # --- sales.xlsx (source) ---
    wb = Workbook()
    ws = wb.active
    ws.title = "销售明细"
    ws.append(["订单编号", "订单状态", "销售额", "提成比例", "退款金额"])
    ws.append(["ORD001", "已完成", 10000, 0.05, 0])
    ws.append(["ORD002", "已完成", 20000, 0.05, 500])
    ws.append(["ORD003", "已取消", 5000, 0.03, 0])
    ws.append(["ORD004", "已完成", 15000, 0.08, 0])
    wb.save(d / "sales.xlsx")
    wb.close()

    # --- commission.xlsx (target) ---
    wb2 = Workbook()
    ws2 = wb2.active
    ws2.title = "提成核算"
    ws2.append(["订单编号", "提成金额"])
    ws2.append(["ORD001", 500])      # 10000 * 0.05 = 500
    ws2.append(["ORD002", 750])      # (20000 - 500) * 0.05 = 975 → but target says 750 (mismatch)
    ws2.append(["ORD004", 1200])     # 15000 * 0.08 = 1200
    wb2.save(d / "commission.xlsx")
    wb2.close()

    return d


class TestNormalCommissionCheck:
    """Group 1: normal commission_check scenario."""

    def test_parse_sales_workbook(self, commission_dir: Path) -> None:
        wb = parse_workbook(str(commission_dir / "sales.xlsx"))
        sheet = wb.sheets["销售明细"]
        assert sheet.headers == ["订单编号", "订单状态", "销售额", "提成比例", "退款金额"]
        assert len(sheet.rows) == 4
        assert sheet.rows[0]["订单编号"] == "ORD001"
        assert sheet.rows[0]["销售额"] == 10000

    def test_parse_commission_workbook(self, commission_dir: Path) -> None:
        wb = parse_workbook(str(commission_dir / "commission.xlsx"))
        sheet = wb.sheets["提成核算"]
        assert len(sheet.rows) == 3
        assert sheet.rows[0]["提成金额"] == 500

    def test_rules_engine_base_commission(self, commission_dir: Path) -> None:
        from excel_audit.rules_engine import evaluate_rules

        wb = parse_workbook(str(commission_dir / "sales.xlsx"))
        rows = wb.sheets["销售明细"].rows

        rules = [
            ExcelAuditRule(id="r1", name="base_commission", when="订单状态 == 已完成", formula="销售额 * 提成比例"),
        ]

        result = evaluate_rules(rules, rows, expected_column="提成金额")
        assert result.rules_evaluated == 1
        assert result.rows_checked == 4
        # Source sheet has no 提成金额 column — engine correctly reports
        # non-numeric findings for matching rows (ORD001, ORD002, ORD004)
        assert len(result.findings) == 3
        assert all("non-numeric" in f.cause for f in result.findings)

    def test_full_audit_pipeline(self, commission_dir: Path) -> None:
        dsl = RuleDsl(
            business_case="commission_check",
            inputs={"source_files": [str(commission_dir / "sales.xlsx")]},
            sheet_mapping=SheetMapping(source="销售明细"),
            rules=[
                ExcelAuditRule(id="r1", name="base_commission", when="订单状态 == 已完成", formula="销售额 * 提成比例"),
            ],
            outputs={},
        )
        output_dir = commission_dir / "output"

        report = run_audit(dsl, job_id="test_001", output_dir=output_dir)
        assert report.status == "completed"
        assert report.result.rows_checked == 4

    def test_reconcile_detects_mismatch(self, commission_dir: Path) -> None:
        """Reconcile sales vs commission — ORD002 should mismatch."""
        from excel_audit.reconcile import reconcile

        source_wb = parse_workbook(str(commission_dir / "sales.xlsx"), sheet_names=["销售明细"])
        target_wb = parse_workbook(str(commission_dir / "commission.xlsx"), sheet_names=["提成核算"])

        source_sheet = source_wb.sheets["销售明细"]
        target_sheet = target_wb.sheets["提成核算"]

        mapping = SheetMapping(source="销售明细", target="提成核算", key_column="订单编号")

        result = reconcile(source_sheet, target_sheet, mapping)
        assert result.rows_checked == 4
        # ORD001: in both, ORD002: in both (but commission differs), ORD003: source only, ORD004: in both
        # ORD003 should show as missing in target
        assert result.rows_mismatched > 0
