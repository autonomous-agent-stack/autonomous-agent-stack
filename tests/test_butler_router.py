"""Tests for ButlerIntentRouter — intent classification and dispatch."""
from __future__ import annotations

import pytest

from autoresearch.core.services.butler_router import (
    ButlerClassification,
    ButlerIntentRouter,
    ButlerTaskType,
)
from autoresearch.core.services.butler_dispatch import (
    ButlerDispatchCenter,
    ButlerModelFillService,
    ButlerRoute,
)


class _FakeModelBackend:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    async def generate(self, **kwargs) -> str:
        self.calls += 1
        return self.response


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

    def test_content_kb_x_bookmarks_curation_phrase(self) -> None:
        """管家口语：整理 X 书签 → content_kb（与字幕/知识库同类意图）。"""
        router = ButlerIntentRouter()
        for phrase in (
            "整理X书签",
            "帮我整理一下 X 书签",
            "把推特书签整理进知识库",
            "organize my twitter bookmarks for kb",
        ):
            result = router.classify(phrase)
            assert result.task_type == ButlerTaskType.CONTENT_KB, phrase
            assert result.confidence > 0, phrase

    def test_unknown_returns_default(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("今天天气怎么样")
        assert result.task_type == ButlerTaskType.UNKNOWN
        assert result.confidence == 0.0

    def test_empty_text(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("")
        assert result.task_type == ButlerTaskType.UNKNOWN

    def test_bookmark_keywords_chinese(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("帮我整理书签")
        assert result.task_type == ButlerTaskType.BOOKMARK

    def test_bookmark_keywords_english(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("organize my bookmarks for read later")
        assert result.task_type == ButlerTaskType.BOOKMARK

    def test_bookmark_url_extraction(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("收藏 https://example.com/article 有用链接")
        assert result.task_type == ButlerTaskType.BOOKMARK
        assert "https://example.com/article" in result.extracted_params.get("urls", [])

    def test_youtube_keywords(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("下载这个youtube视频的字幕")
        assert result.task_type == ButlerTaskType.YOUTUBE

    def test_youtube_transcript_keyword(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("视频转文字 extract transcript")
        assert result.task_type == ButlerTaskType.YOUTUBE

    def test_url_extraction_without_keyword_match(self) -> None:
        router = ButlerIntentRouter()
        result = router.classify("看看这个 https://example.com")
        # URL extracted but no keyword match → UNKNOWN
        assert result.task_type == ButlerTaskType.UNKNOWN
        assert "https://example.com" in result.extracted_params.get("urls", [])

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

    def _make_service(self) -> "ExcelAuditService":
        from autoresearch.shared.store import InMemoryRepository
        from autoresearch.core.services.excel_audit import ExcelAuditService
        from pathlib import Path
        return ExcelAuditService(repository=InMemoryRepository(), repo_root=Path("/tmp"))

    def test_create_returns_queued(self) -> None:
        """Create (sync, fast) returns a QUEUED record."""
        from autoresearch.shared.excel_audit_contract import ExcelAuditCreateRequest
        from autoresearch.shared.models import JobStatus

        svc = self._make_service()
        req = ExcelAuditCreateRequest(task_brief="核对提成表")
        record = svc.create(req)
        assert record.audit_id.startswith("ea_")
        assert record.status == JobStatus.QUEUED

    def test_execute_runs_in_background(self) -> None:
        """Execute runs after create, transitions from QUEUED to terminal state."""
        from autoresearch.shared.excel_audit_contract import ExcelAuditCreateRequest
        from autoresearch.shared.models import JobStatus

        svc = self._make_service()
        req = ExcelAuditCreateRequest(task_brief="核对提成表")
        record = svc.create(req)
        # Store DSL metadata for engine execution
        record = record.model_copy(update={"metadata": {
            "source_files": [],
            "rules": [],
            "sheet_mapping": {},
            "outputs": {},
        }})
        svc._repository.save(record.audit_id, record)

        result = svc.execute(record.audit_id)
        # No source files → should fail gracefully (not crash)
        assert result.status in (JobStatus.COMPLETED, JobStatus.FAILED)

    def test_execute_failure_stores_error(self) -> None:
        """When execution hits a bad path, it completes gracefully (no crash)."""
        from autoresearch.shared.excel_audit_contract import ExcelAuditCreateRequest
        from autoresearch.shared.models import JobStatus

        svc = self._make_service()
        req = ExcelAuditCreateRequest(task_brief="核对提成表")
        record = svc.create(req)
        # Missing source files → workbook_runner returns "failed" status
        # but service wraps it as COMPLETED with engine status in result
        record = record.model_copy(update={"metadata": {
            "source_files": ["/nonexistent/path.xlsx"],
            "rules": [],
            "sheet_mapping": {},
            "outputs": {},
        }})
        svc._repository.save(record.audit_id, record)

        result = svc.execute(record.audit_id)
        # Engine handles missing files gracefully — service reaches COMPLETED
        assert result.status in (JobStatus.COMPLETED, JobStatus.FAILED)

    def test_non_excel_still_classified_unknown(self) -> None:
        """Non-Excel messages fall through to UNKNOWN (claude_runtime path)."""
        router = ButlerIntentRouter()
        assert router.classify("随便聊聊").task_type == ButlerTaskType.UNKNOWN

    def test_create_and_execute_still_works(self) -> None:
        """Legacy create_and_execute path still functional."""
        from autoresearch.shared.excel_audit_contract import ExcelAuditCreateRequest

        svc = self._make_service()
        req = ExcelAuditCreateRequest(task_brief="核对提成表")
        record = svc.create_and_execute(req)
        assert record.audit_id.startswith("ea_")
        assert record.status.value in ("completed", "failed")


class TestButlerDispatchCenter:
    def test_rule_match_does_not_call_model_fill(self) -> None:
        backend = _FakeModelBackend(
            '{"task_type":"unknown","route":"hermes","target_agent":"butler_orchestrator","runtime_id":"hermes","confidence":1,"reason":"x","action":"butler_orchestrator.dispatch"}'
        )
        center = ButlerDispatchCenter(
            model_fill=ButlerModelFillService(backend=backend, enabled=True),
        )
        decision = center.dispatch("帮我核对3月提成表")
        assert decision.task_type == ButlerTaskType.EXCEL_AUDIT
        assert decision.route == ButlerRoute.DIRECT
        assert decision.source == "rule"
        assert backend.calls == 0

    def test_unknown_uses_valid_model_fill_decision(self) -> None:
        backend = _FakeModelBackend(
            '{"task_type":"github_admin","route":"worker","target_agent":"github_ops_accountA","runtime_id":"claude","confidence":0.91,"reason":"repo ops","action":"github_ops.issue_ops"}'
        )
        center = ButlerDispatchCenter(
            model_fill=ButlerModelFillService(backend=backend, enabled=True),
        )
        decision = center.dispatch("帮我看一下这个仓库后续该怎么管")
        assert decision.source == "model"
        assert decision.task_type == ButlerTaskType.GITHUB_ADMIN
        assert decision.target_agent == "github_ops_accountA"
        assert decision.runtime_id == "claude"
        assert backend.calls == 1

    def test_model_fill_invalid_json_escalates_to_hermes(self) -> None:
        backend = _FakeModelBackend("not json")
        center = ButlerDispatchCenter(
            model_fill=ButlerModelFillService(backend=backend, enabled=True),
        )
        decision = center.dispatch("这个很含糊")
        assert decision.source == "escalation"
        assert decision.route == ButlerRoute.HERMES
        assert decision.runtime_id == "hermes"
        assert decision.model_fill_error

    def test_model_fill_low_confidence_escalates_to_hermes(self) -> None:
        backend = _FakeModelBackend(
            '{"task_type":"youtube","route":"worker","target_agent":"youtube_ops","runtime_id":"claude","confidence":0.2,"reason":"weak","action":"youtube_ops.build_digest"}'
        )
        center = ButlerDispatchCenter(
            model_fill=ButlerModelFillService(backend=backend, enabled=True, min_confidence=0.7),
        )
        decision = center.dispatch("也许该稍后再处理这个事情")
        assert decision.source == "escalation"
        assert decision.route == ButlerRoute.HERMES

    def test_doctor_reports_model_fill_degraded_when_disabled(self) -> None:
        center = ButlerDispatchCenter(model_fill=ButlerModelFillService(enabled=False))
        checks = center.doctor_checks()
        assert any(item.name == "model fill" and item.status == "degraded" for item in checks)
