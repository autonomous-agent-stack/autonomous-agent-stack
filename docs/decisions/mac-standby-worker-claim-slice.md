# mac-standby-worker-claim-slice

## Goal

Add the smallest possible queue + lease scheduler to the existing Python/FastAPI control plane so a standby Mac worker can claim work without executing it yet.

## Scope

This slice includes only:

- `POST /api/v1/workers/{worker_id}/claim`
- minimal SQLite-backed `worker_run_queue`
- minimal SQLite-backed `worker_leases`
- one queue only: `housekeeping`
- focused tests for claim behavior

## Rules

- only registered non-stale workers may claim
- duplicate polling by the same worker returns the same active lease deterministically
- workers do not execute jobs in this slice
- no Telegram changes
- no failback or drainback
- no multi-worker matching heuristics

## Non-goals

- no Telegram ingress refactor
- no daemon execution loop
- no lease adoption or failover protocol
- no TypeScript control plane changes

## Acceptance

- claim succeeds for a valid `mac` worker when queued work exists
- no work returns a deterministic empty claim response
- stale workers cannot claim
- active leases block other workers from taking the same run
- expired leases can be reclaimed

## Status

- implemented:
  - `POST /api/v1/workers/{worker_id}/claim`
  - minimal queue + lease persistence
  - focused tests for happy path, no work, stale worker rejection, active lease blocking, and expired lease reclaim
