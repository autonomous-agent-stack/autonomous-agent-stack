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
                    retry_result=_optional_string(run_summary.get("retry_result")),
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
                    notes=_optional_string(run_summary.get("notes")),
                )
            )
    return rows


def render_live_run_regression_matrix_json(rows: list[LiveRunMatrixRow]) -> str:
    return json.dumps([row.__dict__ for row in rows], ensure_ascii=False, indent=2, sort_keys=True)


def render_live_run_regression_matrix_markdown(rows: list[LiveRunMatrixRow]) -> str:
    header = "| task_id | task_name | lane | model_provider | result | failure_status | failure_layer | failure_stage | duration_sec | retry_result | notes |"
    divider = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
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


def _resolve_retry_result(run_summary: dict[str, Any], driver_result: DriverResult) -> str | None:
    explicit = _optional_string(run_summary.get("retry_result"))
    if explicit is not None:
        return explicit
    return "retried" if driver_result.attempt > 1 else None


def _md(value: str | None) -> str:
    return "" if value is None else str(value).replace("|", "\\|")
