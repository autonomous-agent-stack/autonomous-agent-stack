from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def _load_script_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_live_run_stability_benchmark.py"
    spec = importlib.util.spec_from_file_location("live_run_benchmark_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_script_smoke_prints_retry_overview_json_path(tmp_path: Path, monkeypatch, capsys) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "benchmarks" / "live-run-stability").mkdir(parents=True, exist_ok=True)
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / ".venv" / "bin").mkdir(parents=True, exist_ok=True)
    (repo_root / "benchmarks" / "live-run-stability" / "tasks.json").write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability",
                "tasks": [{"task_id": "smoke", "name": "smoke", "prompt": "smoke prompt", "retry_attempts": 1}],
            }
        ),
        encoding="utf-8",
    )

    module = _load_script_module()
    monkeypatch.setattr(module, "parse_args", lambda: argparse.Namespace(repo_root=str(repo_root)))

    fake_summary = {
        "final_status": "completed",
        "result": "completed",
        "driver_result": {
            "run_id": "smoke",
            "agent_id": "openhands",
            "attempt": 1,
            "status": "succeeded",
            "summary": "smoke ok",
            "metrics": {"duration_ms": 1, "steps": 1, "commands": 1},
            "recommended_action": "promote",
        },
        "validation": {"run_id": "smoke", "passed": True, "checks": []},
        "metadata": {},
    }

    def fake_run(*args, **kwargs):
        _ = args, kwargs
        return SimpleNamespace(stdout=json.dumps(fake_summary), stderr="", returncode=0)

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    exit_code = module.main()
    output = json.loads(capsys.readouterr().out)

    expected_path = repo_root / "artifacts" / "live-run-stability" / "retry-overview.json"
    assert exit_code == 0
    assert output["retry_overview_json_path"] == str(expected_path)
    assert expected_path.exists()
