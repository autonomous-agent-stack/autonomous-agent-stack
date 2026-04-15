# mac-standby-worker-runtime-v1

## Goal

Make the existing Python/FastAPI control plane runnable end-to-end with a standby Mac worker:

1. enqueue a housekeeping run
2. let a `mac` standby worker claim it
3. execute a constrained local task
4. report `running` and terminal status back to the control plane

## Scope

This runtime package includes:

- `POST /api/v1/worker-runs`
- `POST /api/v1/workers/{worker_id}/runs/{run_id}/report`
- `src/autoresearch/workers/mac/`
  - `config.py`
  - `client.py`
  - `executor.py`
  - `daemon.py`
- `scripts/start-mac-worker.sh`
- focused tests for report lifecycle and daemon end-to-end behavior
- a repo-local smoke runbook

## Fixed v1 Decisions

- keep `worker_type="mac"`
- keep `mode="standby"`
- keep `role="housekeeper"`
- keep queue scope to `housekeeping`
- one daemon processes one run at a time
- reuse existing `JobStatus` values
- represent "claimed but not started" via active lease + assigned worker, not a new status enum
- support only:
  - `noop`
  - `cleanup_appledouble`
  - `cleanup_tmp`
  - `youtube_action` as a manual fail-closed bridge into the existing YouTube bounded context

## Non-goals

- no Telegram ingress changes
- no failback or drainback
- no multi-agent orchestration
- no TypeScript control plane changes
- no worker pool or concurrent execution
- no remote shell style executor
- no autonomous YouTube monitoring
- no duplicated YouTube state in standby

## Acceptance

- enqueue -> claim -> execute -> report works end-to-end
- run reporting supports `running`, `completed`, `failed`, and accepts `succeeded` as an input alias
- terminal reports deactivate the active lease
- the Mac worker can dry-run `cleanup_appledouble`
- focused tests cover API lifecycle and daemon behavior

## Status

- implemented:
  - enqueue API on the Python control plane
  - run reporting API on the Python control plane
  - `mac` standby daemon with register / heartbeat / claim loop
  - local executor for `noop`, `cleanup_appledouble`, `cleanup_tmp`
  - startup script and smoke runbook
- still intentionally deferred:
  - Telegram fallback
  - failback / drainback
  - queue prioritization
  - concurrent execution
  - cron / scheduled YouTube polling
