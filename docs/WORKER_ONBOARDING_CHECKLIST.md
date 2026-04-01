# Worker Onboarding Checklist

Checklist for certifying a new worker (Linux or Win) as production-ready.
Every item must pass before a worker can be registered in the control plane.

**Design goal**: When a real Linux/Win worker adapter is implemented, swap
`_make_worker()` in `test_worker_contract_compliance.py` and all tests must pass.

---

## Pre-requisites

- [ ] Worker implements `registration() -> WorkerRegistration`
- [ ] Worker implements `heartbeat() -> WorkerHeartbeat`
- [ ] Worker implements `execute(task, *, outcome) -> dict` or equivalent

## Registration Contract

- [ ] `WorkerRegistration.worker_type` is a valid `WorkerType` enum value
- [ ] `WorkerRegistration.capabilities` is non-empty list of strings
- [ ] `WorkerRegistration.allowed_actions` is non-empty list of `AllowedAction` enums
- [ ] `WorkerRegistration.max_concurrent_tasks >= 1`
- [ ] `WorkerRegistration.status` is one of `ONLINE / BUSY / DEGRADED / OFFLINE`
- [ ] `WorkerRegistration.backend_kind` matches a known `HousekeeperBackendKind`

## Heartbeat Contract

- [ ] Returns `WorkerHeartbeat` with valid `worker_id`
- [ ] Contains `WorkerMetrics` with `cpu_usage_percent >= 0` and `memory_usage_mb >= 0`
- [ ] Status is `BUSY` when executing a task, `ONLINE` when idle
- [ ] `active_task_ids` includes currently executing task IDs
- [ ] Heartbeat is sent at `heartbeat_interval_sec` frequency (default 30s)
- [ ] Control plane detects OFFLINE when heartbeat exceeds `heartbeat_dead_sec` (default 300s)

## Run Lifecycle Contract

- [ ] Run follows: `QUEUED -> LEASED -> RUNNING -> SUCCEEDED | FAILED | NEEDS_REVIEW`
- [ ] Every `RunRecord.transition_to()` call succeeds (no invalid transitions)
- [ ] Successful run: `TaskResult(success=True)` with output data
- [ ] Failed run: `TaskError(code, message, retryable, suggested_action)` populated
- [ ] Timing fields populated: `queued_at`, `started_at`, `completed_at`
- [ ] `error_message` set on `RunRecord` for failures

## Gate Integration Contract

- [ ] Execution result can be evaluated by `make_gate_verdict()`
- [ ] SUCCESS outcome maps to ACCEPT action
- [ ] TIMEOUT outcome maps to RETRY action (or FALLBACK/NEEDS_REVIEW if exhausted)
- [ ] OVERREACH outcome maps to REJECT action
- [ ] MISSING_ARTIFACTS outcome maps to RETRY action
- [ ] NEEDS_HUMAN_CONFIRM outcome maps to NEEDS_REVIEW action
- [ ] Gate verdict contains: outcome, action, reason, checks, evaluated_at

## Error Classification Contract

- [ ] TIMEOUT / CRASH / NETWORK_ERROR errors marked `retryable=True`
- [ ] PERMISSION_DENIED / OVERREACH / DISK_FULL errors marked `retryable=False`
- [ ] Every error has a non-empty `code` and `message`
- [ ] Every error has a `suggested_action` ("retry", "manual", "fallback")

## Artifact Contract

- [ ] Successful execution produces at least one artifact
- [ ] Artifacts match `TaskArtifact` shape: `name`, `path`, `content_type`, `size_bytes`
- [ ] Win/Yingdao workers produce screenshots when form_fill / needs_review
- [ ] Linux workers produce stdout.log, stderr.log at minimum

## Lease Contract

- [ ] Worker acquires lease before starting execution
- [ ] Worker releases lease on completion (success or failure)
- [ ] Lease timeout (default 900s) triggers forced release
- [ ] Concurrent workers cannot acquire lease for same task

## Scope Contract (Linux)

- [ ] Changed files validated against `allowed_paths`
- [ ] Forbidden paths trigger `GateOutcome.OVERREACH`
- [ ] Scope check runs as part of gate evaluation, not just worker self-report

## Failure Handling Contract

- [ ] Process crash (exit code != 0) produces `FAILED` status, not hang
- [ ] Timeout (exceeding `task_timeout_sec`) produces `FAILED` + `TIMEOUT` error
- [ ] Stall (no progress for `stall_timeout_sec`) detected and reported
- [ ] Orphaned tasks (supervisor crash) recoverable: RUNNING -> QUEUED

---

## Test Files

| Test File | What It Verifies |
|-----------|-----------------|
| `tests/test_worker_contract_compliance.py` | All 5 contracts above (swap `_make_worker()` for real adapter) |
| `tests/test_acceptance_gaps.py` | 8 blind-spot scenarios the harness misses |
| `tests/test_acceptance_harness.py` | 30-run fault injection suite |
| `tests/test_illegal_transitions.py` | State machine correctness (130 invalid pairs) |
| `tests/test_gate_scenarios.py` | 5 gate outcome scenarios |
| `tests/test_retry_fallback_review.py` | Retry exhaustion + fallback + review rules |

## How to Onboard a New Worker

1. Implement the worker adapter (class with `registration()`, `heartbeat()`, `execute()`)
2. Change `_make_worker()` in `test_worker_contract_compliance.py` to return your adapter
3. Run: `PYTHONPATH=src pytest tests/test_worker_contract_compliance.py -v`
4. All tests must pass
5. Add the worker to `WorkerRegistryService.list_workers()`
6. Register the backend in `ControlPlaneService._execute()`
7. Run full suite: `PYTHONPATH=src pytest ${CORE_TEST_PATHS} -q`
