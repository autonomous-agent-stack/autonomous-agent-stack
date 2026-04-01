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

- `supervisor_heartbeat_to_worker_registration()` 已在后续 registration 集成中接线；本节仅描述 heartbeat 主线。
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

---

## Changelog: Registration Integration

### What changed

Linux supervisor registration is now wired into the real production registry path:

1. `WorkerRegistryService.get_worker_registration("linux_housekeeper")`
   reads the real `supervisor_status.json` / `supervisor_heartbeat.json` files
   and calls `supervisor_heartbeat_to_worker_registration()`.
2. `_linux_housekeeper_worker()` now reuses that unified registration result and
   down-maps it back to legacy `WorkerRegistrationRead`, so `get_worker_registration()`,
   `get_worker()` and `list_workers()` stay aligned.
3. Added 5 integration tests covering idle / running / stopped status, metadata,
   and consistency against `get_worker_heartbeat()` and `list_workers()`.
4. Added the new integration test file to CI.
5. Registration metadata and stopped-state errors now come directly from
   `supervisor_heartbeat_to_worker_registration()`, instead of being re-built in
   `WorkerRegistryService`.

### Before

```text
get_worker_registration("linux_housekeeper")
  → AttributeError / no production path

_linux_housekeeper_worker()
  → hand-built WorkerRegistrationRead only
  → did not call supervisor_heartbeat_to_worker_registration()
```

### After

```text
get_worker_registration("linux_housekeeper")
  → _read_linux_supervisor_state()
  → supervisor_heartbeat_to_worker_registration()
  → WorkerRegistration
  → metadata enriched with queue_depth / process_status / pid / task ids / message

_linux_housekeeper_worker()
  → get_worker_registration("linux_housekeeper")
  → WorkerRegistrationRead  (legacy-compatible projection)
```

### Tests (5 total)

| Test | Condition | Expected |
|------|-----------|----------|
| `test_fresh_idle_registration_reflects_real_status` | idle + 5s age | `WorkerRegistration.status == ONLINE`, `worker_type == LINUX` |
| `test_running_registration_reflects_real_status_and_queue_pid_metadata` | running + task_id + pid | `status == BUSY`, metadata keeps queue / pid / task |
| `test_stopped_registration_reflects_real_status` | stopped + message | `status == OFFLINE` |
| `test_registration_status_matches_heartbeat_and_list_workers` | running | registration / heartbeat / list_workers status agree |
| `test_registration_shape_includes_unified_compat_fields` | idle | allowed_actions / capabilities / max_concurrent_tasks / registered_at / backend_kind present |

### Not changed

- No automatic retry/fallback execution.
- No independent persistence for WorkerRegistration data.
- No CPU / memory metrics collection.
- API response model for `/workers` remains `WorkerRegistrationRead`.

---

## Changelog: Control-Plane Worker API Compatibility

### What changed

No additional production wiring was required in this round. Audit plus endpoint-level
integration tests confirmed that:

1. `/api/v1/control-plane/workers` already consumes `WorkerRegistryService.list_workers()`
2. `/api/v1/control-plane/workers/{worker_id}` already consumes `WorkerRegistryService.get_worker()`
3. For `linux_housekeeper`, both paths already project from unified registration / heartbeat
   sources while keeping the external response model as legacy `WorkerRegistrationRead`

This round adds API-level integration coverage and CI coverage for that compatibility layer.

### Verified compatibility

- `status` stays aligned with unified heartbeat in idle / running / stopped scenarios
- legacy top-level fields remain unchanged
- metadata keeps `queue_depth` / `pid` / `current_task_id` / `message`
- API payload still remains `WorkerRegistrationRead`, not unified `WorkerRegistration`

---

## Changelog: Downstream Task API Consumption

### What changed

Existing downstream task APIs now consume the already-persisted unified Linux
execution data without changing their external response models:

1. `ControlPlaneTaskRead.metadata` now includes `run_status`, `gate_outcome`,
   and `gate_action`, derived from persisted `result_payload["run_record"]` and
   `result_payload["gate_evaluation"]`
2. `HousekeeperTaskRead.metadata` mirrors the same derived fields from the
   control-plane task while preserving existing legacy fields like `dry_run`
3. `result_payload` remains unchanged and still carries the full persisted
   `gate_evaluation` + `run_record` payloads

### Before

```text
/api/v1/control-plane/tasks/{id}
  → could read result_payload
  → did not surface run_status / gate_outcome / gate_action in a compatibility field

/api/v1/openclaw/housekeeper/tasks/{id}
  → mirrored result_payload
  → metadata only carried frontdesk-local fields like dry_run
```

### After

```text
/api/v1/control-plane/tasks/{id}
  → metadata.run_status
  → metadata.gate_outcome
  → metadata.gate_action
  → result_payload unchanged

/api/v1/openclaw/housekeeper/tasks/{id}
  → same metadata projection
  → legacy top-level fields unchanged
  → result_payload unchanged
```

### Tests

- `test_control_plane_task_detail_consumes_run_and_gate_metadata`
- `test_housekeeper_task_detail_consumes_run_and_gate_metadata_without_breaking_legacy_fields`
- `test_housekeeper_task_detail_preserves_result_payload_and_summary_fields`

---

## Changelog: Gate Verdict Manual Approval Routing

### What changed

The real Linux control-plane path now consumes persisted gate verdicts at the
minimal control point in `ControlPlaneService._execute()`:

1. `gate_action == needs_review` now routes the task into the existing
   `APPROVAL_REQUIRED` channel
2. exhausted timeout paths that evaluate to `gate_action == fallback` also route
   into the same `APPROVAL_REQUIRED` channel
3. `success` still follows the existing `COMPLETED` path
4. `retry` still does not execute automatically in this round
5. `result_payload["gate_evaluation"]` and `result_payload["run_record"]` remain
   intact and are still mirrored downstream unchanged

### Before

```text
Linux supervisor run
  → gate_evaluation written into result_payload
  → task status decided only by summary.success
  → needs_review / fallback verdicts ended as FAILED
```

### After

```text
Linux supervisor run
  → gate_evaluation written into result_payload
  → if gate_action in {needs_review, fallback}
       -> create approval request
       -> task status = APPROVAL_REQUIRED
  → else keep existing completed / failed behavior
```

### Tests

- `test_infra_error_dispatch_routes_needs_review_into_approval`
- `test_timeout_with_exhausted_manual_fallback_routes_into_approval`
- `test_control_plane_task_detail_consumes_run_and_gate_metadata`
- `test_housekeeper_task_detail_consumes_run_and_gate_metadata_without_breaking_legacy_fields`
- `test_infra_error_produces_run_status_failed`
