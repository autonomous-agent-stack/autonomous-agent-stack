from __future__ import annotations

import json
from pathlib import Path

from autoresearch.benchmarks.live_run_stability_phase2 import (
    generate_live_run_stability_phase2_gate_report,
)


def _write_manifest(tmp_path: Path) -> Path:
    tasks_path = tmp_path / "benchmarks" / "live-run-stability" / "phase-2" / "tasks.json"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability-phase-2",
                "baseline_suite": "live-run-stability",
                "tasks": [
                    {
                        "task_id": "fail-business-assertion-mismatch",
                        "name": "business validation failure probe: execution succeeds but assertion fails",
                        "target_file": "src/phase2_business_probe.py",
                        "expected_artifacts": [
                            "summary.json",
                            "events.ndjson",
                            "driver_result.json",
                            "artifacts/promotion.patch",
                        ],
                        "retry_attempts": 0,
                        "expected_outcome": {
                            "summary": {
                                "final_status": "human_review",
                                "driver_status": "succeeded",
                                "business_assertion_status": "failed",
                            },
                            "failure_status": "assertion_failed",
                            "failure_layer": "business_validation",
                            "failure_stage": "phase2.business_assertion.required_marker",
                            "retry_result": "not_requested",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return tasks_path


def _write_phase2_summary(
    run_root: Path,
    *,
    final_status: str = "human_review",
    driver_status: str = "succeeded",
    business_assertion_status: str = "failed",
    failure_status: str = "assertion_failed",
    failure_layer: str = "business_validation",
    failure_stage: str = "phase2.business_assertion.required_marker",
    retry_result: str = "not_requested",
    retry_budget: int = 0,
    retry_attempts_used: int = 0,
    include_events: bool = True,
    include_patch: bool = True,
    noise: dict[str, object] | None = None,
) -> None:
    run_dir = run_root / "fail-business-assertion-mismatch"
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    if include_events:
        (run_dir / "events.ndjson").write_text('{"type":"event"}\n', encoding="utf-8")
    (run_dir / "driver_result.json").write_text(json.dumps({"status": driver_status}), encoding="utf-8")
    if include_patch:
        (run_dir / "artifacts" / "promotion.patch").write_text("diff --git a b\n", encoding="utf-8")

    summary = {
        "final_status": final_status,
        "business_assertion_status": business_assertion_status,
        "failure_status": failure_status,
        "failure_layer": failure_layer,
        "failure_stage": failure_stage,
        "retry_result": retry_result,
        "retry_budget": retry_budget,
        "retry_attempts_used": retry_attempts_used,
        "driver_result": {
            "status": driver_status,
            "changed_paths": ["src/phase2_business_probe.py"],
        },
        "artifacts_produced": [
            str(run_dir / "summary.json"),
            str(run_dir / "driver_result.json"),
            str(run_dir / "artifacts" / "promotion.patch"),
            str(run_dir / "events.ndjson"),
        ],
    }
    if noise:
        summary.update(noise)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def test_phase2_gate_passes_when_summary_matches_baseline(tmp_path: Path) -> None:
    tasks_path = _write_manifest(tmp_path)
    run_root = tmp_path / "phase2-runs"
    _write_phase2_summary(run_root)

    report = generate_live_run_stability_phase2_gate_report(tasks_path=tasks_path, run_root=run_root)

    assert report["passed"] is True
    assert report["failed_task_count"] == 0
    assert report["tasks"][0]["passed"] is True
    assert report["tasks"][0]["mismatches"] == []


def test_phase2_gate_report_contract_is_stable(tmp_path: Path) -> None:
    tasks_path = _write_manifest(tmp_path)
    run_root = tmp_path / "phase2-runs"
    _write_phase2_summary(run_root, include_patch=False)

    report = generate_live_run_stability_phase2_gate_report(tasks_path=tasks_path, run_root=run_root)

    assert set(report) == {
        "report_version",
        "suite_name",
        "baseline_suite",
        "task_count",
        "failed_task_count",
        "passed",
        "tasks",
    }
    assert report["report_version"] == 1
    assert set(report["tasks"][0]) == {
        "task_id",
        "task_name",
        "passed",
        "mismatch_count",
        "mismatches",
    }
    assert set(report["tasks"][0]["mismatches"][0]) == {
        "code",
        "field",
        "expected",
        "actual",
    }


def test_phase2_gate_fails_when_required_artifact_is_missing(tmp_path: Path) -> None:
    tasks_path = _write_manifest(tmp_path)
    run_root = tmp_path / "phase2-runs"
    _write_phase2_summary(run_root, include_patch=False)

    report = generate_live_run_stability_phase2_gate_report(tasks_path=tasks_path, run_root=run_root)

    assert report["passed"] is False
    assert report["tasks"][0]["passed"] is False
    assert report["tasks"][0]["mismatches"] == [
        {
            "actual": "missing",
            "code": "missing_artifact",
            "expected": str(run_root / "fail-business-assertion-mismatch" / "artifacts" / "promotion.patch"),
            "field": "artifacts:artifacts/promotion.patch",
        }
    ]


def test_phase2_gate_fails_when_key_status_regresses(tmp_path: Path) -> None:
    tasks_path = _write_manifest(tmp_path)
    run_root = tmp_path / "phase2-runs"
    _write_phase2_summary(run_root, failure_stage="unexpected.failure.stage")

    report = generate_live_run_stability_phase2_gate_report(tasks_path=tasks_path, run_root=run_root)

    assert report["passed"] is False
    assert report["tasks"][0]["mismatches"] == [
        {
            "actual": "unexpected.failure.stage",
            "code": "unexpected_failure_stage",
            "expected": "phase2.business_assertion.required_marker",
            "field": "summary.failure_stage",
        }
    ]


def test_phase2_gate_fails_when_target_file_change_is_missing(tmp_path: Path) -> None:
    tasks_path = _write_manifest(tmp_path)
    run_root = tmp_path / "phase2-runs"
    _write_phase2_summary(run_root)

    summary_path = run_root / "fail-business-assertion-mismatch" / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["driver_result"]["changed_paths"] = []
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    report = generate_live_run_stability_phase2_gate_report(tasks_path=tasks_path, run_root=run_root)

    assert report["passed"] is False
    assert report["tasks"][0]["mismatches"] == [
        {
            "actual": [],
            "code": "missing_target_file_change",
            "expected": "src/phase2_business_probe.py",
            "field": "summary.driver_result.changed_paths",
        }
    ]


def test_phase2_gate_fails_when_timeout_semantics_regress(tmp_path: Path) -> None:
    tasks_path = tmp_path / "benchmarks" / "live-run-stability" / "phase-2" / "tasks.json"
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(
        json.dumps(
            {
                "suite_name": "live-run-stability-phase-2",
                "baseline_suite": "live-run-stability",
                "tasks": [
                    {
                        "task_id": "fail-timeout-probe",
                        "name": "timeout failure probe: keep progress alive until the hard timeout ends the run",
                        "expected_artifacts": [
                            "summary.json",
                            "events.ndjson",
                            "status.json",
                            "heartbeat.json",
                        ],
                        "retry_attempts": 0,
                        "expected_outcome": {
                            "summary": {
                                "final_status": "failed",
                                "driver_status": "timed_out",
                                "business_assertion_status": "failed",
                            },
                            "failure_status": "timed_out",
                            "failure_layer": "infra",
                            "failure_stage": "timed_out",
                            "retry_result": "not_requested",
                        },
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    run_root = tmp_path / "phase2-runs"
    run_dir = run_root / "fail-timeout-probe"
    run_dir.mkdir(parents=True, exist_ok=True)
    for relative_path in ("events.ndjson", "status.json", "heartbeat.json"):
        (run_dir / relative_path).write_text("{}\n", encoding="utf-8")
    (run_dir / "summary.json").write_text(
        json.dumps(
            {
                "final_status": "failed",
                "business_assertion_status": "failed",
                "failure_status": "timed_out",
                "failure_layer": "infra",
                "failure_stage": "timed_out",
                "retry_result": "not_requested",
                "retry_budget": 0,
                "retry_attempts_used": 0,
                "driver_result": {"status": "contract_error", "changed_paths": []},
                "artifacts_produced": [
                    str(run_dir / "summary.json"),
                    str(run_dir / "events.ndjson"),
                    str(run_dir / "status.json"),
                    str(run_dir / "heartbeat.json"),
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    report = generate_live_run_stability_phase2_gate_report(tasks_path=tasks_path, run_root=run_root)

    assert report["passed"] is False
    assert report["tasks"][0]["mismatches"] == [
        {
            "actual": "contract_error",
            "code": "unexpected_driver_status",
            "expected": "timed_out",
            "field": "summary.driver_result.status",
        }
    ]


def test_phase2_gate_ignores_noise_only_differences(tmp_path: Path) -> None:
    tasks_path = _write_manifest(tmp_path)
    run_root = tmp_path / "phase2-runs"
    _write_phase2_summary(
        run_root,
        noise={
            "duration_seconds": 91.2,
            "notes": "different noisy text",
            "metadata": {"real_benchmark_stdout_preview": "volatile"},
        },
    )

    report = generate_live_run_stability_phase2_gate_report(tasks_path=tasks_path, run_root=run_root)

    assert report["passed"] is True
    assert report["tasks"][0]["mismatches"] == []
