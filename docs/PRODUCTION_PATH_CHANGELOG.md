# Production Path Changelog: Linux Gate Integration

## What changed

`ControlPlaneService._execute()` (LINUX_SUPERVISOR branch) now calls bridge
functions from `linux_supervisor_bridge.py` after each real Linux execution,
producing unified contract artifacts that are stored alongside the original
summary in `result_payload["gate_evaluation"]`.

## Before

```
LinuxSupervisorService.run_once()
  → LinuxSupervisorTaskSummaryRead
  → summary.success (boolean) → COMPLETED / FAILED
  → summary.model_dump() → result_payload
  → STOP
```

No gate evaluation. No RunStatus mapping. No GateCheck[].
Unified contracts only exercised in unit tests with FakeLinuxWorker.

## After

```
LinuxSupervisorService.run_once()
  → LinuxSupervisorTaskSummaryRead
  → supervisor_conclusion_to_gate_outcome()  → GateOutcome
  → supervisor_summary_to_gate_checks()      → GateCheck[]
  → supervisor_conclusion_to_run_status()    → RunStatus
  → make_gate_verdict()                      → GateVerdict
  → summary.model_dump() + gate_evaluation   → result_payload
  → summary.success (boolean) → COMPLETED / FAILED  (unchanged)
```

Gate evaluation is **observational, not controlling**.
Task status decision logic is unchanged — still uses `summary.success`.

## What's in result_payload

### Before (unchanged fields)

```json
{
  "task_id": "task-001",
  "run_id": "run-001",
  "conclusion": "succeeded",
  "success": true,
  "duration_seconds": 10.0,
  "artifacts": {"stdout.log": "/tmp/stdout.log"},
  "...": "all original summary fields"
}
```

### After (added field)

```json
{
  "task_id": "task-001",
  "...": "all original summary fields (preserved)",
  "gate_evaluation": {
    "gate_outcome": "success",
    "gate_action": "accept",
    "run_status": "succeeded",
    "gate_checks": [
      {"check_id": "aep_final_status", "passed": true, "detail": "ready_for_promotion", "severity": "info"},
      {"check_id": "process_exit", "passed": true, "detail": "returncode=0", "severity": "info"},
      {"check_id": "agent_completed", "passed": true, "detail": "conclusion=succeeded", "severity": "info"},
      {"check_id": "no_mock_fallback", "passed": true, "detail": "used_mock_fallback=false", "severity": "warning"},
      {"check_id": "artifacts_present", "passed": true, "detail": "1 artifacts", "severity": "info"}
    ],
    "gate_verdict_reason": "linux ok"
  }
}
```

## Impact assessment

| Dimension | Impact |
|-----------|--------|
| Task status logic | **None** — still `summary.success → COMPLETED/FAILED` |
| Retry / fallback | **None** — verdict is stored but not consumed yet |
| API responses | **Additive** — `result_payload` gains `gate_evaluation` key |
| Performance | **Negligible** — 4 pure function calls per execution |
| Backward compat | **Safe** — no fields removed, no types changed |
| New dependencies | **None** — bridge module already existed |

## Files changed

| File | Change |
|------|--------|
| `src/autoresearch/core/services/control_plane_service.py` | Added bridge calls in `_execute()` LINUX_SUPERVISOR branch |
| `tests/test_linux_gate_integration.py` | New: 6 integration tests proving gate evaluation in production path |

## Verification

```bash
PYTHONPATH=src pytest tests/test_linux_gate_integration.py -v
PYTHONPATH=src pytest ${CORE_TEST_PATHS} -q
```
