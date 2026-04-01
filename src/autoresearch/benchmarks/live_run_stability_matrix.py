from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autoresearch.agent_protocol.models import DriverResult, ValidationReport
from autoresearch.executions.failure_classifier import classify_failure


@dataclass(frozen=True)
class LiveRunMatrixRow:
    task_id: str
    task_name: str
    lane: str
    model_provider: str | None
    result: str
    failure_status: str | None
    failure_layer: str | None
    failure_stage: str | None
    duration_sec: float | None
    retry_result: str | None
    retry_budget: int | None
    retry_attempts_used: int | None
    notes: str | None


def generate_live_run_regression_matrix(
    *,
    tasks_path: Path,
    run_roots: list[Path],
) -> list[LiveRunMatrixRow]:
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    rows: list[LiveRunMatrixRow] = []
    for task in tasks.get("tasks", []):
        task_id = str(task.get("task_id") or "")
        task_name = str(task.get("name") or "")
        run_summary = _load_run_summary(run_roots, task_id)
        if run_summary is None:
            rows.append(
                LiveRunMatrixRow(
                    task_id=task_id,
                    task_name=task_name,
                    lane="benchmark",
                    model_provider=None,
                    result="missing",
                    failure_status=None,
                    failure_layer=None,
                    failure_stage=None,
                    duration_sec=None,
                    retry_result=None,
                    retry_budget=_optional_int(task.get("retry_attempts")),
                    retry_attempts_used=None,
                    notes="no summary.json found",
                )
            )
            continue

        driver_payload = run_summary.get("driver_result")
        validation_payload = run_summary.get("validation")
        if not isinstance(driver_payload, dict) or not isinstance(validation_payload, dict):
            rows.append(
                LiveRunMatrixRow(
                    task_id=task_id,
                    task_name=task_name,
                    lane=str(task.get("lane") or "benchmark"),
                    model_provider=_optional_string(run_summary.get("model_provider")),
                    result=str(run_summary.get("final_status") or run_summary.get("result") or "unknown"),
                    failure_status=_optional_string(run_summary.get("failure_status")),
                    failure_layer=_optional_string(run_summary.get("failure_layer")),
                    failure_stage=_optional_string(run_summary.get("failure_stage")),
                    duration_sec=_optional_float(run_summary.get("duration_seconds")),
                    retry_result=_resolve_retry_result(run_summary, None),
                    retry_budget=_resolve_retry_budget(task, run_summary),
                    retry_attempts_used=_resolve_retry_attempts_used(run_summary, None),
                    notes="summary missing driver_result or validation",
                )
            )
            continue

        driver_result = DriverResult.model_validate(driver_payload)
        validation = ValidationReport.model_validate(validation_payload)
        classification = classify_failure(
            driver_result=driver_result,
            validation=validation,
            metadata=run_summary.get("metadata") if isinstance(run_summary.get("metadata"), dict) else None,
        )
        rows.append(
            LiveRunMatrixRow(
                task_id=task_id,
                task_name=task_name,
                lane=str(task.get("lane") or "benchmark"),
                model_provider=_optional_string(run_summary.get("model_provider")),
                result=str(run_summary.get("final_status") or run_summary.get("result") or "unknown"),
                failure_status=_optional_string(run_summary.get("failure_status")) or classification.failure_status,
                failure_layer=_optional_string(run_summary.get("failure_layer")) or classification.failure_layer,
                failure_stage=_optional_string(run_summary.get("failure_stage")),
                duration_sec=_optional_float(run_summary.get("duration_seconds")),
                retry_result=_resolve_retry_result(run_summary, driver_result),
                retry_budget=_resolve_retry_budget(task, run_summary),
                retry_attempts_used=_resolve_retry_attempts_used(run_summary, driver_result),
                notes=_optional_string(run_summary.get("notes")),
            )
        )
    return rows


def render_live_run_regression_matrix_json(rows: list[LiveRunMatrixRow]) -> str:
    return json.dumps([row.__dict__ for row in rows], ensure_ascii=False, indent=2, sort_keys=True)


def render_live_run_regression_matrix_markdown(rows: list[LiveRunMatrixRow]) -> str:
    header = "| task_id | task_name | lane | model_provider | result | failure_status | failure_layer | failure_stage | duration_sec | retry_result | retry_budget | retry_attempts_used | notes |"
    divider = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    lines = [header, divider]
    for row in rows:
        cells = [
            _md(row.task_id),
            _md(row.task_name),
            _md(row.lane),
            _md(row.model_provider),
            _md(row.result),
            _md(row.failure_status),
            _md(row.failure_layer),
            _md(row.failure_stage),
            _md(None if row.duration_sec is None else f"{row.duration_sec:.3f}"),
            _md(row.retry_result),
            _md(None if row.retry_budget is None else str(row.retry_budget)),
            _md(None if row.retry_attempts_used is None else str(row.retry_attempts_used)),
            _md(row.notes),
        ]
        lines.append(
            "| "
            + " | ".join(cells)
            + " |"
        )
    return "\n".join(lines) + "\n"


def write_live_run_regression_matrix(
    *,
    tasks_path: Path,
    run_roots: list[Path],
    json_path: Path,
    markdown_path: Path,
) -> list[LiveRunMatrixRow]:
    rows = generate_live_run_regression_matrix(tasks_path=tasks_path, run_roots=run_roots)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(render_live_run_regression_matrix_json(rows), encoding="utf-8")
    markdown_path.write_text(render_live_run_regression_matrix_markdown(rows), encoding="utf-8")
    return rows


def _load_run_summary(run_roots: list[Path], task_id: str) -> dict[str, Any] | None:
    for root in run_roots:
        summary_path = root / task_id / "summary.json"
        if summary_path.exists():
            return json.loads(summary_path.read_text(encoding="utf-8"))
    return None


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _retry_metadata(run_summary: dict[str, Any]) -> dict[str, Any]:
    metadata = run_summary.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    retry_metadata = metadata.get("live_run_retry")
    return dict(retry_metadata) if isinstance(retry_metadata, dict) else {}


def _resolve_retry_result(run_summary: dict[str, Any], driver_result: DriverResult | None) -> str | None:
    explicit = _optional_string(run_summary.get("retry_result"))
    if explicit is not None:
        return explicit
    metadata_result = _optional_string(_retry_metadata(run_summary).get("result"))
    if metadata_result is not None:
        return metadata_result
    if driver_result is None:
        return None
    if driver_result.attempt > 1:
        result = _optional_string(run_summary.get("final_status")) or _optional_string(run_summary.get("result"))
        if result in {"completed", "ready_for_promotion", "promoted"}:
            return "recovered"
        return "retried"
    return None


def _resolve_retry_budget(task: dict[str, Any], run_summary: dict[str, Any]) -> int | None:
    explicit = _optional_int(run_summary.get("retry_budget"))
    if explicit is not None:
        return explicit
    metadata_budget = _optional_int(_retry_metadata(run_summary).get("budget"))
    if metadata_budget is not None:
        return metadata_budget
    return _optional_int(task.get("retry_attempts"))


def _resolve_retry_attempts_used(run_summary: dict[str, Any], driver_result: DriverResult | None) -> int | None:
    explicit = _optional_int(run_summary.get("retry_attempts_used"))
    if explicit is not None:
        return explicit
    metadata_attempts = _optional_int(_retry_metadata(run_summary).get("attempts_used"))
    if metadata_attempts is not None:
        return metadata_attempts
    if driver_result is None:
        return None
    return max(int(driver_result.attempt) - 1, 0)


def _md(value: str | None) -> str:
    return "" if value is None else str(value).replace("|", "\\|")
