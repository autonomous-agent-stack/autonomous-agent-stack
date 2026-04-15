"""
Excel Jobs Repository - SQLite-backed local job state

Stores Excel processing job records including:
- Job metadata (input files, status, timestamps)
- Audit markers (validation, review, approval states)
- Artifact references (input/output file paths)
- Hash verification for reproducibility
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autoresearch.shared.models import JobStatus, StrictModel, utc_now
from autoresearch.shared.store import Repository, create_resource_id, SQLiteModelRepository

logger = logging.getLogger(__name__)


class ExcelJobMetadata(StrictModel):
    """Metadata for an Excel processing job."""
    job_id: str
    task_name: str
    input_files: list[str]
    status: JobStatus = JobStatus.CREATED
    created_at: datetime = utc_now()
    updated_at: datetime = utc_now()
    error_message: str | None = None
    metadata: dict[str, Any] = {}


class ExcelJobAuditMarkers(StrictModel):
    """Audit and review markers for Excel jobs."""
    job_id: str
    validation_status: str | None = None  # 'passed', 'failed', 'blocked'
    review_status: str | None = None  # 'pending', 'approved', 'rejected'
    approval_status: str | None = None  # 'pending', 'approved', 'rejected'
    reviewed_by: str | None = None
    approved_by: str | None = None
    reviewed_at: datetime | None = None
    approved_at: datetime | None = None
    audit_trail: list[dict[str, Any]] = []


class ExcelJobArtifacts(StrictModel):
    """Artifact references for Excel jobs."""
    job_id: str
    input_hashes: dict[str, str]  # filename -> SHA256
    output_files: list[str]
    patch_file: str | None = None
    report_file: str | None = None
    created_at: datetime = utc_now()


class ExcelJobRecord(StrictModel):
    """Complete Excel job record."""
    metadata: ExcelJobMetadata
    audit: ExcelJobAuditMarkers
    artifacts: ExcelJobArtifacts


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


class ExcelJobsRepository:
    """
    Repository for Excel processing job records.

    Uses SQLite for persistence. Jobs are stored with metadata,
    audit markers, and artifact references.
    """

    def __init__(self, db_path: Path, table_name: str = "excel_jobs") -> None:
        """
        Initialize repository.

        Args:
            db_path: Path to SQLite database file
            table_name: Name of jobs table (for multi-tenancy if needed)
        """
        self._db_path = db_path
        self._table_name = table_name
        self._repo = SQLiteModelRepository(
            db_path=db_path,
            table_name=table_name,
            model_cls=ExcelJobRecord,
        )
        logger.info("ExcelJobsRepository initialized: %s (table: %s)", db_path, table_name)

    def create(
        self,
        task_name: str,
        input_files: list[str],
        metadata: dict[str, Any] | None = None,
    ) -> ExcelJobRecord:
        """
        Create a new Excel job record.

        Args:
            task_name: Human-readable task name
            input_files: List of input file paths
            metadata: Additional metadata

        Returns:
            Created job record
        """
        job_id = create_resource_id("excel")
        now = utc_now()

        job_metadata = ExcelJobMetadata(
            job_id=job_id,
            task_name=task_name,
            input_files=input_files,
            status=JobStatus.CREATED,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        job_audit = ExcelJobAuditMarkers(job_id=job_id)

        # Compute hashes for input files
        input_hashes = {}
        for file_path in input_files:
            path = Path(file_path)
            if path.exists():
                input_hashes[path.name] = compute_file_hash(path)

        job_artifacts = ExcelJobArtifacts(
            job_id=job_id,
            input_hashes=input_hashes,
            output_files=[],
        )

        record = ExcelJobRecord(
            metadata=job_metadata,
            audit=job_audit,
            artifacts=job_artifacts,
        )

        self._repo.save(job_id, record)
        logger.info("Created Excel job: %s (%s)", job_id, task_name)
        return record

    def get(self, job_id: str) -> ExcelJobRecord | None:
        """Get job record by ID."""
        return self._repo.get(job_id)

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: str | None = None,
    ) -> ExcelJobRecord | None:
        """
        Update job status.

        Args:
            job_id: Job ID
            status: New status
            error_message: Optional error message

        Returns:
            Updated record, or None if not found
        """
        record = self._repo.get(job_id)
        if record is None:
            return None

        record.metadata.status = status
        record.metadata.updated_at = utc_now()
        if error_message:
            record.metadata.error_message = error_message

        self._repo.save(job_id, record)
        logger.info("Updated job %s status to %s", job_id, status.value)
        return record

    def add_artifact(
        self,
        job_id: str,
        artifact_type: str,
        file_path: str,
    ) -> ExcelJobRecord | None:
        """
        Add output artifact to job.

        Args:
            job_id: Job ID
            artifact_type: Type of artifact ('output', 'patch', 'report')
            file_path: Path to artifact file

        Returns:
            Updated record, or None if not found
        """
        record = self._repo.get(job_id)
        if record is None:
            return None

        if artifact_type == "output":
            record.artifacts.output_files.append(file_path)
        elif artifact_type == "patch":
            record.artifacts.patch_file = file_path
        elif artifact_type == "report":
            record.artifacts.report_file = file_path

        record.metadata.updated_at = utc_now()
        self._repo.save(job_id, record)
        return record

    def set_validation_status(
        self,
        job_id: str,
        validation_status: str,
    ) -> ExcelJobRecord | None:
        """
        Set validation status for job.

        Args:
            job_id: Job ID
            validation_status: 'passed', 'failed', or 'blocked'

        Returns:
            Updated record, or None if not found
        """
        record = self._repo.get(job_id)
        if record is None:
            return None

        record.audit.validation_status = validation_status
        record.metadata.updated_at = utc_now()

        # Add to audit trail
        record.audit.audit_trail.append({
            "timestamp": utc_now().isoformat(),
            "event": "validation_status_set",
            "status": validation_status,
        })

        self._repo.save(job_id, record)
        return record

    def list_by_status(self, status: JobStatus) -> list[ExcelJobRecord]:
        """List all jobs with given status."""
        all_jobs = self._repo.list()
        return [job for job in all_jobs if job.metadata.status == status]

    def list_all(self) -> list[ExcelJobRecord]:
        """List all jobs."""
        return self._repo.list()

    def delete(self, job_id: str) -> bool:
        """
        Delete job record.

        Args:
            job_id: Job ID to delete

        Returns:
            True if deleted, False if not found
        """
        import sqlite3

        try:
            with sqlite3.connect(self._db_path) as connection:
                cursor = connection.execute(
                    f"DELETE FROM {self._table_name} WHERE resource_id = ?",
                    (job_id,),
                )
                connection.commit()
                return cursor.rowcount > 0
        except Exception:
            return False
