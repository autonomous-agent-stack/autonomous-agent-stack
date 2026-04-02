from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from autoresearch.agent_protocol.models import FallbackStep, JobSpec, ValidatorSpec
from autoresearch.benchmarks.live_run_retry import LIVE_RUN_RETRY_RESULT_VALUES
from autoresearch.benchmarks.live_run_stability_matrix import (
    generate_live_run_regression_matrix,
    render_live_run_regression_matrix_json,
    render_live_run_regression_matrix_markdown,
    write_live_run_regression_matrix,
)
from autoresearch.benchmarks.live_run_stability_runner import (
    build_live_run_agent_command,
    build_live_run_agent_env,
    build_live_run_retry_overview,
    normalize_live_run_summary,
    run_live_run_stability_benchmark,
)
from autoresearch.executions.runner import AgentExecutionRunner


def _write_manifest(repo_root: Path, agent_id: str, entrypoint: str) -> None:
    payload = {
        "id": agent_id,
        "kind": "process",
        "entrypoint": entrypoint,
        "version": "0.1",
    }
    manifest_path = repo_root / "configs" / "agents" / f"{agent_id}.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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
                "retry_result": "exhausted",
                "retry_budget": 2,
                "retry_attempts_used": 2,
                "notes": "stable",
                "driver_result": {
                    "run_id": "a",
                    "agent_id": "agent",
                    "attempt": 3,
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
    assert rows[0].retry_result == "exhausted"
    assert rows[0].retry_budget == 2
    assert rows[0].retry_attempts_used == 2
    assert rows[1].result == "missing"
    assert rows[1].notes == "no summary.json found"

    json_text = render_live_run_regression_matrix_json(rows)
    md_text = render_live_run_regression_matrix_markdown(rows)
    assert '"task_id": "a"' in json_text
    assert '"retry_budget": 2' in json_text
    assert "retry_attempts_used" in md_text
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
        retry_overview_json_path=tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json",
        executor=executor,
    )

    assert result.task_count == 2
    assert (tmp_path / "runs" / "ok" / "summary.json").exists()
    assert (tmp_path / "runs" / "ok" / "task.json").exists()
    assert (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json").exists()
    assert (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.md").exists()
    assert (tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json").exists()
    matrix = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json").read_text(
            encoding="utf-8"
        )
    )
    retry_overview = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json").read_text(
            encoding="utf-8"
        )
    )
    assert matrix[0]["task_id"] == "ok"
    assert matrix[0]["result"] == "completed"
    assert matrix[0]["retry_result"] == "not_requested"
    assert matrix[0]["retry_budget"] == 0
    assert matrix[0]["retry_attempts_used"] == 0
    assert matrix[1]["failure_status"] == "infra_error"
    assert retry_overview["task_count"] == 2
    assert retry_overview["retry_requested_task_count"] == 0
    assert retry_overview["retry_result_counts"]["not_requested"] == 2


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
        retry_overview_json_path=tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json",
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


def test_normalize_live_run_summary_marks_not_attempted_for_failed_first_attempt() -> None:
    summary = normalize_live_run_summary(
        task={"task_id": "retry", "retry_attempts": 2},
        summary={
            "final_status": "failed",
            "result": "failed",
            "driver_result": {
                "run_id": "retry",
                "agent_id": "agent",
                "attempt": 1,
                "status": "failed",
                "summary": "initial failure before retry",
                "metrics": {"duration_ms": 20, "steps": 1, "commands": 1},
                "recommended_action": "retry",
                "error": "boom",
            },
            "validation": {"run_id": "retry", "passed": False, "checks": []},
        },
    )

    assert summary["retry_result"] == "not_attempted"
    assert summary["retry_budget"] == 2
    assert summary["retry_attempts_used"] == 0
    assert summary["metadata"]["live_run_retry"]["result"] == "not_attempted"
    assert summary["metadata"]["live_run_retry"]["succeeded"] is False


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
        "--repo-root",
        str(repo_root),
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
        "--repo-root",
        str(repo_root),
        "--agent",
        "openhands",
        "--task",
        "summary audit",
        "--run-id",
        "queue-summary-audit",
    ]


def test_normalize_live_run_summary_persists_stable_retry_metadata() -> None:
    summary = normalize_live_run_summary(
        task={"task_id": "retry", "retry_attempts": 2},
        summary={
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
        },
    )

    assert summary["retry_result"] == "recovered"
    assert summary["retry_budget"] == 2
    assert summary["retry_attempts_used"] == 1
    assert summary["metadata"]["live_run_retry"] == {
        "requested": True,
        "budget": 2,
        "attempts_used": 1,
        "final_attempt": 2,
        "result": "recovered",
        "succeeded": True,
        "final_status": "completed",
    }


def test_live_run_benchmark_runner_records_retry_artifacts_for_recovered_attempt(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [{"task_id": "retry", "name": "retry", "retry_attempts": 2}],
            }
        ),
        encoding="utf-8",
    )

    def executor(task: dict[str, object], run_dir: Path) -> dict[str, object]:
        _ = task, run_dir
        return {
            "final_status": "completed",
            "result": "completed",
            "driver_result": {
                "run_id": "retry",
                "agent_id": "agent",
                "attempt": 2,
                "status": "succeeded",
                "summary": "recovered after transient failure",
                "metrics": {"duration_ms": 20, "steps": 2, "commands": 2},
                "recommended_action": "promote",
            },
            "validation": {"run_id": "retry", "passed": True, "checks": []},
        }

    run_live_run_stability_benchmark(
        tasks_path=tasks_path,
        run_root=tmp_path / "runs",
        matrix_json_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json",
        matrix_markdown_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.md",
        retry_overview_json_path=tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json",
        executor=executor,
    )

    summary = json.loads((tmp_path / "runs" / "retry" / "summary.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["retry_result"] == "recovered"
    assert summary["retry_budget"] == 2
    assert summary["retry_attempts_used"] == 1
    assert summary["metadata"]["live_run_retry"]["result"] == "recovered"
    assert matrix[0]["retry_result"] == "recovered"
    assert matrix[0]["retry_budget"] == 2
    assert matrix[0]["retry_attempts_used"] == 1


def test_live_run_benchmark_runner_records_not_needed_retry_artifacts(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [{"task_id": "retry", "name": "retry", "retry_attempts": 2}],
            }
        ),
        encoding="utf-8",
    )

    def executor(task: dict[str, object], run_dir: Path) -> dict[str, object]:
        _ = task, run_dir
        return {
            "final_status": "completed",
            "result": "completed",
            "driver_result": {
                "run_id": "retry",
                "agent_id": "agent",
                "attempt": 1,
                "status": "succeeded",
                "summary": "passed on first attempt",
                "metrics": {"duration_ms": 20, "steps": 1, "commands": 1},
                "recommended_action": "promote",
            },
            "validation": {"run_id": "retry", "passed": True, "checks": []},
        }

    run_live_run_stability_benchmark(
        tasks_path=tasks_path,
        run_root=tmp_path / "runs",
        matrix_json_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json",
        matrix_markdown_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.md",
        retry_overview_json_path=tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json",
        executor=executor,
    )

    summary = json.loads((tmp_path / "runs" / "retry" / "summary.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json").read_text(
            encoding="utf-8"
        )
    )
    retry_overview = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["retry_result"] == "not_needed"
    assert summary["retry_budget"] == 2
    assert summary["retry_attempts_used"] == 0
    assert summary["metadata"]["live_run_retry"] == {
        "requested": True,
        "budget": 2,
        "attempts_used": 0,
        "final_attempt": 1,
        "result": "not_needed",
        "succeeded": True,
        "final_status": "completed",
    }
    assert matrix[0]["retry_result"] == "not_needed"
    assert matrix[0]["retry_budget"] == 2
    assert matrix[0]["retry_attempts_used"] == 0
    assert retry_overview["retry_result_counts"]["not_needed"] == 1
    assert retry_overview["tasks"][0]["retry_result"] == "not_needed"


def test_live_run_benchmark_runner_records_exhausted_retry_artifacts(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [{"task_id": "retry", "name": "retry", "retry_attempts": 1}],
            }
        ),
        encoding="utf-8",
    )

    def executor(task: dict[str, object], run_dir: Path) -> dict[str, object]:
        _ = task, run_dir
        return {
            "final_status": "failed",
            "result": "failed",
            "driver_result": {
                "run_id": "retry",
                "agent_id": "agent",
                "attempt": 2,
                "status": "failed",
                "summary": "retry exhausted",
                "metrics": {"duration_ms": 20, "steps": 2, "commands": 2},
                "recommended_action": "human_review",
                "error": "still broken",
            },
            "validation": {"run_id": "retry", "passed": False, "checks": []},
        }

    run_live_run_stability_benchmark(
        tasks_path=tasks_path,
        run_root=tmp_path / "runs",
        matrix_json_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json",
        matrix_markdown_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.md",
        retry_overview_json_path=tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json",
        executor=executor,
    )

    summary = json.loads((tmp_path / "runs" / "retry" / "summary.json").read_text(encoding="utf-8"))
    matrix = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json").read_text(
            encoding="utf-8"
        )
    )
    retry_overview = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["retry_result"] == "exhausted"
    assert summary["retry_budget"] == 1
    assert summary["retry_attempts_used"] == 1
    assert matrix[0]["retry_result"] == "exhausted"
    assert matrix[0]["retry_budget"] == 1
    assert matrix[0]["retry_attempts_used"] == 1
    assert retry_overview["retry_result_counts"]["exhausted"] == 1
    assert retry_overview["tasks"][0]["retry_result"] == "exhausted"


def test_retry_overview_json_has_stable_schema(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [
                    {"task_id": "one", "name": "one", "retry_attempts": 0},
                    {"task_id": "two", "name": "two", "retry_attempts": 1},
                ],
            }
        ),
        encoding="utf-8",
    )

    def executor(task: dict[str, object], run_dir: Path) -> dict[str, object]:
        _ = run_dir
        task_id = str(task["task_id"])
        if task_id == "one":
            return {
                "final_status": "completed",
                "result": "completed",
                "driver_result": {
                    "run_id": task_id,
                    "agent_id": "agent",
                    "attempt": 1,
                    "status": "succeeded",
                    "summary": "clean pass",
                    "metrics": {"duration_ms": 5, "steps": 1, "commands": 1},
                    "recommended_action": "promote",
                },
                "validation": {"run_id": task_id, "passed": True, "checks": []},
            }
        return {
            "final_status": "failed",
            "result": "failed",
            "driver_result": {
                "run_id": task_id,
                "agent_id": "agent",
                "attempt": 2,
                "status": "failed",
                "summary": "retry exhausted",
                "metrics": {"duration_ms": 5, "steps": 2, "commands": 2},
                "recommended_action": "human_review",
                "error": "still broken",
            },
            "validation": {"run_id": task_id, "passed": False, "checks": []},
        }

    run_live_run_stability_benchmark(
        tasks_path=tasks_path,
        run_root=tmp_path / "runs",
        matrix_json_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json",
        matrix_markdown_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.md",
        retry_overview_json_path=tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json",
        executor=executor,
    )

    retry_overview = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json").read_text(
            encoding="utf-8"
        )
    )

    assert set(retry_overview) == {
        "task_count",
        "retry_requested_task_count",
        "retried_task_count",
        "retry_result_counts",
        "tasks",
    }
    assert set(retry_overview["retry_result_counts"]) == set(LIVE_RUN_RETRY_RESULT_VALUES)
    assert retry_overview["retry_result_counts"]["not_requested"] == 1
    assert retry_overview["retry_result_counts"]["exhausted"] == 1
    assert all(
        set(item) == {
            "task_id",
            "task_name",
            "result",
            "failure_status",
            "retry_result",
            "retry_budget",
            "retry_attempts_used",
        }
        for item in retry_overview["tasks"]
    )


def test_retry_overview_json_aggregates_match_regression_matrix_rows(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [
                    {"task_id": "not-requested", "name": "not requested", "retry_attempts": 0},
                    {"task_id": "not-needed", "name": "not needed", "retry_attempts": 2},
                    {"task_id": "recovered", "name": "recovered", "retry_attempts": 2},
                    {"task_id": "exhausted", "name": "exhausted", "retry_attempts": 1},
                    {"task_id": "not-attempted", "name": "not attempted", "retry_attempts": 1},
                ],
            }
        ),
        encoding="utf-8",
    )

    def executor(task: dict[str, object], run_dir: Path) -> dict[str, object]:
        _ = run_dir
        task_id = str(task["task_id"])
        if task_id == "not-requested":
            return {
                "final_status": "completed",
                "result": "completed",
                "driver_result": {
                    "run_id": task_id,
                    "agent_id": "agent",
                    "attempt": 1,
                    "status": "succeeded",
                    "summary": "clean pass without retry budget",
                    "metrics": {"duration_ms": 5, "steps": 1, "commands": 1},
                    "recommended_action": "promote",
                },
                "validation": {"run_id": task_id, "passed": True, "checks": []},
            }
        if task_id == "not-needed":
            return {
                "final_status": "completed",
                "result": "completed",
                "driver_result": {
                    "run_id": task_id,
                    "agent_id": "agent",
                    "attempt": 1,
                    "status": "succeeded",
                    "summary": "clean pass with retry budget unused",
                    "metrics": {"duration_ms": 5, "steps": 1, "commands": 1},
                    "recommended_action": "promote",
                },
                "validation": {"run_id": task_id, "passed": True, "checks": []},
            }
        if task_id == "recovered":
            return {
                "final_status": "completed",
                "result": "completed",
                "driver_result": {
                    "run_id": task_id,
                    "agent_id": "agent",
                    "attempt": 2,
                    "status": "succeeded",
                    "summary": "recovered after retry",
                    "metrics": {"duration_ms": 5, "steps": 2, "commands": 2},
                    "recommended_action": "promote",
                },
                "validation": {"run_id": task_id, "passed": True, "checks": []},
            }
        if task_id == "exhausted":
            return {
                "final_status": "failed",
                "result": "failed",
                "driver_result": {
                    "run_id": task_id,
                    "agent_id": "agent",
                    "attempt": 2,
                    "status": "failed",
                    "summary": "retry exhausted",
                    "metrics": {"duration_ms": 5, "steps": 2, "commands": 2},
                    "recommended_action": "human_review",
                    "error": "still broken",
                },
                "validation": {"run_id": task_id, "passed": False, "checks": []},
            }
        return {"final_status": "failed"}

    run_live_run_stability_benchmark(
        tasks_path=tasks_path,
        run_root=tmp_path / "runs",
        matrix_json_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json",
        matrix_markdown_path=tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.md",
        retry_overview_json_path=tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json",
        executor=executor,
    )

    matrix = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "regression-matrix.json").read_text(
            encoding="utf-8"
        )
    )
    retry_overview = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json").read_text(
            encoding="utf-8"
        )
    )

    expected_retry_result_counts = {
        retry_result: sum(1 for row in matrix if row["retry_result"] == retry_result)
        for retry_result in LIVE_RUN_RETRY_RESULT_VALUES
    }
    expected_retry_requested_task_count = sum(
        1 for row in matrix if isinstance(row["retry_budget"], int) and row["retry_budget"] > 0
    )
    expected_retried_task_count = sum(
        1
        for row in matrix
        if isinstance(row["retry_attempts_used"], int) and row["retry_attempts_used"] > 0
    )

    assert retry_overview["task_count"] == len(matrix)
    assert retry_overview["retry_requested_task_count"] == expected_retry_requested_task_count
    assert retry_overview["retried_task_count"] == expected_retried_task_count
    assert retry_overview["retry_result_counts"] == expected_retry_result_counts
    assert retry_overview["retry_result_counts"] == {
        "not_requested": 1,
        "not_needed": 1,
        "not_attempted": 1,
        "recovered": 1,
        "exhausted": 1,
    }


def test_retry_overview_handles_missing_summary_rows_without_forcing_retry_result(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [{"task_id": "missing", "name": "missing", "retry_attempts": 2}],
            }
        ),
        encoding="utf-8",
    )

    rows = generate_live_run_regression_matrix(tasks_path=tasks_path, run_roots=[tmp_path / "runs"])
    overview = build_live_run_retry_overview(rows)

    assert rows[0].result == "missing"
    assert rows[0].retry_result is None
    assert rows[0].retry_budget == 2
    assert rows[0].retry_attempts_used is None
    assert overview["task_count"] == 1
    assert overview["retry_requested_task_count"] == 1
    assert overview["retried_task_count"] == 0
    assert all(value == 0 for value in overview["retry_result_counts"].values())
    assert overview["tasks"] == [
        {
            "task_id": "missing",
            "task_name": "missing",
            "result": "missing",
            "failure_status": None,
            "retry_result": None,
            "retry_budget": 2,
            "retry_attempts_used": None,
        }
    ]


def test_retry_overview_marks_partial_summary_as_not_attempted_when_retry_budget_exists(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [{"task_id": "partial", "name": "partial", "retry_attempts": 1}],
            }
        ),
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
        retry_overview_json_path=tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json",
        executor=executor,
    )

    retry_overview = json.loads(
        (tmp_path / "artifacts" / "live-run-stability" / "retry-overview.json").read_text(
            encoding="utf-8"
        )
    )

    assert retry_overview["task_count"] == 1
    assert retry_overview["retry_requested_task_count"] == 1
    assert retry_overview["retried_task_count"] == 0
    assert retry_overview["retry_result_counts"]["not_attempted"] == 1
    assert retry_overview["tasks"] == [
        {
            "task_id": "partial",
            "task_name": "partial",
            "result": "failed",
            "failure_status": None,
            "retry_result": "not_attempted",
            "retry_budget": 1,
            "retry_attempts_used": 0,
        }
    ]


def test_matrix_derives_retry_result_from_attempt_count(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {"suite_name": "live-run-stability", "tasks": [{"task_id": "retry", "name": "retry", "retry_attempts": 2}]}
        ),
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

    assert rows[0].retry_result == "recovered"
    assert rows[0].retry_budget == 2
    assert rows[0].retry_attempts_used == 1


def test_matrix_normalizes_legacy_retried_result_to_stable_enum(tmp_path: Path) -> None:
    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {"suite_name": "live-run-stability", "tasks": [{"task_id": "retry", "name": "retry", "retry_attempts": 1}]}
        ),
        encoding="utf-8",
    )

    run_root = tmp_path / "runs"
    (run_root / "retry").mkdir(parents=True)
    (run_root / "retry" / "summary.json").write_text(
        json.dumps(
            {
                "final_status": "completed",
                "result": "completed",
                "retry_result": "retried",
                "driver_result": {
                    "run_id": "retry",
                    "agent_id": "agent",
                    "attempt": 2,
                    "status": "succeeded",
                    "summary": "legacy retried payload",
                    "metrics": {"duration_ms": 20, "steps": 2, "commands": 2},
                    "recommended_action": "promote",
                },
                "validation": {"run_id": "retry", "passed": True, "checks": []},
            }
        ),
        encoding="utf-8",
    )

    rows = generate_live_run_regression_matrix(tasks_path=tasks_path, run_roots=[run_root])

    assert rows[0].retry_result == "recovered"
    assert rows[0].retry_budget == 1
    assert rows[0].retry_attempts_used == 1


def test_live_run_benchmark_runner_uses_real_retry_loop_with_flaky_adapter(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "flaky_target.py").write_text("VALUE = 'seed'\n", encoding="utf-8")

    adapter = repo_root / "drivers" / "flaky_adapter.py"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text(
        """#!/usr/bin/env python3
import json
import os
from pathlib import Path

workspace = Path(os.environ["AEP_WORKSPACE"])
result_path = Path(os.environ["AEP_RESULT_PATH"])
attempt = int(os.environ["AEP_ATTEMPT"])
target = workspace / "src" / "flaky_target.py"

if attempt == 1:
    target.write_text("raise RuntimeError('retry me')\\n", encoding="utf-8")
    summary = "seeded transient failure"
else:
    target.write_text("VALUE = 'fixed'\\n", encoding="utf-8")
    summary = "recovered on retry"

payload = {
    "protocol_version": "aep/v0",
    "run_id": "run-live-benchmark-flaky",
    "agent_id": "flaky",
    "attempt": attempt,
    "status": "succeeded",
    "summary": summary,
    "changed_paths": ["src/flaky_target.py"],
    "output_artifacts": [],
    "metrics": {"duration_ms": 0, "steps": attempt, "commands": attempt, "prompt_tokens": None, "completion_tokens": None},
    "recommended_action": "promote",
    "error": None,
}
result_path.write_text(json.dumps(payload), encoding="utf-8")
""",
        encoding="utf-8",
    )
    adapter.chmod(0o755)
    _write_manifest(repo_root, "flaky", "drivers/flaky_adapter.py")

    benchmark_runtime = tmp_path / "benchmark-runtime"
    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runner-runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [{"task_id": "flaky-retry", "name": "flaky retry", "retry_attempts": 1}],
            }
        ),
        encoding="utf-8",
    )

    def executor(task: dict[str, object], run_dir: Path) -> dict[str, object]:
        _ = task, run_dir
        summary = runner.run_job(
            JobSpec(
                run_id="run-live-benchmark-flaky",
                agent_id="flaky",
                task="fix flaky target",
                validators=[
                    ValidatorSpec(
                        id="worker.test_command",
                        kind="command",
                        command=f"{sys.executable} src/flaky_target.py",
                    )
                ],
                fallback=[FallbackStep(action="retry", max_attempts=1)],
            )
        )
        return summary.model_dump(mode="json")

    run_live_run_stability_benchmark(
        tasks_path=tasks_path,
        run_root=benchmark_runtime / "runs",
        matrix_json_path=benchmark_runtime / "artifacts" / "live-run-stability" / "regression-matrix.json",
        matrix_markdown_path=benchmark_runtime / "artifacts" / "live-run-stability" / "regression-matrix.md",
        retry_overview_json_path=benchmark_runtime / "artifacts" / "live-run-stability" / "retry-overview.json",
        executor=executor,
    )

    summary = json.loads((benchmark_runtime / "runs" / "flaky-retry" / "summary.json").read_text(encoding="utf-8"))
    retry_overview = json.loads(
        (
            benchmark_runtime / "artifacts" / "live-run-stability" / "retry-overview.json"
        ).read_text(encoding="utf-8")
    )

    assert summary["retry_result"] == "recovered"
    assert summary["retry_attempts_used"] == 1
    assert summary["driver_result"]["attempt"] == 2
    assert retry_overview["retry_result_counts"]["recovered"] == 1


def test_agent_run_script_supports_repo_root_for_cli_retry_integration(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "flaky_target.py").write_text("VALUE = 'seed'\n", encoding="utf-8")

    adapter = repo_root / "drivers" / "flaky_cli_adapter.py"
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text(
        """#!/usr/bin/env python3
import json
import os
from pathlib import Path

workspace = Path(os.environ["AEP_WORKSPACE"])
result_path = Path(os.environ["AEP_RESULT_PATH"])
attempt = int(os.environ["AEP_ATTEMPT"])
target = workspace / "src" / "flaky_target.py"

if attempt == 1:
    target.write_text("raise RuntimeError('retry me')\\n", encoding="utf-8")
    summary = "seeded transient failure"
else:
    target.write_text("VALUE = 'fixed'\\n", encoding="utf-8")
    summary = "recovered on retry"

payload = {
    "protocol_version": "aep/v0",
    "run_id": "cli-flaky",
    "agent_id": "flaky",
    "attempt": attempt,
    "status": "succeeded",
    "summary": summary,
    "changed_paths": ["src/flaky_target.py"],
    "output_artifacts": [],
    "metrics": {"duration_ms": 0, "steps": attempt, "commands": attempt, "prompt_tokens": None, "completion_tokens": None},
    "recommended_action": "promote",
    "error": None,
}
result_path.write_text(json.dumps(payload), encoding="utf-8")
""",
        encoding="utf-8",
    )
    adapter.chmod(0o755)
    _write_manifest(repo_root, "flaky", "drivers/flaky_cli_adapter.py")

    workspace_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    src_path = str((workspace_root / "src").resolve())
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{src_path}:{pythonpath}" if pythonpath else src_path

    completed = subprocess.run(
        [
            sys.executable,
            str(workspace_root / "scripts" / "agent_run.py"),
            "--repo-root",
            str(repo_root),
            "--agent",
            "flaky",
            "--task",
            "fix flaky target",
            "--run-id",
            "cli-flaky",
            "--retry",
            "1",
            "--validator-cmd",
            f"{sys.executable} src/flaky_target.py",
        ],
        cwd=workspace_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    persisted_summary = json.loads(
        (repo_root / ".masfactory_runtime" / "runs" / "cli-flaky" / "summary.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["final_status"] == "ready_for_promotion"
    assert summary["driver_result"]["attempt"] == 2
    assert summary["driver_result"]["summary"] == "recovered on retry"
    assert persisted_summary["driver_result"]["attempt"] == 2
