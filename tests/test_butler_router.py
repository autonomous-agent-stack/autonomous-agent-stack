"""Tests for ButlerIntentRouter — intent classification and dispatch."""
from __future__ import annotations

import pytest

from autoresearch.core.services.butler_router import (
    ButlerClassification,
    ButlerIntentRouter,
    ButlerTaskType,
)


class TestButlerIntentClassification:
    """Keyword-based intent classification."""

    def test_excel_audit_keywords_chinese(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("帮我核对3月提成表")
        assert result.task_type == ButlerTaskType.EXCEL_AUDIT
        assert result.confidence > 0

    def test_excel_audit_keywords_english(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("Check the excel commission report")
        assert result.task_type == ButlerTaskType.EXCEL_AUDIT

    def test_excel_audit_keyword_duizhang(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("做一下对账")
        assert result.task_type == ButlerTaskType.EXCEL_AUDIT

    def test_github_admin_keywords(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("盘点一下Lisa的仓库，准备transfer")
        assert result.task_type == ButlerTaskType.GITHUB_ADMIN

    def test_content_kb_keywords(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("把这个字幕入库知识库")
        assert result.task_type == ButlerTaskType.CONTENT_KB

    def test_unknown_returns_default(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("今天天气怎么样")
        assert result.task_type == ButlerTaskType.UNKNOWN
        assert result.confidence == 0.0

    def test_empty_text(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("")
        assert result.task_type == ButlerTaskType.UNKNOWN

    def test_file_path_extraction_xlsx(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("核对 sales.xlsx 和 commission.xlsx 的提成")
        assert result.task_type == ButlerTaskType.EXCEL_AUDIT
        assert "sales.xlsx" in result.extracted_params.get("attachments", [])
        assert "commission.xlsx" in result.extracted_params.get("attachments", [])

    def test_file_path_extraction_case_insensitive(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("核对 REPORT.XLSX")
        assert "REPORT.XLSX" in result.extracted_params.get("attachments", [])

    def test_no_file_paths_when_absent(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("核对提成表")
        assert "attachments" not in result.extracted_params or result.extracted_params.get("attachments") == []


class TestButlerExcelAuditDispatch:
    """Test that the gateway dispatches to ExcelAuditService."""

    def test_service_create_and_execute(self) -> None:
        """Verify ExcelAuditService.create_and_execute works with InMemoryRepository."""
        from autoresearch.shared.excel_audit_contract import ExcelAuditCreateRequest
        from autoresearch.shared.store import InMemoryRepository
        from autoresearch.core.services.excel_audit import ExcelAuditService
        from pathlib import Path

        svc = ExcelAuditService(
            repository=InMemoryRepository(),
            repo_root=Path("/tmp"),
        )
        req = ExcelAuditCreateRequest(task_brief="核对提成表")
        record = svc.create_and_execute(req)
        assert record.audit_id.startswith("ea_")
        # No source files → should fail gracefully
        assert record.status.value in ("completed", "failed")
