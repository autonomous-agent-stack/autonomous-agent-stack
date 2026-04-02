# Live Run Stability Phase 2

This directory holds intentional-failure probes for the guarded-rollout phase of the live-run stability suite.

## What this phase proves

- A task can fail in the watchdog path and be classified as `stalled_no_progress` instead of being misreported as a generic runtime failure.
- A task can complete execution successfully, produce a non-empty patch, and still be routed to `human_review` when a business assertion fails.
- Failure classification stays layered:
  - `infra` for watchdog / no-progress failure
  - `business_validation` for validator-driven assertion failure

## Current probes

### `fail-stall-no-progress`

- Purpose: verify a run with no durable progress is closed as `stalled_no_progress`
- Expected result:
  - `summary.final_status = failed`
  - `driver_result.status = stalled_no_progress`
  - `failure_status = stalled_no_progress`
  - `failure_layer = infra`
  - `failure_stage = stalled_no_progress`
- Retry behavior:
  - retry is skipped after the stall is detected

### `fail-business-assertion-mismatch`

- Purpose: verify that execution can succeed while business validation still fails
- Driver behavior:
  - writes exactly `src/phase2_business_probe.py`
  - produces a non-empty patch
  - does not write `PHASE2_REQUIRED_MARKER`
- Validator behavior:
  - checks only `src/phase2_business_probe.py`
  - fails when `PHASE2_REQUIRED_MARKER` is missing
- Expected result:
  - `summary.final_status = human_review`
  - `driver_result.status = succeeded`
  - `failure_status = assertion_failed`
  - `failure_layer = business_validation`
  - `failure_stage = phase2.business_assertion.required_marker`

## Reproduction

Run the phase 2 benchmark suite from the repository root:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_live_run_stability_phase2_benchmark.py
```

To run a single probe, point the phase 2 runner at a manifest subset and a clean benchmark root.

## Regression gate

After each phase-2 run, `regression-gate.json` is written to the benchmark root.
The gate compares each task's actual summary against `expected_outcome` in the manifest.

### What the gate compares

| Field | Compared? | Code on mismatch |
|-------|-----------|-----------------|
| `summary.final_status` | yes | `unexpected_final_status` |
| `summary.driver_result.status` | yes | `unexpected_driver_status` |
| `summary.business_assertion_status` | yes | `unexpected_business_assertion_status` |
| `summary.failure_status` | yes | `unexpected_failure_status` |
| `summary.failure_layer` | yes | `unexpected_failure_layer` |
| `summary.failure_stage` | yes | `unexpected_failure_stage` |
| `summary.retry_result` | yes | `unexpected_retry_result` |
| `summary.retry_budget` | yes | `unexpected_retry_budget` |
| `summary.retry_attempts_used` | yes (when `retry_result` in `{not_requested, not_attempted}`) | `unexpected_retry_attempts_used` |
| `summary.driver_result.changed_paths` (target_file) | yes | `missing_target_file_change` |
| `expected_artifacts` | yes | `missing_artifact` |
| `summary.json` presence | yes | `missing_summary` |

### What the gate ignores

`duration_seconds`, `notes`, `metadata`, and any field not listed above.

### Mismatch reason shape

Each mismatch is `{code, field, expected, actual}`. The gate report is versioned (`report_version: 1`).

### Gate report top-level keys

`report_version`, `suite_name`, `baseline_suite`, `task_count`, `failed_task_count`, `passed`, `tasks`.

Each task in `tasks` has: `task_id`, `task_name`, `passed`, `mismatch_count`, `mismatches`.

## Notes

- Keep phase 2 outputs isolated from the main live-run stability artifacts.
- Do not reuse old benchmark roots or copied runtime directories; stale artifacts can recurse into the baseline copy step.
- These probes are intentionally narrow. They exist to validate failure classification and summary semantics, not to expand the benchmark surface.
