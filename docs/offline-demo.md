# Offline Demo & Acceptance Guide

## Quick Start

```bash
# 1. Run the interactive demo (5 scenarios, no real workers)
PYTHONPATH=src python scripts/demo_offline.py

# 2. Run the formal acceptance harness (30 consecutive runs, 5 fault types)
PYTHONPATH=src python scripts/acceptance_run.py --runs 30

# 3. Run with verbose output and JSON report
PYTHONPATH=src python scripts/acceptance_run.py --runs 50 --verbose --json-report report.json

# 4. Run all contract + console + fixture tests
PYTHONPATH=src pytest \
  tests/test_task_contract.py \
  tests/test_worker_contract.py \
  tests/test_run_contract.py \
  tests/test_task_gate_contract.py \
  tests/test_console.py \
  tests/test_offline_demo_fixture.py \
  tests/test_illegal_transitions.py \
  tests/test_gate_scenarios.py \
  tests/test_retry_fallback_review.py \
  tests/test_fake_workers.py \
  tests/test_acceptance_harness.py \
  -q
```

---

## Acceptance Test Harness (`scripts/acceptance_run.py`)

### Purpose
Formal acceptance test that proves the control plane handles every failure mode correctly across 30–50 consecutive runs. Each run injects a specific fault and verifies the entire lifecycle produces correct outcomes at every layer: run status, gate verdict, gate action, and task status.

### Fault Injection Types

| Fault Type | Worker Result | Run Status | Gate Outcome | Gate Action | Task Status |
|------------|--------------|------------|--------------|-------------|-------------|
| **timeout** | Worker exceeds 900s deadline | `FAILED` | `TIMEOUT` | `RETRY` or `FALLBACK` | `QUEUED` (re-queued) |
| **crash** | Process killed (exit 137) | `FAILED` | `TIMEOUT` | `RETRY` or `FALLBACK` | `QUEUED` (re-queued) |
| **overreach** | Agent modified out-of-scope files | `SUCCEEDED` | `OVERREACH` | `REJECT` | `REJECTED` |
| **missing_artifacts** | Required output not produced | `SUCCEEDED` | `MISSING_ARTIFACTS` | `RETRY` | `QUEUED` or `NEEDS_REVIEW` |
| **permission_denied** | Insufficient filesystem perms | `FAILED` | `NEEDS_HUMAN_CONFIRM` | `NEEDS_REVIEW` | `NEEDS_REVIEW` |
| **success** | Normal execution | `SUCCEEDED` | `SUCCESS` | `ACCEPT` | `SUCCEEDED` |

### Run Lifecycle (per run)

```
1. task_created       — Task object initialized (PENDING)
2. task_queued        — Task dispatched (QUEUED)
3. run_created        — RunRecord initialized (QUEUED)
4. run_leased         — Worker acquires lease (LEASED)
5. heartbeat_busy     — Worker sends BUSY heartbeat
6. run_running        — Execution begins (RUNNING)
7. worker_executed    — Fake worker returns result (with fault injection)
8. run_terminal       — Run reaches terminal state (SUCCEEDED/FAILED/NEEDS_REVIEW)
9. gate_evaluated     — Gate checks applied, verdict rendered
10. action_applied    — Gate action mapped to task status transition
```

### Acceptance Criteria
- All 10 lifecycle steps must complete for every run
- Run status must match the fault profile's expected terminal state
- Gate outcome must match the fault profile
- Gate action must be the expected action (or an allowed upgrade from retry exhaustion)
- Task status must be consistent with the gate action applied
- **100% pass rate required** — any single failure rejects the entire acceptance

### JSON Report
Pass `--json-report path.json` to get a machine-readable report with:
- Per-run outcomes (expected vs actual for each layer)
- Fault type breakdown (pass/fail counts per category)
- Timestamps and duration

---

## Console Demo

Start the API server:

```bash
PYTHONPATH=src uvicorn autoresearch.api.app:app --reload --port 8000
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/console/` | GET | HTML landing page with task/worker tables, run detail viewer, approval queue |
| `/api/v1/console/tasks` | GET | List tasks. Query params: `status`, `priority`, `limit` |
| `/api/v1/console/workers` | GET | List workers with status, capabilities, heartbeat age, metrics |
| `/api/v1/console/runs/{run_id}` | GET | Run detail: status timeline, logs, artifacts, gate verdict with checks |
| `/api/v1/console/approvals` | GET | Pending approval queue (tasks with `approval_required` status) |
| `/api/v1/console/approvals/{task_id}/approve` | POST | Approve → task re-queued |
| `/api/v1/console/approvals/{task_id}/reject` | POST | Reject → task rejected |
| `/api/v1/console/approvals/{task_id}/retry` | POST | Retry failed task → re-queued with incremented retry_count |
| `/api/v1/console/approvals/{task_id}/fallback` | POST | Delegate to fallback agent → re-queued with fallback_agent set |
| `/api/v1/console/approval-log` | GET | Audit trail of all approval actions taken |

### Run Detail Page

The landing page includes an interactive run detail viewer. Enter a run ID (e.g. `run-001`, `run-002`) and click "Load Run" to see:

- **Status bar**: Current run status and attempt number
- **Timeline**: `queued_at → started_at → completed_at` timestamps
- **Logs**: Timestamped log entries with color-coded severity (info/warning/error)
- **Artifacts**: Output files with type, path, and size
- **Gate Verdict**: Outcome → action mapping, reason, and individual check results with pass/fail indicators

### Task Filtering

The task table supports filtering by status using the button bar:
- All / Pending / Queued / Running / Succeeded / Failed / Awaiting Approval

### Worker Status

The worker table shows for each worker:
- Status badge (online/busy/degraded/offline)
- Capability tags
- Last heartbeat timestamp
- Heartbeat age (time since last heartbeat)
- Metrics (CPU, memory, active tasks, completed tasks)

---

## Review / Retry / Fallback Decision Logic

### Overview

When a run completes (or fails), the **gate** evaluates the outcome and decides what happens next. The decision chain is:

```
Run completes
    ↓
Gate evaluates (checks + outcome)
    ↓
Gate verdict (outcome + action)
    ↓
Action applied to task
```

### Gate Outcomes → Default Actions

| Gate Outcome | Default Action | When It Happens |
|--------------|---------------|-----------------|
| `SUCCESS` | `ACCEPT` | All checks passed, run completed normally |
| `TIMEOUT` | `RETRY` | Worker exceeded configured deadline |
| `MISSING_ARTIFACTS` | `RETRY` | Required output artifacts not produced |
| `OVERREACH` | `REJECT` | Agent modified files outside allowed scope |
| `NEEDS_HUMAN_CONFIRM` | `NEEDS_REVIEW` | Policy requires manual sign-off |

### Retry Exhaustion Rules

When the default action is `RETRY`, the gate checks `retry_attempt` against `max_retries`:

```
if retry_attempt < max_retries:
    action = RETRY                    # Normal retry
elif fallback_agent_id is available:
    action = FALLBACK                 # Upgrade: delegate to fallback agent
else:
    action = NEEDS_REVIEW             # Upgrade: escalate to human
```

This means:
- **Retry**: Same agent re-executes the task (new RunRecord created)
- **Fallback**: A different agent takes over (e.g. simpler/safer backup agent)
- **Needs Review**: No automatic recovery possible, human must decide

### Task Status Transitions

After the gate action is applied, the task transitions:

| Gate Action | Task Status | Next Step |
|-------------|------------|-----------|
| `ACCEPT` | `SUCCEEDED` | Terminal — task is complete |
| `REJECT` | `REJECTED` | Terminal — no further action |
| `RETRY` | `QUEUED` | Re-enter dispatch queue |
| `FALLBACK` | `QUEUED` | Re-enter queue with fallback agent binding |
| `NEEDS_REVIEW` | `NEEDS_REVIEW` | Wait for human decision |

### Human Decision Paths (Needs Review)

From `NEEDS_REVIEW`, a human can choose:

```
NEEDS_REVIEW
    ├──→ SUCCEEDED    (human confirms the result is acceptable)
    ├──→ FAILED       (human decides the result is unusable)
    ├──→ QUEUED       (human requests a retry with same or different agent)
    └──→ REJECTED     (human decides to abort)
```

### Approval Flow (Pre-Execution)

For tasks marked `requires_approval=True`:

```
PENDING → APPROVAL_REQUIRED → QUEUED     (approved, proceed)
                          → REJECTED     (denied, abort)
                          → CANCELLED    (withdrawn)
```

### Failure Taxonomy

10 failure categories with retry classification:

**Retryable** (automatic recovery possible):
- `TIMEOUT` — Worker exceeded deadline
- `CRASH` — Process killed by OS
- `MISSING_ARTIFACTS` — Output not produced
- `NETWORK_ERROR` — Connectivity lost
- `CONTRACT_ERROR` — Invalid response format
- `STALL` — No forward progress
- `OOM` — Out of memory

**Non-retryable** (requires human intervention):
- `OVERREACH` — Scope violation
- `PERMISSION_DENIED` — Access denied
- `DISK_FULL` — Resource exhaustion

---

## Test Coverage

- **423+ tests** across unified contracts, console, simulation fixtures, and acceptance harness
- Exhaustive illegal state transition matrix (every invalid pair for TaskStatus + RunStatus)
- Five gate scenario tests (success, timeout, overreach, missing artifacts, human confirm)
- Retry/fallback/needs_review rule boundary tests (exhaustion, max_retries=0, negative attempt)
- Failure taxonomy coverage (10 categories, retryable vs non-retryable)
- Acceptance harness: 30 consecutive runs with deterministic fault injection
