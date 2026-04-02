from __future__ import annotations

import json
import shutil
from pathlib import Path

from autoresearch.benchmarks.live_run_stability_phase2 import (
    _ensure_phase2_stall_heartbeat_file,
    _ensure_phase2_stall_status_file,
    _phase2_artifacts_produced,
    _phase2_required_marker_validator_command,
    build_live_run_stability_phase2_paths,
    run_live_run_stability_phase2_benchmark,
)
from autoresearch.executions.runner import AgentExecutionRunner


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _copy_phase2_assets(repo_root: Path) -> None:
    workspace_root = _workspace_root()
    relative_paths = [
        "benchmarks/live-run-stability/phase-2/tasks.json",
        "configs/agents/phase2-stall-probe.yaml",
        "configs/agents/phase2-business-assertion-probe.yaml",
        "drivers/live_run_phase2_stall_probe.py",
        "drivers/live_run_phase2_business_assertion_probe.py",
    ]
    for relative_path in relative_paths:
        source = workspace_root / relative_path
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "src").mkdir(parents=True, exist_ok=True)


def _write_tasks_subset(repo_root: Path, task_id: str) -> Path:
    tasks_path = repo_root / "benchmarks" / "live-run-stability" / "phase-2" / "tasks.json"
    payload = json.loads(tasks_path.read_text(encoding="utf-8"))
    payload["tasks"] = [task for task in payload["tasks"] if task["task_id"] == task_id]
    subset_path = repo_root / "benchmarks" / "live-run-stability" / "phase-2" / f"{task_id}.json"
    subset_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return subset_path


def _assert_phase2_artifact_inventory(
    *,
    summary: dict[str, object],
    run_dir: Path,
    expected_paths: list[Path],
) -> None:
    expected_inventory = [str(path) for path in expected_paths]
    assert summary["artifacts_produced"] == expected_inventory
    assert all(path.exists() for path in expected_paths)
    assert all(str(path).startswith(str(run_dir)) for path in expected_paths)


def test_phase2_required_marker_validator_command_targets_manifest_file() -> None:
    command = _phase2_required_marker_validator_command(
        target_file="src/phase2_business_probe.py",
        required_marker="PHASE2_REQUIRED_MARKER",
    )

    assert "src/phase2_business_probe.py" in command
    assert "PHASE2_REQUIRED_MARKER" in command


def test_phase2_artifact_inventory_stays_within_run_dir(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "fail-stall-no-progress"
    run_dir.mkdir(parents=True, exist_ok=True)

    local_report = run_dir / "artifacts" / "local-report.json"
    local_report.parent.mkdir(parents=True, exist_ok=True)
    local_report.write_text(json.dumps({"ok": True}), encoding="utf-8")

    foreign_runtime = tmp_path / "runner-runtime" / "fail-stall-no-progress" / "driver_result.json"
    foreign_runtime.parent.mkdir(parents=True, exist_ok=True)
    foreign_runtime.write_text("{}", encoding="utf-8")

    inventory = _phase2_artifacts_produced(
        run_dir=run_dir,
        extra_paths=[
            foreign_runtime,
            Path("artifacts/local-report.json"),
            local_report,
            run_dir / "missing.json",
        ],
    )

    assert inventory == [
        str(run_dir / "summary.json"),
        str(run_dir / "artifacts" / "local-report.json"),
    ]
    assert all(path.startswith(str(run_dir)) for path in inventory)
    assert all("runner-runtime" not in path for path in inventory)


def test_phase2_stall_status_file_is_synthesized_when_runtime_copy_is_missing(tmp_path: Path) -> None:
    destination = tmp_path / "runs" / "fail-stall-no-progress" / "status.json"

    result = _ensure_phase2_stall_status_file(
        source=tmp_path / "runner-runtime" / "missing-status.json",
        destination=destination,
        summary={
            "driver_result": {"status": "stalled_no_progress"},
            "final_status": "failed",
        },
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert result == destination
    assert payload == {
        "probe": "phase2-stall-no-progress",
        "status": "stalled_no_progress",
        "final_status": "failed",
    }


def test_phase2_stall_heartbeat_file_is_synthesized_when_runtime_copy_is_missing(tmp_path: Path) -> None:
    destination = tmp_path / "runs" / "fail-stall-no-progress" / "heartbeat.json"

    result = _ensure_phase2_stall_heartbeat_file(
        source=tmp_path / "runner-runtime" / "missing-heartbeat.json",
        destination=destination,
        summary={
            "failure_status": "stalled_no_progress",
        },
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert result == destination
    assert payload == {
        "probe": "phase2-stall-no-progress",
        "heartbeat": "synthesized",
        "failure_status": "stalled_no_progress",
    }


def test_phase2_stall_probe_produces_closed_failure_outputs(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _copy_phase2_assets(repo_root)
    tasks_path = _write_tasks_subset(repo_root, "fail-stall-no-progress")
    benchmark_root = tmp_path / "phase2-benchmark"
    monkeypatch.setattr(AgentExecutionRunner, "_stall_progress_timeout_sec", staticmethod(lambda _: 1))

    result = run_live_run_stability_phase2_benchmark(
        repo_root=repo_root,
        tasks_path=tasks_path,
        benchmark_root=benchmark_root,
    )

    paths = build_live_run_stability_phase2_paths(
        repo_root=repo_root,
        tasks_path=tasks_path,
        benchmark_root=benchmark_root,
    )
    run_dir = paths.run_root / "fail-stall-no-progress"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    overview = json.loads(paths.retry_overview_json_path.read_text(encoding="utf-8"))
    matrix = json.loads(paths.matrix_json_path.read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in (run_dir / "events.ndjson").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert result.task_count == 1
    assert (run_dir / "status.json").exists()
    assert (run_dir / "heartbeat.json").exists()
    _assert_phase2_artifact_inventory(
        summary=summary,
        run_dir=run_dir,
        expected_paths=[
            run_dir / "summary.json",
            run_dir / "events.ndjson",
            run_dir / "status.json",
            run_dir / "heartbeat.json",
        ],
    )
    assert summary["final_status"] == "failed"
    assert summary["driver_result"]["status"] == "stalled_no_progress"
    assert summary["failure_status"] == "stalled_no_progress"
    assert summary["failure_layer"] == "infra"
    assert summary["failure_stage"] == "stalled_no_progress"
    assert summary["retry_result"] == "not_attempted"
    assert any(
        item.get("type") == "fallback_skipped" and item.get("reason") == "stalled_no_progress"
        for item in events
    )
    assert overview["retry_result_counts"]["not_attempted"] == 1
    assert matrix == [
        {
            "duration_sec": None,
            "failure_layer": "infra",
            "failure_stage": "stalled_no_progress",
            "failure_status": "stalled_no_progress",
            "lane": "phase-2",
            "model_provider": None,
            "notes": None,
            "result": "failed",
            "retry_attempts_used": 0,
            "retry_budget": 1,
            "retry_result": "not_attempted",
            "task_id": "fail-stall-no-progress",
            "task_name": "stall failure probe: terminate on no-progress without promoting the run",
        }
    ]


def test_phase2_business_assertion_probe_produces_reported_validation_failure(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _copy_phase2_assets(repo_root)
    tasks_path = _write_tasks_subset(repo_root, "fail-business-assertion-mismatch")
    benchmark_root = tmp_path / "phase2-benchmark"

    result = run_live_run_stability_phase2_benchmark(
        repo_root=repo_root,
        tasks_path=tasks_path,
        benchmark_root=benchmark_root,
    )

    paths = build_live_run_stability_phase2_paths(
        repo_root=repo_root,
        tasks_path=tasks_path,
        benchmark_root=benchmark_root,
    )
    run_dir = paths.run_root / "fail-business-assertion-mismatch"
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    driver_result = json.loads((run_dir / "driver_result.json").read_text(encoding="utf-8"))
    overview = json.loads(paths.retry_overview_json_path.read_text(encoding="utf-8"))
    matrix = json.loads(paths.matrix_json_path.read_text(encoding="utf-8"))
    report_json = json.loads((run_dir / "artifacts" / "business_assertion_report.json").read_text(encoding="utf-8"))
    report_md = (run_dir / "artifacts" / "business_assertion_report.md").read_text(encoding="utf-8")
    promotion_patch = (run_dir / "artifacts" / "promotion.patch").read_text(encoding="utf-8")

    assert result.task_count == 1
    assert (run_dir / "events.ndjson").exists()
    assert (run_dir / "driver_result.json").exists()
    assert (run_dir / "artifacts" / "promotion.patch").exists()
    _assert_phase2_artifact_inventory(
        summary=summary,
        run_dir=run_dir,
        expected_paths=[
            run_dir / "summary.json",
            run_dir / "events.ndjson",
            run_dir / "driver_result.json",
            run_dir / "artifacts" / "promotion.patch",
            run_dir / "artifacts" / "business_assertion_report.json",
            run_dir / "artifacts" / "business_assertion_report.md",
        ],
    )
    assert summary["final_status"] == "human_review"
    assert summary["driver_result"]["status"] == "succeeded"
    assert summary["driver_result"]["changed_paths"] == ["src/phase2_business_probe.py"]
    assert driver_result["status"] == "succeeded"
    assert driver_result["changed_paths"] == ["src/phase2_business_probe.py"]
    assert summary["business_assertion_status"] == "failed"
    assert summary["failure_status"] == "assertion_failed"
    assert summary["failure_layer"] == "business_validation"
    assert summary["failure_stage"] == "phase2.business_assertion.required_marker"
    assert summary["retry_result"] == "not_requested"
    assert overview["retry_result_counts"]["not_requested"] == 1
    assert report_json["failure_stage"] == "phase2.business_assertion.required_marker"
    assert report_json["failed_checks"][0]["id"] == "phase2.business_assertion.required_marker"
    assert "missing required marker" in report_json["failed_checks"][0]["detail"]
    assert "phase2.business_assertion.required_marker" in report_md
    assert "src/phase2_business_probe.py" in promotion_patch
    assert matrix == [
        {
            "duration_sec": None,
            "failure_layer": "business_validation",
            "failure_stage": "phase2.business_assertion.required_marker",
            "failure_status": "assertion_failed",
            "lane": "phase-2",
            "model_provider": None,
            "notes": None,
            "result": "human_review",
            "retry_attempts_used": 0,
            "retry_budget": 0,
            "retry_result": "not_requested",
            "task_id": "fail-business-assertion-mismatch",
            "task_name": "business validation failure probe: execution succeeds but assertion fails",
        }
    ]


def test_phase2_full_suite_artifact_inventory_stays_within_run_dirs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _copy_phase2_assets(repo_root)
    benchmark_root = tmp_path / "phase2-benchmark"
    monkeypatch.setattr(AgentExecutionRunner, "_stall_progress_timeout_sec", staticmethod(lambda _: 1))

    result = run_live_run_stability_phase2_benchmark(
        repo_root=repo_root,
        benchmark_root=benchmark_root,
    )

    paths = build_live_run_stability_phase2_paths(
        repo_root=repo_root,
        benchmark_root=benchmark_root,
    )
    overview = json.loads(paths.retry_overview_json_path.read_text(encoding="utf-8"))

    assert result.task_count == 2
    assert overview["task_count"] == 2

    for task_id in ("fail-stall-no-progress", "fail-business-assertion-mismatch"):
        run_dir = paths.run_root / task_id
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        artifact_paths = [Path(path) for path in summary["artifacts_produced"]]

        assert artifact_paths
        assert all(path.exists() for path in artifact_paths)
        assert all(str(path).startswith(str(run_dir)) for path in artifact_paths)
        assert all("runner-runtime" not in str(path) for path in artifact_paths)


def test_phase2_manifest_expected_artifacts_are_present_in_runtime_inventory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _copy_phase2_assets(repo_root)
    benchmark_root = tmp_path / "phase2-benchmark"
    monkeypatch.setattr(AgentExecutionRunner, "_stall_progress_timeout_sec", staticmethod(lambda _: 1))

    run_live_run_stability_phase2_benchmark(
        repo_root=repo_root,
        benchmark_root=benchmark_root,
    )

    tasks = json.loads(
        (repo_root / "benchmarks" / "live-run-stability" / "phase-2" / "tasks.json").read_text(
            encoding="utf-8"
        )
    )["tasks"]
    paths = build_live_run_stability_phase2_paths(
        repo_root=repo_root,
        benchmark_root=benchmark_root,
    )

    for task in tasks:
        run_dir = paths.run_root / str(task["task_id"])
        summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
        artifact_inventory = set(summary["artifacts_produced"])
        expected_paths = [str(run_dir / artifact) for artifact in task["expected_artifacts"]]

        assert set(expected_paths).issubset(artifact_inventory)
        assert all(Path(path).exists() for path in expected_paths)


def test_phase2_retry_overview_aggregates_match_regression_matrix_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _copy_phase2_assets(repo_root)
    benchmark_root = tmp_path / "phase2-benchmark"
    monkeypatch.setattr(AgentExecutionRunner, "_stall_progress_timeout_sec", staticmethod(lambda _: 1))

    run_live_run_stability_phase2_benchmark(
        repo_root=repo_root,
        benchmark_root=benchmark_root,
    )

    paths = build_live_run_stability_phase2_paths(
        repo_root=repo_root,
        benchmark_root=benchmark_root,
    )
    matrix = json.loads(paths.matrix_json_path.read_text(encoding="utf-8"))
    overview = json.loads(paths.retry_overview_json_path.read_text(encoding="utf-8"))

    retry_requested_task_count = sum(1 for row in matrix if int(row["retry_budget"] or 0) > 0)
    retried_task_count = sum(1 for row in matrix if int(row["retry_attempts_used"] or 0) > 0)
    retry_result_counts: dict[str, int] = {}
    for row in matrix:
        retry_result = str(row["retry_result"])
        retry_result_counts[retry_result] = retry_result_counts.get(retry_result, 0) + 1
    expected_retry_result_counts = {
        key: retry_result_counts.get(key, 0)
        for key in overview["retry_result_counts"]
    }

    assert overview["task_count"] == len(matrix)
    assert overview["retry_requested_task_count"] == retry_requested_task_count
    assert overview["retried_task_count"] == retried_task_count
    assert overview["retry_result_counts"] == expected_retry_result_counts


def test_phase2_benchmark_outputs_do_not_leak_runner_runtime_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _copy_phase2_assets(repo_root)
    benchmark_root = tmp_path / "phase2-benchmark"
    monkeypatch.setattr(AgentExecutionRunner, "_stall_progress_timeout_sec", staticmethod(lambda _: 1))

    run_live_run_stability_phase2_benchmark(
        repo_root=repo_root,
        benchmark_root=benchmark_root,
    )

    paths = build_live_run_stability_phase2_paths(
        repo_root=repo_root,
        benchmark_root=benchmark_root,
    )
    matrix_json_text = paths.matrix_json_path.read_text(encoding="utf-8")
    matrix_md_text = paths.matrix_markdown_path.read_text(encoding="utf-8")
    overview_json_text = paths.retry_overview_json_path.read_text(encoding="utf-8")
    matrix = json.loads(matrix_json_text)
    overview = json.loads(overview_json_text)

    assert "runner-runtime" not in matrix_json_text
    assert "runner-runtime" not in matrix_md_text
    assert "runner-runtime" not in overview_json_text

    matrix_task_ids = {row["task_id"] for row in matrix}
    overview_task_ids = {row["task_id"] for row in overview["tasks"]}
    run_dir_task_ids = {
        run_dir.name
        for run_dir in paths.run_root.iterdir()
        if run_dir.is_dir() and (run_dir / "summary.json").exists()
    }

    assert matrix_task_ids == overview_task_ids
    assert matrix_task_ids == run_dir_task_ids
