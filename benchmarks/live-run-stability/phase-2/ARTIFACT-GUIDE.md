# Phase-2 Regression Gate — Artifact Guide

## Output Artifacts

| Artifact | Role | CI Effect |
|---|---|---|
| `regression-gate.json` | **PR-blocking authority** | Workflow exits non-zero when `passed == false`. This is the sole signal that merges. |
| `regression-matrix.json` / `.md` | Task classification view | Human-readable breakdown of which tasks passed/failed and why. Explanatory only — never blocks a PR. |
| `retry-overview.json` | Audit trail | Records every retry decision, attempt count, and fallback outcome for post-hoc analysis. Explanatory only. |

## Benchmark Root

`--benchmark-root` **must** point to a clean directory outside the repository tree (e.g. `${{ runner.temp }}/live-run-stability-phase2` in CI, or `/tmp/live-run-stability-phase2` locally). The benchmark writes run artifacts, baselines, and intermediate state into this root. Keeping it outside the repo prevents baseline snapshots from recursing into benchmark output and avoids accidental commits.

## Gate Semantics (frozen)

The gate compares each task's actual `summary.json` against the `expected_outcome` declared in `tasks.json`. A mismatch on any checked field (final_status, driver_status, failure_status, failure_layer, failure_stage, retry_result, retry_budget, artifacts) fails the gate. Extra fields in the summary ("noise") are ignored.

Do not extend the gate with new semantics without an explicit scope change.
