from __future__ import annotations

import json
from pathlib import Path


PHASE2_MANIFEST_PATH = Path("benchmarks/live-run-stability/phase-2/tasks.json")
POSITIVE_MANIFEST_PATH = Path("benchmarks/live-run-stability/tasks.json")


def _load_phase2_manifest() -> dict[str, object]:
    return json.loads(PHASE2_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_live_run_stability_phase2_manifest_is_well_formed() -> None:
    data = _load_phase2_manifest()

    assert data["suite_name"] == "live-run-stability-phase-2"
    assert data["version"] == 1
    assert data["baseline_suite"] == "live-run-stability"
    assert data["scope"] == "private-alpha guarded rollout failure probes"

    tasks = data["tasks"]
    assert isinstance(tasks, list)
    assert len(tasks) == 2

    for task in tasks:
        assert task["task_id"]
        assert task["name"]
        assert task["purpose"]
        assert task["prompt"]
        assert task["trigger_mechanism"]
        assert task["lane"] == "phase-2"
        assert task["scenario_type"] == "intentional_failure"
        assert task["expected_artifacts"]
        assert "summary.json" in task["expected_artifacts"]
        assert task["pass_conditions"]
        assert 60 <= int(task["max_duration_seconds"]) <= 300
        assert int(task["retry_attempts"]) >= 0
        assert task["main_failure_bucket"] in {"infra", "business_validation"}

        expected = task["expected_outcome"]
        assert expected["summary"]["final_status"] in {"failed", "human_review"}
        assert expected["summary"]["driver_status"] in {"stalled_no_progress", "succeeded"}
        assert expected["summary"]["business_assertion_status"] == "failed"
        assert expected["failure_status"]
        assert expected["failure_layer"]
        assert expected["failure_stage"]
        assert expected["retry_result"] in {
            "not_requested",
            "not_needed",
            "not_attempted",
            "recovered",
            "exhausted",
        }


def test_phase2_manifest_failure_expectations_are_complete() -> None:
    tasks = {
        task["task_id"]: task
        for task in _load_phase2_manifest()["tasks"]
    }

    stall = tasks["fail-stall-no-progress"]
    assert stall["expected_artifacts"] == [
        "summary.json",
        "events.ndjson",
        "status.json",
        "heartbeat.json",
    ]
    assert stall["retry_attempts"] == 1
    assert stall["max_duration_seconds"] == 180
    assert stall["main_failure_bucket"] == "infra"
    assert stall["expected_outcome"] == {
        "summary": {
            "final_status": "failed",
            "driver_status": "stalled_no_progress",
            "business_assertion_status": "failed",
        },
        "failure_status": "stalled_no_progress",
        "failure_layer": "infra",
        "failure_stage": "stalled_no_progress",
        "retry_result": "not_attempted",
    }
    assert "summary.final_status == failed" in stall["pass_conditions"]
    assert "summary.failure_status == stalled_no_progress" in stall["pass_conditions"]
    assert "events.ndjson records fallback_skipped with reason stalled_no_progress" in stall["pass_conditions"]

    business = tasks["fail-business-assertion-mismatch"]
    assert business["expected_artifacts"] == [
        "summary.json",
        "events.ndjson",
        "driver_result.json",
        "artifacts/promotion.patch",
    ]
    assert business["retry_attempts"] == 0
    assert business["max_duration_seconds"] == 240
    assert business["main_failure_bucket"] == "business_validation"
    assert business["warmup_strategy"].startswith("Prewarm the AI Lab runtime")
    assert business["target_file"] == "src/phase2_business_probe.py"
    assert (
        business["target_contents"]
        == "\"\"\"Phase 2 business validation probe.\"\"\"\n\nVALUE = \"phase2-business-probe\"\n"
    )
    assert business["validator"] == {
        "id": "phase2.business_assertion.required_marker",
        "kind": "command",
        "target_file": "src/phase2_business_probe.py",
        "required_marker": "PHASE2_REQUIRED_MARKER",
        "expectation": "fail when the fixed file does not contain the required marker",
    }
    assert business["expected_outcome"] == {
        "summary": {
            "final_status": "human_review",
            "driver_status": "succeeded",
            "business_assertion_status": "failed",
        },
        "failure_status": "assertion_failed",
        "failure_layer": "business_validation",
        "failure_stage": "phase2.business_assertion.required_marker",
        "retry_result": "not_requested",
    }
    assert "summary.final_status == human_review" in business["pass_conditions"]
    assert (
        "summary.driver_result.changed_paths contains src/phase2_business_probe.py"
        in business["pass_conditions"]
    )
    assert "summary.failure_status == assertion_failed" in business["pass_conditions"]
    assert "summary.failure_stage == phase2.business_assertion.required_marker" in business["pass_conditions"]


def test_phase2_manifest_is_disjoint_from_positive_suite() -> None:
    phase2 = _load_phase2_manifest()
    positive = json.loads(POSITIVE_MANIFEST_PATH.read_text(encoding="utf-8"))

    positive_ids = {task["task_id"] for task in positive["tasks"]}
    phase2_ids = {task["task_id"] for task in phase2["tasks"]}

    assert phase2_ids == {
        "fail-stall-no-progress",
        "fail-business-assertion-mismatch",
    }
    assert phase2_ids.isdisjoint(positive_ids)
    assert all(not task_id.startswith("fail-") for task_id in positive_ids)

    for task in phase2["tasks"]:
        assert task["scenario_type"] == "intentional_failure"
        assert task["expected_outcome"]["summary"]["final_status"] not in {
            "completed",
            "ready_for_promotion",
            "promoted",
            "succeeded",
        }
        assert all("ready_for_promotion" not in condition for condition in task["pass_conditions"])
