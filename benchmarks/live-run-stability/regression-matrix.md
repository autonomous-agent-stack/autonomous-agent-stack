# Live-Run Regression Matrix

| Task ID | Scenario | Expected Artifacts | Pass Condition | Max Duration |
| --- | --- | --- | --- | --- |
| `queue-queue-smoke` | `queue smoke: complete a simple linux housekeeper run` | Minimal queue-backed supervisor success path | `summary.json`, `status.json`, `heartbeat.json`, `artifacts/` | `summary.final_status == completed` | 300s |
| `queue-summary-audit` | `summary audit: inspect a live run and extract failure signals` | Turn a real live run into a root-cause note | `summary.json`, `artifacts/root_cause.json`, `artifacts/failure_notes.md` | `summary.root_cause.kind` is set | 240s |
| `queue-regression-diff` | `regression diff: compare two live-run summaries` | Compare baseline vs head run | `summary.json`, `artifacts/regression_matrix.json`, `artifacts/regression_matrix.md` | matrix records status and root-cause deltas | 360s |
| `queue-stall-classifier` | `stall classifier: explain a timed out or stalled live run` | Label stalled / timed out / mock fallback / assertion fail | `summary.json`, `artifacts/failure_classification.json`, `artifacts/failure_classification.md` | stable failure label and decisive signal | 240s |

## Notes

- These tasks are intentionally stable samples, not ad hoc prompts.
- The suite is limited to live-run observability and regression comparison.
- No scheduler, day/night, Telegram, or video-agent behavior is included.
