from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


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
        ),
    )

    exit_code = module.main()
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["tasks_path"] == str(tasks_path)
    assert output["benchmark_root"] == str(benchmark_root)
    assert output["run_root"] == str(benchmark_root / "runs")
    assert output["retry_overview_json_path"] == str(benchmark_root / "retry-overview.json")
