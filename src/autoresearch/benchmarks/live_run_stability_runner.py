from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from autoresearch.benchmarks.live_run_stability_matrix import write_live_run_regression_matrix


class LiveRunTaskExecutor(Protocol):
    def __call__(self, task: dict[str, Any], run_dir: Path) -> dict[str, Any]: ...


@dataclass(frozen=True)
class LiveRunBenchmarkResult:
    tasks_path: Path
    run_root: Path
    matrix_json_path: Path
    matrix_markdown_path: Path
    task_count: int


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

        summary = executor(task, run_dir)
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
