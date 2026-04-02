from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from autoresearch.benchmarks.live_run_retry import (
    LIVE_RUN_RETRY_RESULT_VALUES,
    build_live_run_retry_result_counts,
    resolve_live_run_retry_result,
)
from autoresearch.benchmarks.live_run_stability_matrix import write_live_run_regression_matrix

_SUCCESS_SUMMARY_RESULTS = {"completed", "ready_for_promotion", "promoted", "succeeded"}


class LiveRunTaskExecutor(Protocol):
    def __call__(self, task: dict[str, Any], run_dir: Path) -> dict[str, Any]: ...


@dataclass(frozen=True)
class LiveRunBenchmarkResult:
    tasks_path: Path
    run_root: Path
    matrix_json_path: Path
    matrix_markdown_path: Path
    retry_overview_json_path: Path
    task_count: int


def build_live_run_agent_command(*, repo_root: Path, task: dict[str, Any]) -> list[str]:
    prompt = str(task.get("prompt") or task.get("name") or "")
    task_id = str(task.get("task_id") or "unknown")
    command = [
        str(repo_root / ".venv" / "bin" / "python"),
        "scripts/agent_run.py",
        "--repo-root",
        str(repo_root),
        "--agent",
        "openhands",
        "--task",
        prompt,
        "--run-id",
        task_id,
    ]
    retry_attempts = _task_retry_attempts(task)
    if retry_attempts > 0:
        command.extend(["--retry", str(retry_attempts)])
    return command


def run_live_run_stability_benchmark(
    *,
    tasks_path: Path,
    run_root: Path,
    matrix_json_path: Path,
    matrix_markdown_path: Path,
    retry_overview_json_path: Path,
    executor: LiveRunTaskExecutor,
) -> LiveRunBenchmarkResult:
    tasks = json.loads(tasks_path.read_text(encoding="utf-8"))
    run_root.mkdir(parents=True, exist_ok=True)

    task_count = 0
    for task in tasks.get("tasks", []):
        task_count += 1
        task_id = str(task.get("task_id") or "").strip()
        if not task_id:
            continue
        run_dir = run_root / task_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")

        summary = normalize_live_run_summary(task=task, summary=executor(task, run_dir), run_dir=run_dir)
        summary_path = run_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = write_live_run_regression_matrix(
        tasks_path=tasks_path,
        run_roots=[run_root],
        json_path=matrix_json_path,
        markdown_path=matrix_markdown_path,
    )
    retry_overview_json_path.parent.mkdir(parents=True, exist_ok=True)
    retry_overview_json_path.write_text(
        json.dumps(build_live_run_retry_overview(rows), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return LiveRunBenchmarkResult(
        tasks_path=tasks_path,
        run_root=run_root,
        matrix_json_path=matrix_json_path,
        matrix_markdown_path=matrix_markdown_path,
        retry_overview_json_path=retry_overview_json_path,
        task_count=task_count,
    )


def build_live_run_agent_env(repo_root: Path) -> dict[str, str]:
    env = dict(os.environ)
    src_path = str((repo_root / "src").resolve())
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src_path}:{pythonpath}" if pythonpath else src_path
    env["PATH"] = f"{(repo_root / '.venv' / 'bin').resolve()}:{env.get('PATH', '')}"
    return env


def _task_retry_attempts(task: dict[str, Any]) -> int:
    raw_value = task.get("retry_attempts")
    if raw_value is None:
        return 0
    try:
        return max(int(raw_value), 0)
    except (TypeError, ValueError):
        return 0


def normalize_live_run_summary(
    *,
    task: dict[str, Any],
    summary: dict[str, Any],
    run_dir: Path | None = None,
) -> dict[str, Any]:
    normalized = dict(summary)
    retry_budget = _task_retry_attempts(task)
    final_attempt = _summary_attempt(normalized)
    retry_attempts_used = max(final_attempt - 1, 0)
    retry_result = _summary_retry_result(
        summary=normalized,
        retry_budget=retry_budget,
        retry_attempts_used=retry_attempts_used,
    )

    normalized["retry_budget"] = retry_budget
    normalized["retry_attempts_used"] = retry_attempts_used
    normalized["retry_result"] = retry_result

    metadata = dict(normalized.get("metadata")) if isinstance(normalized.get("metadata"), dict) else {}
    retry_metadata = dict(metadata.get("live_run_retry")) if isinstance(metadata.get("live_run_retry"), dict) else {}
    retry_metadata.update(
        {
            "requested": retry_budget > 0,
            "budget": retry_budget,
            "attempts_used": retry_attempts_used,
            "final_attempt": final_attempt,
            "result": retry_result,
            "succeeded": _summary_succeeded(normalized),
            "final_status": _summary_status(normalized),
        }
    )
    metadata["live_run_retry"] = retry_metadata
    normalized["metadata"] = metadata
    if run_dir is not None:
        normalized["artifacts_produced"] = _normalize_live_run_artifacts_produced(
            artifacts=normalized.get("artifacts_produced"),
            run_dir=run_dir,
        )
    return normalized


def _normalize_live_run_artifacts_produced(*, artifacts: Any, run_dir: Path) -> list[str]:
    normalized = [str(run_dir / "summary.json")]
    if not isinstance(artifacts, list):
        return normalized

    run_dir_resolved = run_dir.resolve()
    for item in artifacts:
        candidate_text = str(item or "").strip()
        if not candidate_text:
            continue
        candidate = Path(candidate_text)
        artifact_path = candidate if candidate.is_absolute() else run_dir / candidate
        try:
            resolved = artifact_path.resolve()
        except OSError:
            continue
        if not resolved.exists():
            continue
        try:
            resolved.relative_to(run_dir_resolved)
        except ValueError:
            continue
        resolved_text = str(resolved)
        if resolved_text not in normalized:
            normalized.append(resolved_text)
    return normalized


def _summary_attempt(summary: dict[str, Any]) -> int:
    driver_result = summary.get("driver_result")
    if isinstance(driver_result, dict):
        raw_attempt = driver_result.get("attempt")
        try:
            return max(int(raw_attempt), 1)
        except (TypeError, ValueError):
            return 1
    return 1


def _summary_retry_result(
    *,
    summary: dict[str, Any],
    retry_budget: int,
    retry_attempts_used: int,
) -> str:
    return resolve_live_run_retry_result(
        explicit=summary.get("retry_result"),
        succeeded=_summary_succeeded(summary),
        retry_budget=retry_budget,
        retry_attempts_used=retry_attempts_used,
    )


def _summary_succeeded(summary: dict[str, Any]) -> bool:
    status = _summary_status(summary)
    if status in _SUCCESS_SUMMARY_RESULTS:
        return True
    driver_result = summary.get("driver_result")
    return isinstance(driver_result, dict) and str(driver_result.get("status") or "").strip() == "succeeded"


def _summary_status(summary: dict[str, Any]) -> str:
    return str(summary.get("final_status") or summary.get("result") or "").strip()


def build_live_run_retry_overview(rows: list[Any]) -> dict[str, Any]:
    counts = build_live_run_retry_result_counts()
    tasks: list[dict[str, Any]] = []
    retry_requested_task_count = 0
    retried_task_count = 0

    for row in rows:
        retry_result = getattr(row, "retry_result", None)
        if retry_result in LIVE_RUN_RETRY_RESULT_VALUES:
            counts[str(retry_result)] += 1
        retry_budget = getattr(row, "retry_budget", None)
        retry_attempts_used = getattr(row, "retry_attempts_used", None)
        if isinstance(retry_budget, int) and retry_budget > 0:
            retry_requested_task_count += 1
        if isinstance(retry_attempts_used, int) and retry_attempts_used > 0:
            retried_task_count += 1
        tasks.append(
            {
                "task_id": getattr(row, "task_id", ""),
                "task_name": getattr(row, "task_name", ""),
                "result": getattr(row, "result", None),
                "failure_status": getattr(row, "failure_status", None),
                "retry_result": getattr(row, "retry_result", None),
                "retry_budget": retry_budget,
                "retry_attempts_used": retry_attempts_used,
            }
        )

    return {
        "task_count": len(rows),
        "retry_requested_task_count": retry_requested_task_count,
        "retried_task_count": retried_task_count,
        "retry_result_counts": counts,
        "tasks": tasks,
    }
