from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

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
    task_count: int


def build_live_run_agent_command(*, repo_root: Path, task: dict[str, Any]) -> list[str]:
    prompt = str(task.get("prompt") or task.get("name") or "")
    task_id = str(task.get("task_id") or "unknown")
    command = [
        str(repo_root / ".venv" / "bin" / "python"),
        "scripts/agent_run.py",
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

        summary = normalize_live_run_summary(task=task, summary=executor(task, run_dir))
        summary_path = run_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    write_live_run_regression_matrix(
        tasks_path=tasks_path,
        run_roots=[run_root],
        json_path=matrix_json_path,
        markdown_path=matrix_markdown_path,
    )
    return LiveRunBenchmarkResult(
        tasks_path=tasks_path,
        run_root=run_root,
        matrix_json_path=matrix_json_path,
        matrix_markdown_path=matrix_markdown_path,
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


def normalize_live_run_summary(*, task: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
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
    explicit = summary.get("retry_result")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    if retry_budget <= 0:
        return "not_requested"
    if retry_attempts_used <= 0:
        return "not_needed" if _summary_succeeded(summary) else "not_attempted"
    return "recovered" if _summary_succeeded(summary) else "exhausted"


def _summary_succeeded(summary: dict[str, Any]) -> bool:
    status = _summary_status(summary)
    if status in _SUCCESS_SUMMARY_RESULTS:
        return True
    driver_result = summary.get("driver_result")
    return isinstance(driver_result, dict) and str(driver_result.get("status") or "").strip() == "succeeded"


def _summary_status(summary: dict[str, Any]) -> str:
    return str(summary.get("final_status") or summary.get("result") or "").strip()
