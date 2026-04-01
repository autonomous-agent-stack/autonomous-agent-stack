from __future__ import annotations

import json
from pathlib import Path


def test_live_run_stability_benchmark_manifest_is_well_formed() -> None:
    manifest_path = Path("benchmarks/live-run-stability/tasks.json")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert data["suite_name"] == "live-run-stability"
    tasks = data["tasks"]
    assert 10 <= len(tasks) <= 14
    assert any(int(task.get("retry_attempts", 0)) > 0 for task in tasks)
    assert len({int(task.get("retry_attempts", 0)) for task in tasks}) >= 3

    for task in tasks:
        assert task["task_id"]
        assert task["name"]
        assert task["prompt"]
        assert task["expected_artifacts"]
        assert task["pass_conditions"]
        assert 60 <= int(task["max_duration_seconds"]) <= 900
        assert int(task.get("retry_attempts", 0)) >= 0
        assert "summary.json" in task["expected_artifacts"]
        assert task["main_failure_bucket"] in {
            "infra",
            "orchestration",
            "model",
            "business_validation",
        }

    assert {task["task_id"] for task in tasks} >= {
        "queue-fast-poll",
        "queue-deadline-guard",
        "queue-progress-starve",
        "queue-mock-fallback-check",
        "queue-business-assert",
        "queue-artifact-integrity",
        "queue-real-task-scan",
        "queue-long-run-pressure",
    }


def test_live_run_stability_regression_matrix_matches_manifest() -> None:
    manifest = json.loads(
        Path("benchmarks/live-run-stability/tasks.json").read_text(encoding="utf-8")
    )
    matrix = Path("benchmarks/live-run-stability/regression-matrix.md").read_text(
        encoding="utf-8"
    )

    assert "| Task ID |" in matrix
    assert "| Scenario |" in matrix
    assert "| Expected Artifacts |" in matrix
    assert "| Pass Condition |" in matrix
    assert "| Max Duration |" in matrix
    for task in manifest["tasks"][:4]:
        assert task["task_id"] in matrix
        assert task["name"] in matrix
