from __future__ import annotations

import json
from pathlib import Path

from autoresearch.benchmarks.live_run_stability_matrix import (
    generate_live_run_regression_matrix,
    render_live_run_regression_matrix_json,
    render_live_run_regression_matrix_markdown,
    write_live_run_regression_matrix,
)
from autoresearch.benchmarks.live_run_stability_runner import (
    build_live_run_agent_command,
    build_live_run_agent_env,
    run_live_run_stability_benchmark,
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


def test_live_run_benchmark_runner_writes_run_dirs_and_matrix(tmp_path: Path) -> None:
    tasks_path = tmp_path / "benchmarks" / "tasks.json"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [
                    {"task_id": "ok", "name": "ok task"},
                    {"task_id": "partial", "name": "partial task"},
                ],
            }
        ),
        encoding="utf-8",
    )

    def executor(task: dict[str, object], run_dir: Path) -> dict[str, object]:
        task_id = str(task["task_id"])
        if task_id == "ok":
            return {
                "final_status": "completed",
                "result": "completed",
                "duration_seconds": 1.5,
                "driver_result": {
                    "run_id": task_id,
                    "agent_id": "agent",
                    "status": "succeeded",
                    "summary": "ok",
                    "metrics": {"duration_ms": 1500, "steps": 1, "commands": 1},
                    "recommended_action": "promote",
                },
                "validation": {"run_id": task_id, "passed": True, "checks": []},
                "metadata": {},
            }
        return {
            "final_status": "failed",
            "result": "failed",
            "driver_result": {
                "run_id": task_id,
                "agent_id": "agent",
                "status": "contract_error",
                "summary": "boom",
                "metrics": {"duration_ms": 0, "steps": 0, "commands": 0},
                "recommended_action": "human_review",
            },
            "validation": {"run_id": task_id, "passed": True, "checks": []},
        }

    result = run_live_run_stability_benchmark(
        tasks_path=tasks_path,
        run_root=tmp_path / "runs",
        matrix_json_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json",
        matrix_markdown_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.md",
        executor=executor,
    )

    assert result.task_count == 2
    assert (tmp_path / "runs" / "ok" / "summary.json").exists()
    assert (tmp_path / "runs" / "ok" / "task.json").exists()
    assert (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json").exists()
    assert (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.md").exists()
    matrix = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json").read_text(
            encoding="utf-8"
        )
    )
    assert matrix[0]["task_id"] == "ok"
    assert matrix[0]["result"] == "completed"
    assert matrix[1]["failure_status"] == "infra_error"


def test_live_run_benchmark_runner_handles_partial_summaries_conservatively(
    tmp_path: Path,
) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps({"suite_name": "live-run-stability", "tasks": [{"task_id": "partial", "name": "partial"}]}),
        encoding="utf-8",
    )

    def executor(task: dict[str, object], run_dir: Path) -> dict[str, object]:
        _ = task, run_dir
        return {"final_status": "failed"}

    run_live_run_stability_benchmark(
        tasks_path=tasks_path,
        run_root=tmp_path / "runs",
        matrix_json_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json",
        matrix_markdown_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.md",
        executor=executor,
    )

    matrix = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json").read_text(
            encoding="utf-8"
        )
    )
    assert matrix[0]["task_id"] == "partial"
    assert matrix[0]["result"] == "failed"
    assert matrix[0]["failure_status"] is None


def test_live_run_agent_env_prefers_repo_venv_and_src(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".venv" / "bin").mkdir(parents=True)
    monkeypatch.setenv("PYTHONPATH", "/foreign/path")
    env = build_live_run_agent_env(repo_root)

    assert str(repo_root / ".venv" / "bin") in env["PATH"]
    assert str(repo_root / "src") in env["PYTHONPATH"]


def test_build_live_run_agent_command_includes_retry_when_task_requests_it(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / ".venv" / "bin").mkdir(parents=True)

    command = build_live_run_agent_command(
        repo_root=repo_root,
        task={
            "task_id": "queue-smoke",
            "prompt": "run the queue smoke benchmark",
            "retry_attempts": 2,
        },
    )

    assert command == [
        str(repo_root / ".venv" / "bin" / "python"),
        "scripts/agent_run.py",
        "--agent",
        "openhands",
        "--task",
        "run the queue smoke benchmark",
        "--run-id",
        "queue-smoke",
        "--retry",
        "2",
    ]


def test_build_live_run_agent_command_omits_retry_when_task_does_not_request_it(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / ".venv" / "bin").mkdir(parents=True)

    command = build_live_run_agent_command(
        repo_root=repo_root,
        task={
            "task_id": "queue-summary-audit",
            "name": "summary audit",
        },
    )

    assert command == [
        str(repo_root / ".venv" / "bin" / "python"),
        "scripts/agent_run.py",
        "--agent",
        "openhands",
        "--task",
        "summary audit",
        "--run-id",
        "queue-summary-audit",
    ]


def test_matrix_derives_retry_result_from_attempt_count(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps({"suite_name": "live-run-stability", "tasks": [{"task_id": "retry", "name": "retry"}]}),
        encoding="utf-8",
    )

    run_root = tmp_path / "runs"
    (run_root / "retry").mkdir(parents=True)
    (run_root / "retry" / "summary.json").write_text(
        json.dumps(
            {
                "final_status": "completed",
                "result": "completed",
                "driver_result": {
                    "run_id": "retry",
                    "agent_id": "agent",
                    "attempt": 2,
                    "status": "succeeded",
                    "summary": "recovered after retry",
                    "metrics": {"duration_ms": 20, "steps": 2, "commands": 2},
                    "recommended_action": "promote",
                },
                "validation": {"run_id": "retry", "passed": True, "checks": []},
            }
        ),
        encoding="utf-8",
    )

    rows = generate_live_run_regression_matrix(tasks_path=tasks_path, run_roots=[run_root])

    assert rows[0].retry_result == "retried"
