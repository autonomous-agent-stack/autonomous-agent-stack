"""Excel audit service — API-layer orchestration.

Bridges the HTTP API to the deterministic excel_audit engine.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from autoresearch.shared.excel_audit_contract import (
    ExcelAuditCreateRequest,
    ExcelAuditRead,
    ExcelAuditResultRead,
)
from autoresearch.shared.models import JobStatus, utc_now
from autoresearch.shared.store import Repository, create_resource_id

logger = logging.getLogger(__name__)


class ExcelAuditService:
    def __init__(self, repository: Repository[ExcelAuditRead], repo_root: Path) -> None:
        self._repository = repository
        self._repo_root = repo_root

    def create(self, request: ExcelAuditCreateRequest) -> ExcelAuditRead:
        audit_id = create_resource_id("ea")
        now = utc_now()
        record = ExcelAuditRead(
            audit_id=audit_id,
            task_brief=request.task_brief,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
        )
        return self._repository.save(audit_id, record)

    def get(self, audit_id: str) -> ExcelAuditRead | None:
        return self._repository.get(audit_id)

    def list(self) -> list[ExcelAuditRead]:
        return self._repository.list()

    def execute(self, audit_id: str) -> ExcelAuditRead:
        """Execute a queued audit job."""
        record = self._repository.get(audit_id)
        if record is None:
            raise ValueError(f"Audit {audit_id} not found")
        if record.status not in (JobStatus.QUEUED, JobStatus.CREATED):
            raise ValueError(f"Audit {audit_id} is {record.status.value}, cannot execute")

        # Mark running
        record = record.model_copy(update={
            "status": JobStatus.RUNNING,
            "updated_at": utc_now(),
        })
        self._repository.save(audit_id, record)

        try:
            result = self._run_engine(record)
            record = record.model_copy(update={
                "status": JobStatus.COMPLETED,
                "result": result,
                "updated_at": utc_now(),
            })
        except Exception as exc:
            logger.exception("Excel audit %s failed", audit_id)
            record = record.model_copy(update={
                "status": JobStatus.FAILED,
                "error": str(exc),
                "updated_at": utc_now(),
            })

        self._repository.save(audit_id, record)
        return record

    def _run_engine(self, record: ExcelAuditRead) -> ExcelAuditResultRead:
        """Delegate to the deterministic engine."""
        from excel_audit.contracts import ExcelAuditRule, RuleDsl, SheetMapping
        from excel_audit.workbook_runner import run_audit

        # For now, use a default commission_check DSL from metadata
        meta = record.metadata
        source_files = meta.get("source_files", [])
        rules_raw = meta.get("rules", [])
        mapping_raw = meta.get("sheet_mapping", {})

        rules = [
            ExcelAuditRule(
                id=r.get("id", f"r{i}"),
                name=r.get("name", f"rule_{i}"),
                when=r.get("when", ""),
                formula=r.get("formula", ""),
            )
            for i, r in enumerate(rules_raw)
        ]

        mapping = SheetMapping(
            source=mapping_raw.get("source", ""),
            target=mapping_raw.get("target", ""),
            key_column=mapping_raw.get("key_column", ""),
        )

        dsl = RuleDsl(
            business_case="commission_check",
            inputs={"source_files": source_files},
            sheet_mapping=mapping,
            rules=rules,
            outputs=meta.get("outputs", {}),
        )

        output_dir = self._repo_root / "artifacts" / record.audit_id
        report = run_audit(dsl, job_id=record.audit_id, output_dir=output_dir)

        return ExcelAuditResultRead(
            rows_checked=report.result.rows_checked,
            rows_mismatched=report.result.rows_mismatched,
            mismatch_amount_total=report.result.mismatch_amount_total,
            findings_count=len(report.result.findings),
        )

    def create_and_execute(self, request: ExcelAuditCreateRequest) -> ExcelAuditRead:
        """Create and immediately execute an audit."""
        record = self.create(request)

        # Store DSL parameters in metadata for engine execution
        record = record.model_copy(update={
            "metadata": {
                "source_files": request.source_files,
                "rules": [r.model_dump() for r in request.rules],
                "sheet_mapping": request.sheet_mapping.model_dump(),
                "outputs": request.options,
            },
        })
        self._repository.save(record.audit_id, record)

        return self.execute(record.audit_id)
