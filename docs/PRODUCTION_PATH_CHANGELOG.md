# Production Path Changelog: Linux Gate + Run Lifecycle Integration

## What changed

`ControlPlaneService._execute()` (LINUX_SUPERVISOR branch) calls bridge
functions from `linux_supervisor_bridge.py` after each real Linux execution,
producing unified contract artifacts stored in `result_payload`. The
`run_record` payload is normalized to the same JSON-safe string shape used by
the surrounding summary fields.

## Before

```
LinuxSupervisorService.run_once()
  -> LinuxSupervisorTaskSummaryRead
  -> summary.success (boolean) -> COMPLETED / FAILED
  -> summary.model_dump() -> result_payload
  -> STOP
```

No gate evaluation. No RunStatus mapping. No GateCheck[]. No RunRecord.
Unified contracts only exercised in unit tests with FakeLinuxWorker.

## After

```
LinuxSupervisorService.run_once()
  -> LinuxSupervisorTaskSummaryRead
  -> supervisor_conclusion_to_gate_outcome()  -> GateOutcome
  -> supervisor_summary_to_gate_checks()      -> GateCheck[]
  -> supervisor_conclusion_to_run_status()    -> RunStatus
  -> make_gate_verdict()                      -> GateVerdict
  -> supervisor_summary_to_run_record()       -> BridgeRunRecord
  -> summary.model_dump() + gate_evaluation + run_record -> result_payload
  -> summary.success (boolean) -> COMPLETED / FAILED  (unchanged)
```

Gate evaluation and run record are **observational, not controlling**.
Task status decision logic is unchanged -- still uses `summary.success`.

## What's in result_payload

### gate_evaluation (added in previous commit)

```json
{
  "gate_outcome": "success",
  "gate_action": "accept",
  "run_status": "succeeded",
  "gate_checks": [
    {"check_id": "aep_final_status", "passed": true, "detail": "ready_for_promotion"},
    {"check_id": "process_exit", "passed": true, "detail": "returncode=0"},
    {"check_id": "agent_completed", "passed": true, "detail": "conclusion=succeeded"},
    {"check_id": "no_mock_fallback", "passed": true, "detail": "used_mock_fallback=false"},
    {"check_id": "artifacts_present", "passed": true, "detail": "1 artifacts"}
  ],
  "gate_verdict_reason": "linux ok"
}
```

### run_record (added in this commit)

```json
{
  "run_id": "run-001",
  "task_id": "task-001",
  "worker_id": "linux_housekeeper",
  "status": "succeeded",
  "run_status": "succeeded",
  "started_at": "2026-04-01T12:00:00Z",
  "completed_at": "2026-04-01T12:00:10Z",
  "error_message": null,
  "result_data": {
    "artifacts": {"stdout.log": "/tmp/stdout.log"},
    "aep_final_status": "ready_for_promotion",
    "aep_driver_status": "succeeded",
    "conclusion": "succeeded",
    "duration_seconds": 10.0,
    "process_returncode": 0
  },
  "attempt": 1
}
```

**Note on `started_at` / `completed_at`**: These are derived from
`summary.started_at` and `summary.finished_at` respectively. There is no
separate QUEUED or LEASED timestamp in the current LinuxSupervisor execution
path -- the supervisor goes directly from pending to running. These fields
approximate the full run lifecycle:
- `started_at` = when the supervisor started the subprocess
- `completed_at` = when the subprocess finished (or was killed)

The `queued_at` and `leased_at` fields from the unified `RunRecord` model are
not populated because the LinuxSupervisor has no lease mechanism. If lease
tracking is added to the supervisor in the future, these should be backfilled.

## Impact assessment

| Dimension | Impact |
|-----------|--------|
| Task status logic | **None** -- still `summary.success -> COMPLETED/FAILED` |
| Retry / fallback | **None** -- verdict stored but not consumed |
| API responses | **Additive** -- `result_payload` gains `gate_evaluation` + `run_record` keys |
| Performance | **Negligible** -- 5 pure function calls per execution |
| Backward compat | **Safe** -- no fields removed, no types changed |
| New dependencies | **None** -- bridge module already existed |

## Files changed

| File | Change |
|------|--------|
| `src/autoresearch/core/services/control_plane_service.py` | Bridge calls in `_execute()` LINUX_SUPERVISOR branch plus JSON normalization for `run_record` status/timestamps |
| `tests/test_linux_gate_integration.py` | 6 integration tests proving gate evaluation |
| `tests/test_linux_run_lifecycle_integration.py` | 8 integration tests proving run lifecycle |

CI audit note: `.github/workflows/ci.yml` already included
`tests/test_linux_run_lifecycle_integration.py` in both `CORE_LINT_PATHS` and
`CORE_TEST_PATHS`, so this follow-up did not need a workflow edit.

## Verification

```bash
PYTHONPATH=src pytest tests/test_linux_gate_integration.py -v
PYTHONPATH=src pytest tests/test_linux_run_lifecycle_integration.py -v
PYTHONPATH=src pytest ${CORE_TEST_PATHS} -q
```

---

## Changelog: Heartbeat Integration (commits 86de697 + 6307136)

### What changed

Two commits wired the unified `WorkerHeartbeat` into `WorkerRegistryService`:

1. **86de697** — Added `get_worker_heartbeat()` + `_read_linux_supervisor_state()`,
   plus 5 integration tests for the `get_worker_heartbeat()` path.
2. **6307136** — Fixed `_linux_housekeeper_worker()` to reuse `_read_linux_supervisor_state()`
   and call `supervisor_heartbeat_to_worker_heartbeat()`, replacing the old inline threshold
   logic that read wrong filenames. Added 5 consistency tests proving `list_workers()` and
   `get_worker_heartbeat()` return the same status.

### Before

```
get_worker_heartbeat("linux_housekeeper")
  → None (not implemented)

_linux_housekeeper_worker()
  → reads state/status.json + state/heartbeat.json  (WRONG filenames)
  → inline threshold logic (30s/120s)
  → always OFFLINE because files don't exist
```

### After

```
get_worker_heartbeat("linux_housekeeper")
  → _read_linux_supervisor_state()
  → reads supervisor_status.json / supervisor_heartbeat.json  (correct)
  → supervisor_heartbeat_to_worker_heartbeat()  (bridge)
  → WorkerHeartbeat

_linux_housekeeper_worker()
  → _read_linux_supervisor_state()  (same method)
  → supervisor_heartbeat_to_worker_heartbeat()  (same bridge)
  → WorkerAvailabilityStatus(unified_heartbeat.status.value)
  → WorkerRegistrationRead  (status matches get_worker_heartbeat)
```

Both paths now share the same file reader and bridge function, ensuring status consistency.

### Tests (10 total)

**`TestWorkerRegistryHeartbeatIntegration`** (5 tests — `get_worker_heartbeat()` path):

| Test | Condition | Expected |
|------|-----------|----------|
| `test_fresh_idle_heartbeat_is_unified_online` | idle + 5s age | `WorkerStatus.ONLINE` |
| `test_running_heartbeat_is_unified_busy_with_active_task` | running + task_id | `WorkerStatus.BUSY`, `active_task_ids=["task-001"]` |
| `test_stale_heartbeat_is_unified_offline` | idle + 130s age | `WorkerStatus.OFFLINE` |
| `test_stopped_heartbeat_surfaces_unified_errors` | stopped + message | `WorkerStatus.OFFLINE`, `errors=["worker crashed"]` |
| `test_unified_heartbeat_uses_expected_top_level_shape` | idle | top-level keys = `{worker_id, status, metrics, active_task_ids, errors, metadata}` |

**`TestWorkerRegistryListWorkersHeartbeatConsistency`** (5 tests — `list_workers()` consistency):

| Test | Condition | Expected |
|------|-----------|----------|
| `test_running_fresh_list_workers_is_not_offline` | running | status ≠ OFFLINE |
| `test_idle_fresh_status_matches_unified_heartbeat` | idle | list_workers == get_worker_heartbeat |
| `test_stopped_status_matches_unified_heartbeat` | stopped | list_workers == get_worker_heartbeat |
| `test_stale_status_matches_unified_heartbeat` | stale | list_workers == get_worker_heartbeat |
| `test_list_workers_and_unified_heartbeat_agree_for_same_worker` | running + get_worker | full agreement |

### Not changed

- `supervisor_heartbeat_to_worker_registration()` remains unwired.
- Bridge threshold constants (`_STALE_THRESHOLD_SEC = _DEAD_THRESHOLD_SEC = 120`) unchanged — DEGRADED is unreachable.
- Worker selection / dispatch logic unchanged.
- No independent persistence for WorkerHeartbeat data.

### Files changed

| File | Change |
|------|--------|
| `src/autoresearch/core/services/worker_registry.py` | `get_worker_heartbeat()` + `_read_linux_supervisor_state()` + refactored `_linux_housekeeper_worker()` |
| `tests/test_worker_registry_heartbeat_integration.py` | 10 integration tests (166 lines) |
| `.github/workflows/ci.yml` | Added test path to CORE_LINT_PATHS + CORE_TEST_PATHS |

### Verification

```bash
PYTHONPATH=src pytest tests/test_worker_registry_heartbeat_integration.py -v
```
