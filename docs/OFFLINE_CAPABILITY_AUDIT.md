# Offline / Fake Capability Audit

Precise inventory of every capability in the stack, classified as:
- **REAL** — backed by production code that runs in deployment
- **OFFLINE-ONLY** — exists in unified contracts, tests, or scripts, but never called from production
- **FAKE** — simulated by mock data or fake_workers.py, no real backend

---

## Summary

| Category | Count | Capabilities |
|----------|-------|-------------|
| **REAL** | 11 | worker status ranking, approval flow, artifact collection, retry/fallback decision, cancel task, scope check, LinuxSupervisor subprocess, stall detection, timeout enforcement, orphan task repair, git promotion gate |
| **OFFLINE-ONLY** | 8 | task lifecycle validation, RunRecord, make_gate_verdict, WorkerHeartbeat sending, task-level lease, missing artifact detection, failure taxonomy, AEP protocol status mapping |
| **FAKE** | 7 | heartbeat age→status derivation, worker registration, console API, task filtering, run detail, Win/Yingdao execution, console approval actions |

---

## Detailed Classification

### REAL (11)

| # | Capability | Production Code |
|---|-----------|-----------------|
| 1 | Worker status ranking | `worker_registry.py:55-87` uses `worker_status_rank()` in `find_worker_for_backend()` |
| 2 | Approval flow (DB-backed) | `approvals.py` + `hitl_approval.py` wired via `dependencies.py:284` and `panel.py:130-199` |
| 3 | Artifact collection | `linux_supervisor.py:612-630` — copies stdout/stderr/AEP summary/events/patch from run dirs |
| 4 | Retry/fallback decision | `runner.py:158-179` evaluates fallback steps; `state_machine_bus.py:140-153` has DB-backed retry queue |
| 5 | Cancel task | `openclaw.py:283-294` + `panel.py:367-385` call `agent_service.cancel()` |
| 6 | Scope check (overreach) | `openhands_controlled_backend.py:197,825-841` checks changed_files against allowed/forbidden paths |
| 7 | LinuxSupervisor subprocess | `linux_supervisor.py` full lifecycle: enqueue → Popen → heartbeat → timeout → summary |
| 8 | Stall detection | `runner.py:647,758-766` (workspace file mtime) + `linux_supervisor.py:412` (heartbeat stall) |
| 9 | Timeout enforcement | `runner.py:699-715` (duration threshold) + `linux_supervisor.py:573` (conclusion mapping) |
| 10 | Orphan task repair | `linux_supervisor.py:152,207-261` — scans for RUNNING tasks without summaries |
| 11 | Git promotion gate | `git_promotion_gate.py:307-826` — full promotion workflow with preflight/validation |

### OFFLINE-ONLY (8)

| # | Capability | Where It Exists | Why Not Production |
|---|-----------|----------------|-------------------|
| 1 | Task lifecycle validation (`is_valid_transition`) | `task_contract.py:249` | Only called in tests; production sets `task.status = X` directly |
| 2 | RunRecord state machine | `run_contract.py:85` | Only used in `acceptance_run.py` and tests; production has no `RunRecord` concept |
| 3 | Gate evaluation (`make_gate_verdict`) | `task_gate_contract.py:113` | Only called in tests/scripts; production goes directly from runner result to task status |
| 4 | WorkerHeartbeat sending | `worker_contract.py:137` | Only `fake_workers.py` constructs these; production writes filesystem JSON |
| 5 | Task-level lease acquire/release | `fake_workers.py:299-323` | Production has `WriterLeaseService` for git writes only, no task lease |
| 6 | Missing artifact detection | `task_gate_contract.py:40` | Enum value exists but no production code sets `MISSING_ARTIFACTS` |
| 7 | Failure taxonomy (10 categories) | `fake_workers.py:382-538` | Only in testing; production uses `LinuxSupervisorConclusion` (7 values) and AEP strings |
| 8 | AEP protocol status mapping | `run_contract.py:150,155` | `aep_driver_status_to_run()` / `aep_final_status_to_run()` defined but never imported by production |

### FAKE (7)

| # | Capability | Mock Location | What's Fake |
|---|-----------|--------------|-------------|
| 1 | Heartbeat age→status derivation | `console.py:44,60,71` hardcodes; `fake_workers.py:285-338` simulates | Production reads filesystem JSON with hardcoded 30s/120s thresholds; no real heartbeat protocol |
| 2 | Worker registration (dynamic) | `worker_registry.py:32-38` hardcodes 4 workers | No `register()` / `unregister()` endpoint; workers are static config |
| 3 | Console API endpoints | `console.py:1-4` states "Mock data only" | All endpoints return `_MOCK_TASKS`, `_MOCK_WORKERS`, `_MOCK_RUNS` |
| 4 | Task filtering by status | `console.py:256-267` filters `_MOCK_TASKS` | No production task query with status filter in any real router |
| 5 | Run detail (logs/artifacts/gate) | `console.py:280-286` returns `_MOCK_RUNS` | No production run-detail endpoint backed by real data |
| 6 | Win/Yingdao execution | `worker_registry.py:154-164` returns `OFFLINE` + `"implemented": False` | Zero execution backend for Yingdao |
| 7 | Console approval actions | `console.py:294-317` mutates in-memory mock | Real approval endpoints exist in `approvals.py` and `panel.py` but console uses mock |

---

## Acceptance Harness Coverage vs Reality

| Harness Tests (423) | What It Verifies | Production Coverage |
|---------------------|-----------------|-------------------|
| TaskStatus transitions | State machine correctness | Production doesn't call `is_valid_transition()` |
| RunRecord lifecycle | Run status transitions | Production has no `RunRecord` model |
| Gate verdicts | Outcome→Action mapping | Production doesn't call `make_gate_verdict()` |
| Retry/fallback rules | Exhaustion upgrade logic | Production has its own retry in `runner.py` (separate logic) |
| FakeLinuxWorker execute | Worker output shapes | Real supervisor returns `LinuxSupervisorTaskSummaryRead` (different shape) |
| HeartbeatSimulation | Age→status derivation | Production reads filesystem JSON (different mechanism) |
| LeaseManager | Acquire/release/timeout | Production has no task-level lease |
| Console endpoints | Task/worker/run/approval CRUD | All mock data, no real backend |
| Acceptance 30-run | Full lifecycle with fault injection | In-memory only, never spawns processes |

**Bottom line**: The 423 tests verify the unified contract models are internally consistent. They do NOT verify that production code uses these models or follows these contracts.
