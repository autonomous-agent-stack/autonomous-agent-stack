# Offline Demo Guide

## Quick Start

```bash
# Run the offline demo (no real workers needed)
PYTHONPATH=src python scripts/demo_offline.py

# Run all contract + console + fixture tests
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
  -q
```

## What's Included

### Demo Runner (`scripts/demo_offline.py`)
Five scenarios that exercise the full control-plane lifecycle:

1. **Success Flow**: queued → leased → running → succeeded (gate accepts)
2. **Failure Flow**: queued → leased → running → failed (gate recommends retry)
3. **Review Flow**: queued → leased → running → needs_review (human approves)
4. **Rejection Flow**: overreach detected → gate rejects
5. **Retry Exhaustion**: retries exhausted → auto-upgrade to fallback agent

### Fake Worker Adapters (`src/autoresearch/testing/fake_workers.py`)
- `FakeLinuxWorker` — configurable outcomes (success/timeout/crash/needs_review/permission_denied)
- `FakeWinYingdaoWorker` — form fill and flow execution simulation
- `HeartbeatSimulation` — heartbeat age → worker status derivation
- `LeaseManager` — lease acquisition, release, and timeout detection
- `FAILURE_TAXONOMY` — 10 failure scenarios across 10 categories

### Console Endpoints
All endpoints use mock data, no real connections:

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/console/tasks` | List tasks (filter by status, priority) |
| `GET /api/v1/console/workers` | List workers with status/heartbeat/metrics |
| `GET /api/v1/console/runs/{id}` | Run detail with logs, artifacts, gate verdict |
| `GET /api/v1/console/approvals` | Pending approval queue |
| `POST /api/v1/console/approvals/{id}/approve` | Approve a task |
| `POST /api/v1/console/approvals/{id}/reject` | Reject a task |
| `POST /api/v1/console/approvals/{id}/retry` | Retry a failed task |
| `POST /api/v1/console/approvals/{id}/fallback` | Fallback to secondary agent |
| `GET /api/v1/console/` | HTML landing page with tables and filters |

### Test Coverage
- **413 tests** across unified contracts, console, and simulation fixtures
- Illegal state transition matrix (every invalid pair tested)
- Five gate scenario tests (success, timeout, overreach, missing artifacts, human confirm)
- Retry/fallback/needs_review rule boundary tests
- Failure taxonomy coverage (10 categories, retryable vs non-retryable)
