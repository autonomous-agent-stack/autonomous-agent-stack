# mac-standby-worker-v1

## Goal

Add the minimum worker-control-plane loop to the existing Python/FastAPI app, then attach a standby Mac worker.

## Current Truth

- main control plane is Python/FastAPI
- initial `/api/v1/workers` slice exists for `register` and `heartbeat`
- do not touch Telegram ingress in v1
- reuse existing shared status models where possible
- worker type should remain `mac` in v1
- claim / lease / scheduler are not part of this slice

## Scope

v1 includes only:

- `workers/register`
- `workers/heartbeat`
- SQLite-backed worker registry
- focused tests

## Non-goals

- no Telegram queue refactor
- no multi-agent orchestration
- no TypeScript control plane adoption
- no new worker type enum explosion

## Acceptance

- a Mac worker can register with `mode=standby`
- heartbeat updates liveness
- tests cover happy path and stale worker detection

## Status

- implemented:
  - `POST /api/v1/workers/register`
  - `POST /api/v1/workers/{worker_id}/heartbeat`
  - SQLite-backed worker registry
  - focused tests for register, duplicate registration, heartbeat, and stale detection
- follow-up claim / queue / lease work is tracked in `docs/decisions/mac-standby-worker-claim-slice.md`
