from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Protocol

from autoresearch.shared.models import EvaluationCreateRequest, EvaluationRead, JobStatus, utc_now


class EvaluationRepository(Protocol):
    def create(
        self,
        evaluation: EvaluationRead,
        request: EvaluationCreateRequest,
    ) -> EvaluationRead: ...

    def update(self, evaluation: EvaluationRead) -> EvaluationRead: ...

    def get(self, evaluation_id: str) -> EvaluationRead | None: ...

    def list(self) -> list[EvaluationRead]: ...

    def interrupt_running(self, reason: str) -> int: ...


class SQLiteEvaluationRepository:
    """Persist evaluation state so API status survives service restarts."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def create(
        self,
        evaluation: EvaluationRead,
        request: EvaluationCreateRequest,
    ) -> EvaluationRead:
        self._upsert(evaluation, request_payload=request.model_dump(mode="json"))
        return evaluation

    def update(self, evaluation: EvaluationRead) -> EvaluationRead:
        self._upsert(evaluation)
        return evaluation

    def get(self, evaluation_id: str) -> EvaluationRead | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT *
                FROM evaluation_runs
                WHERE evaluation_id = ?
                """,
                (evaluation_id,),
            ).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def list(self) -> list[EvaluationRead]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM evaluation_runs
                ORDER BY created_at DESC, evaluation_id DESC
                """
            ).fetchall()
        return [self._row_to_model(row) for row in rows]

    def interrupt_running(self, reason: str) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE evaluation_runs
                SET status = ?,
                    result_status = ?,
                    summary = ?,
                    error = ?,
                    updated_at = ?
                WHERE status = ?
                """,
                (
                    JobStatus.INTERRUPTED.value,
                    JobStatus.INTERRUPTED.value,
                    reason,
                    reason,
                    utc_now().isoformat(),
                    JobStatus.RUNNING.value,
                ),
            )
            connection.commit()
        return cursor.rowcount

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_runs (
                    evaluation_id TEXT PRIMARY KEY,
                    task_name TEXT NOT NULL,
                    config_path TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_status TEXT,
                    run_id TEXT,
                    score REAL,
                    summary TEXT,
                    duration_seconds REAL,
                    artifact_dir TEXT,
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    request_json TEXT NOT NULL DEFAULT '{}',
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_evaluation_runs_status
                ON evaluation_runs(status)
                """
            )
            connection.commit()

    def _upsert(
        self,
        evaluation: EvaluationRead,
        request_payload: dict[str, object] | None = None,
    ) -> None:
        payload = {
            "evaluation_id": evaluation.evaluation_id,
            "task_name": evaluation.task_name,
            "config_path": evaluation.config_path,
            "description": evaluation.description,
            "status": evaluation.status.value,
            "result_status": evaluation.result_status,
            "run_id": evaluation.run_id,
            "score": evaluation.score,
            "summary": evaluation.summary,
            "duration_seconds": evaluation.duration_seconds,
            "artifact_dir": evaluation.artifact_dir,
            "metrics_json": json.dumps(evaluation.metrics, sort_keys=True),
            "metadata_json": json.dumps(evaluation.metadata, sort_keys=True),
            "request_json": (
                json.dumps(request_payload, sort_keys=True) if request_payload is not None else None
            ),
            "error": evaluation.error,
            "created_at": evaluation.created_at.isoformat(),
            "updated_at": evaluation.updated_at.isoformat(),
        }

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO evaluation_runs (
                    evaluation_id,
                    task_name,
                    config_path,
                    description,
                    status,
                    result_status,
                    run_id,
                    score,
                    summary,
                    duration_seconds,
                    artifact_dir,
                    metrics_json,
                    metadata_json,
                    request_json,
                    error,
                    created_at,
                    updated_at
                ) VALUES (
                    :evaluation_id,
                    :task_name,
                    :config_path,
                    :description,
                    :status,
                    :result_status,
                    :run_id,
                    :score,
                    :summary,
                    :duration_seconds,
                    :artifact_dir,
                    :metrics_json,
                    :metadata_json,
                    COALESCE(:request_json, '{}'),
                    :error,
                    :created_at,
                    :updated_at
                )
                ON CONFLICT(evaluation_id) DO UPDATE SET
                    task_name = excluded.task_name,
                    config_path = excluded.config_path,
                    description = excluded.description,
                    status = excluded.status,
                    result_status = excluded.result_status,
                    run_id = excluded.run_id,
                    score = excluded.score,
                    summary = excluded.summary,
                    duration_seconds = excluded.duration_seconds,
                    artifact_dir = excluded.artifact_dir,
                    metrics_json = excluded.metrics_json,
                    metadata_json = excluded.metadata_json,
                    request_json = COALESCE(excluded.request_json, evaluation_runs.request_json),
                    error = excluded.error,
                    updated_at = excluded.updated_at
                """,
                payload,
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _row_to_model(self, row: sqlite3.Row) -> EvaluationRead:
        return EvaluationRead(
            evaluation_id=row["evaluation_id"],
            task_name=row["task_name"],
            config_path=row["config_path"],
            description=row["description"],
            status=JobStatus(row["status"]),
            result_status=row["result_status"],
            run_id=row["run_id"],
            score=row["score"],
            summary=row["summary"],
            duration_seconds=row["duration_seconds"],
            artifact_dir=row["artifact_dir"],
            metrics=json.loads(row["metrics_json"] or "{}"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata_json"] or "{}"),
            error=row["error"],
        )
