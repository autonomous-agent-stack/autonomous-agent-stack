#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from autoresearch.benchmarks.live_run_stability_runner import (
    build_live_run_agent_env,
    run_live_run_stability_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the live-run stability benchmark")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="repository root",
    )
    return parser.parse_args()


def _parse_summary(stdout: str) -> dict[str, object] | None:
    if not stdout.strip():
        return None
    try:
        parsed = json.loads(stdout)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        try:
            start = stdout.index("{")
            end = stdout.rindex("}") + 1
            parsed = json.loads(stdout[start:end])
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    tasks_path = repo_root / "benchmarks" / "live-run-stability" / "tasks.json"
    run_root = repo_root / "artifacts" / "live-run-stability" / "runs"
    matrix_json = repo_root / "artifacts" / "live-run-stability" / "regression-matrix.json"
    matrix_md = repo_root / "artifacts" / "live-run-stability" / "regression-matrix.md"
    env = build_live_run_agent_env(repo_root)

    def executor(task: dict[str, object], run_dir: Path) -> dict[str, object]:
        prompt = str(task.get("prompt") or task.get("name") or "")
        task_id = str(task.get("task_id") or "unknown")
        completed = subprocess.run(
            [
                str(repo_root / ".venv" / "bin" / "python"),
                "scripts/agent_run.py",
                "--agent",
                "openhands",
                "--task",
                prompt,
                "--run-id",
                task_id,
            ],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        summary = _parse_summary(stdout)
        if summary is None:
            summary = {
                "final_status": "failed",
                "result": "failed",
                "notes": (stderr or stdout or "agent_run produced no parseable summary")[:1000],
                "driver_result": {
                    "run_id": task_id,
                    "agent_id": "openhands",
                    "status": "contract_error",
                    "summary": (stderr or stdout or "empty output")[:1000],
                    "metrics": {"duration_ms": 0, "steps": 0, "commands": 0},
                    "recommended_action": "human_review",
                },
                "validation": {"run_id": task_id, "passed": False, "checks": []},
                "metadata": {},
            }
        summary.setdefault("metadata", {})
        metadata = dict(summary.get("metadata") or {})
        metadata["real_benchmark_returncode"] = completed.returncode
        metadata["real_benchmark_stdout_preview"] = stdout[:1000] if stdout else None
        metadata["real_benchmark_stderr_preview"] = stderr[:1000] if stderr else None
        summary["metadata"] = metadata
        return summary

    result = run_live_run_stability_benchmark(
        tasks_path=tasks_path,
        run_root=run_root,
        matrix_json_path=matrix_json,
        matrix_markdown_path=matrix_md,
        executor=executor,
    )
    print(
        json.dumps(
            {
                "task_count": result.task_count,
                "run_root": str(result.run_root),
                "matrix_json_path": str(result.matrix_json_path),
                "matrix_markdown_path": str(result.matrix_markdown_path),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
