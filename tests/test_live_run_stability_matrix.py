from __future__ import annotations

import json
from pathlib import Path

from autoresearch.benchmarks.live_run_stability_matrix import (
    generate_live_run_regression_matrix,
    render_live_run_regression_matrix_json,
    render_live_run_regression_matrix_markdown,
    write_live_run_regression_matrix,
)


def test_matrix_generates_from_missing_and_present_summaries(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [
                    {"task_id": "a", "name": "task a"},
                    {"task_id": "b", "name": "task b"},
                ],
            }
        ),
        encoding="utf-8",
    )

    run_root = tmp_path / "runs"
    (run_root / "a").mkdir(parents=True)
    (run_root / "a" / "summary.json").write_text(
        json.dumps(
            {
                "final_status": "failed",
                "result": "failed",
                "failure_status": "infra_error",
                "failure_layer": "infra",
                "failure_stage": "adapter",
                "duration_seconds": 3.5,
                "model_provider": "mock-provider",
                "retry_result": "retry",
                "notes": "stable",
                "driver_result": {
                    "run_id": "a",
                    "agent_id": "agent",
                    "status": "contract_error",
                    "summary": "boom",
                    "metrics": {"duration_ms": 1, "steps": 0, "commands": 0},
                    "recommended_action": "human_review",
                },
                "validation": {"run_id": "a", "passed": True, "checks": []},
                "metadata": {"mock_fallback_enabled": False},
            }
        ),
        encoding="utf-8",
    )

    rows = generate_live_run_regression_matrix(tasks_path=tasks_path, run_roots=[run_root])
    assert len(rows) == 2
    assert rows[0].task_id == "a"
    assert rows[0].failure_status == "infra_error"
    assert rows[0].failure_layer == "infra"
    assert rows[1].result == "missing"
    assert rows[1].notes == "no summary.json found"

    json_text = render_live_run_regression_matrix_json(rows)
    md_text = render_live_run_regression_matrix_markdown(rows)
    assert '"task_id": "a"' in json_text
    assert "| a | task a |" in md_text
    assert "| b | task b |" in md_text


def test_matrix_writer_emits_baseline_files(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps({"suite_name": "live-run-stability", "tasks": []}),
        encoding="utf-8",
    )
    json_path = tmp_path / "out" / "matrix.json"
    md_path = tmp_path / "out" / "matrix.md"

    rows = write_live_run_regression_matrix(
        tasks_path=tasks_path,
        run_roots=[tmp_path / "runs"],
        json_path=json_path,
        markdown_path=md_path,
    )

    assert rows == []
    assert json_path.exists()
    assert md_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8")) == []
    assert "Live-Run Regression Matrix" not in md_path.read_text(encoding="utf-8")
