from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from autoresearch.executions.runner import AgentExecutionRunner


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _copy_phase2_assets(repo_root: Path) -> None:
    workspace_root = _workspace_root()
    relative_paths = [
        "benchmarks/live-run-stability/phase-2/tasks.json",
        "configs/agents/phase2-stall-probe.yaml",
        "configs/agents/phase2-timeout-probe.yaml",
        "configs/agents/phase2-business-assertion-probe.yaml",
        "drivers/live_run_phase2_stall_probe.py",
        "drivers/live_run_phase2_timeout_probe.py",
        "drivers/live_run_phase2_business_assertion_probe.py",
    ]
    for relative_path in relative_paths:
        source = workspace_root / relative_path
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "src").mkdir(parents=True, exist_ok=True)


def _load_script_module():
    script_path = (
        Path(__file__).resolve().parents[1] / "scripts" / "run_live_run_stability_phase2_benchmark.py"
    )
    spec = importlib.util.spec_from_file_location("live_run_phase2_benchmark_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_smoke_prints_phase2_output_paths(tmp_path: Path, monkeypatch, capsys) -> None:
    repo_root = tmp_path / "repo"
    benchmark_root = tmp_path / "phase2-output"
    tasks_path = repo_root / "benchmarks" / "live-run-stability" / "phase-2" / "tasks.json"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(json.dumps({"suite_name": "live-run-stability-phase-2", "tasks": []}), encoding="utf-8")

    module = _load_script_module()
    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: argparse.Namespace(
            repo_root=str(repo_root),
            tasks_path=str(tasks_path),
            benchmark_root=str(benchmark_root),
        ),
    )
    monkeypatch.setattr(
        module,
        "run_live_run_stability_phase2_benchmark",
        lambda **kwargs: SimpleNamespace(
            task_count=0,
            run_root=Path(kwargs["benchmark_root"]) / "runs",
            matrix_json_path=Path(kwargs["benchmark_root"]) / "regression-matrix.json",
            matrix_markdown_path=Path(kwargs["benchmark_root"]) / "regression-matrix.md",
            retry_overview_json_path=Path(kwargs["benchmark_root"]) / "retry-overview.json",
            gate_report_json_path=Path(kwargs["benchmark_root"]) / "regression-gate.json",
            gate_passed=True,
        ),
    )

    exit_code = module.main()
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["tasks_path"] == str(tasks_path)
    assert output["benchmark_root"] == str(benchmark_root)
    assert output["run_root"] == str(benchmark_root / "runs")
    assert output["retry_overview_json_path"] == str(benchmark_root / "retry-overview.json")
    assert output["gate_report_json_path"] == str(benchmark_root / "regression-gate.json")
    assert output["gate_passed"] is True


def test_script_runs_phase2_benchmark_and_writes_outputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_phase2_assets(repo_root)
    benchmark_root = tmp_path / "phase2-output"

    module = _load_script_module()
    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: argparse.Namespace(
            repo_root=str(repo_root),
            tasks_path=None,
            benchmark_root=str(benchmark_root),
        ),
    )
    monkeypatch.setattr(AgentExecutionRunner, "_stall_progress_timeout_sec", staticmethod(lambda _: 1))

    exit_code = module.main()
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["task_count"] == 3
    assert Path(output["run_root"]).exists()
    assert Path(output["matrix_json_path"]).exists()
    assert Path(output["matrix_markdown_path"]).exists()
    assert Path(output["retry_overview_json_path"]).exists()
    assert Path(output["gate_report_json_path"]).exists()
    assert output["gate_passed"] is True
    assert (benchmark_root / "runs" / "fail-timeout-probe" / "summary.json").exists()
    assert (benchmark_root / "runs" / "fail-stall-no-progress" / "summary.json").exists()
    assert (benchmark_root / "runs" / "fail-business-assertion-mismatch" / "summary.json").exists()


def test_script_returns_nonzero_when_phase2_gate_fails(tmp_path: Path, monkeypatch, capsys) -> None:
    repo_root = tmp_path / "repo"
    benchmark_root = tmp_path / "phase2-output"
    tasks_path = repo_root / "benchmarks" / "live-run-stability" / "phase-2" / "tasks.json"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(json.dumps({"suite_name": "live-run-stability-phase-2", "tasks": []}), encoding="utf-8")

    module = _load_script_module()
    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: argparse.Namespace(
            repo_root=str(repo_root),
            tasks_path=str(tasks_path),
            benchmark_root=str(benchmark_root),
        ),
    )
    monkeypatch.setattr(
        module,
        "run_live_run_stability_phase2_benchmark",
        lambda **kwargs: SimpleNamespace(
            task_count=0,
            run_root=Path(kwargs["benchmark_root"]) / "runs",
            matrix_json_path=Path(kwargs["benchmark_root"]) / "regression-matrix.json",
            matrix_markdown_path=Path(kwargs["benchmark_root"]) / "regression-matrix.md",
            retry_overview_json_path=Path(kwargs["benchmark_root"]) / "retry-overview.json",
            gate_report_json_path=Path(kwargs["benchmark_root"]) / "regression-gate.json",
            gate_passed=False,
        ),
    )

    exit_code = module.main()
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["gate_passed"] is False
