"""Golden test group 3: Error cases.

Tests missing files, invalid formats, empty sheets.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from excel_audit.contracts import RuleDsl, SheetMapping
from excel_audit.parser import parse_workbook
from excel_audit.workbook_runner import run_audit

pytest.importorskip("openpyxl")


class TestErrorCases:
    """Group 3: error handling."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            parse_workbook(str(tmp_path / "nonexistent.xlsx"))

    def test_invalid_file_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.xlsx"
        bad.write_text("this is not xlsx")
        with pytest.raises(ValueError, match="Failed to open"):
            parse_workbook(str(bad))

    def test_missing_sheet_returns_empty(self, tmp_path: Path) -> None:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Sheet1"
        ws.append(["col1", "col2"])
        wb.save(tmp_path / "test.xlsx")
        wb.close()

        result = parse_workbook(str(tmp_path / "test.xlsx"), sheet_names=["NonExistent"])
        assert "NonExistent" not in result.sheets

    def test_empty_sheet_parsed(self, tmp_path: Path) -> None:
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "Empty"
        wb.save(tmp_path / "empty.xlsx")
        wb.close()

        result = parse_workbook(str(tmp_path / "empty.xlsx"))
        sheet = result.sheets["Empty"]
        # openpyxl returns no rows for an entirely empty sheet
        assert sheet.rows == []

    def test_run_audit_no_source_files(self, tmp_path: Path) -> None:
        dsl = RuleDsl(
            business_case="commission_check",
            inputs={"source_files": []},
        )
        report = run_audit(dsl, job_id="empty_test")
        assert report.status == "failed"
        assert report.next_action == "retry"

    def test_run_audit_missing_source_file(self, tmp_path: Path) -> None:
        dsl = RuleDsl(
            business_case="commission_check",
            inputs={"source_files": [str(tmp_path / "missing.xlsx")]},
        )
        report = run_audit(dsl, job_id="missing_test")
        assert report.status == "failed"

    def test_api_service_create_and_get(self) -> None:
        from autoresearch.shared.excel_audit_contract import ExcelAuditCreateRequest
        from autoresearch.shared.store import InMemoryRepository
        from autoresearch.core.services.excel_audit import ExcelAuditService

        svc = ExcelAuditService(
            repository=InMemoryRepository(),
            repo_root=Path("/tmp"),
        )
        req = ExcelAuditCreateRequest(task_brief="核对3月提成")
        record = svc.create(req)
        assert record.audit_id.startswith("ea_")
        assert record.task_brief == "核对3月提成"

        fetched = svc.get(record.audit_id)
        assert fetched is not None
        assert fetched.audit_id == record.audit_id

    def test_api_service_list(self) -> None:
        from autoresearch.shared.excel_audit_contract import ExcelAuditCreateRequest
        from autoresearch.shared.store import InMemoryRepository
        from autoresearch.core.services.excel_audit import ExcelAuditService

        svc = ExcelAuditService(
            repository=InMemoryRepository(),
            repo_root=Path("/tmp"),
        )
        svc.create(ExcelAuditCreateRequest(task_brief="task1"))
        svc.create(ExcelAuditCreateRequest(task_brief="task2"))
        assert len(svc.list()) == 2

    def test_execute_nonexistent_raises(self) -> None:
        from autoresearch.shared.store import InMemoryRepository
        from autoresearch.core.services.excel_audit import ExcelAuditService

        svc = ExcelAuditService(
            repository=InMemoryRepository(),
            repo_root=Path("/tmp"),
        )
        with pytest.raises(ValueError, match="not found"):
            svc.execute("ea_nonexistent")
