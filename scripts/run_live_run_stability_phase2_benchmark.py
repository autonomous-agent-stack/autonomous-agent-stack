#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoresearch.benchmarks.live_run_stability_phase2 import (
    build_live_run_stability_phase2_paths,
    run_live_run_stability_phase2_benchmark,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the live-run stability phase-2 benchmark")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="repository root",
    )
    parser.add_argument(
        "--tasks-path",
        default=None,
        help="optional override for the phase-2 tasks manifest",
    )
    parser.add_argument(
        "--benchmark-root",
        default=None,
        help="optional override for the phase-2 benchmark output root",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    tasks_path = Path(args.tasks_path).resolve() if args.tasks_path else None
    benchmark_root = Path(args.benchmark_root).resolve() if args.benchmark_root else None
    paths = build_live_run_stability_phase2_paths(
        repo_root=repo_root,
        tasks_path=tasks_path,
        benchmark_root=benchmark_root,
    )
    result = run_live_run_stability_phase2_benchmark(
        repo_root=repo_root,
        tasks_path=paths.tasks_path,
        benchmark_root=paths.benchmark_root,
    )
    print(
        json.dumps(
            {
                "task_count": result.task_count,
                "tasks_path": str(paths.tasks_path),
                "benchmark_root": str(paths.benchmark_root),
                "run_root": str(result.run_root),
                "matrix_json_path": str(result.matrix_json_path),
                "matrix_markdown_path": str(result.matrix_markdown_path),
                "retry_overview_json_path": str(result.retry_overview_json_path),
                "gate_report_json_path": str(paths.gate_report_json_path),
                "gate_passed": bool(result.gate_passed),
            },
            indent=2,
        )
    )
    return 0 if result.gate_passed is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
