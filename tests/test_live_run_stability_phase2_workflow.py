from __future__ import annotations

from pathlib import Path

import yaml


WORKFLOW_PATH = Path(".github/workflows/live-run-stability-phase2-gate.yml")


def _load_workflow() -> dict[str, object]:
    return yaml.load(WORKFLOW_PATH.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def _step_by_name(steps: list[dict[str, object]], name: str) -> dict[str, object]:
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(f"workflow step not found: {name}")


def test_phase2_workflow_supports_manual_and_pr_triggers() -> None:
    workflow = _load_workflow()

    assert workflow["name"] == "Live Run Stability Phase-2 Gate"
    triggers = workflow["on"]
    assert "workflow_dispatch" in triggers
    assert "pull_request" in triggers

    pull_request = triggers["pull_request"]
    assert ".github/workflows/live-run-stability-phase2-gate.yml" in pull_request["paths"]
    assert "benchmarks/live-run-stability/phase-2/**" in pull_request["paths"]
    assert "scripts/run_live_run_stability_phase2_benchmark.py" in pull_request["paths"]
    assert "src/autoresearch/benchmarks/live_run_stability_phase2.py" in pull_request["paths"]


def test_phase2_workflow_runs_existing_gate_script_and_uploads_artifacts() -> None:
    workflow = _load_workflow()
    job = workflow["jobs"]["phase2-gate"]
    assert job["env"]["PHASE2_BENCHMARK_ROOT"] == "${{ runner.temp }}/live-run-stability-phase2"
    steps = job["steps"]

    run_step = _step_by_name(steps, "Run phase-2 gate")
    assert run_step["env"]["PYTHONPATH"] == "src"
    assert "python scripts/run_live_run_stability_phase2_benchmark.py" in run_step["run"]
    assert '--benchmark-root "${PHASE2_BENCHMARK_ROOT}"' in run_step["run"]
    assert 'tee "${PHASE2_BENCHMARK_ROOT}/workflow-output.json"' in run_step["run"]

    explain_step = _step_by_name(steps, "Explain phase-2 gate result")
    assert explain_step["if"] == "${{ always() }}"
    assert "regression-gate.json" in explain_step["run"]
    assert "Keep the benchmark root outside the repository" in explain_step["run"]
    assert "PR blocking stays anchored to regression-gate.json only" in explain_step["run"]
    assert "regression-matrix and retry-overview remain explanatory artifacts" in explain_step["run"]

    upload_step = _step_by_name(steps, "Upload phase-2 gate artifacts")
    assert upload_step["if"] == "${{ always() }}"
    assert upload_step["uses"] == "actions/upload-artifact@v4"
    assert upload_step["with"]["name"] == "live-run-stability-phase2-gate"
    assert upload_step["with"]["if-no-files-found"] == "error"
    artifact_paths = upload_step["with"]["path"]
    assert "${{ env.PHASE2_BENCHMARK_ROOT }}/regression-gate.json" in artifact_paths
    assert "${{ env.PHASE2_BENCHMARK_ROOT }}/regression-matrix.json" in artifact_paths
    assert "${{ env.PHASE2_BENCHMARK_ROOT }}/retry-overview.json" in artifact_paths
    assert "${{ env.PHASE2_BENCHMARK_ROOT }}/runs/**" in artifact_paths


def test_phase2_workflow_explain_step_documents_artifact_roles() -> None:
    """The explain step must name the three artifact roles explicitly so the
    workflow is self-documenting and stays in sync with
    benchmarks/live-run-stability/phase-2/ARTIFACT-GUIDE.md."""
    workflow = _load_workflow()
    steps = workflow["jobs"]["phase2-gate"]["steps"]
    explain_step = _step_by_name(steps, "Explain phase-2 gate result")
    explain_run: str = explain_step["run"]

    # regression-gate.json is the PR-blocking authority
    assert "regression-gate.json" in explain_run
    assert "PR blocking stays anchored to regression-gate.json only" in explain_run

    # regression-matrix and retry-overview are explanatory only
    assert "regression-matrix" in explain_run
    assert "retry-overview" in explain_run
    assert "explanatory" in explain_run

    # benchmark root must be outside the repository
    assert "benchmark root outside the repository" in explain_run.lower()


def test_phase2_workflow_benchmark_root_is_outside_repo() -> None:
    """CI must use runner.temp (outside the checkout tree) as benchmark root."""
    workflow = _load_workflow()
    env = workflow["jobs"]["phase2-gate"]["env"]
    benchmark_root: str = env["PHASE2_BENCHMARK_ROOT"]
    assert benchmark_root.startswith("${{ runner.temp }}")
    assert "live-run-stability-phase2" in benchmark_root
