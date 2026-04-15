# MacBook Codex Week 1 Validation

Date: 2026-04-09

## Scope

This report records the Week 1 MacBook execution plan as validation work only.
The MacBook remains an experiment and verification node. It is not promoted to a
formal control-plane host, Telegram ingress node, or release surface.

## Mainline Baseline

Validated on `127.0.0.1:8001` using the repo mainline flow:

```bash
make setup
make doctor
make start
```

Observed results:

- `http://127.0.0.1:8001/health` returned `{"status":"ok"}`
- `http://127.0.0.1:8001/docs` returned `200 OK`
- `http://127.0.0.1:8001/panel` redirected to `/panel/` and resolved to `200 OK`

Notes:

- `make doctor` completed with `Result: READY`
- dev-mode warning remained for `AUTORESEARCH_TELEGRAM_SECRET_TOKEN`
- `make setup` completed but pip reported resolver conflicts in the virtualenv:
  - `semgrep` expects `jsonschema~=4.25.1`
  - `semgrep` expects `mcp==1.23.3`
  - `opentelemetry-proto` expects `protobuf<7.0`

## Dashboard Audit

The dashboard was run as a standalone prototype on `http://localhost:3000`:

```bash
cd dashboard
npm install
npm run dev
```

Confirmed behavior:

- `/`, `/agents`, `/tests`, and `/parity` all served `200 OK`
- documented API endpoints returned `404 Not Found`:
  - `/api/status`
  - `/api/agents`
  - `/api/tests`
  - `/api/parity`
  - `/api/commits`
- current code under `dashboard/app/` has page routes only and no `app/api/*` implementation

Impact:

- this dashboard is a UI prototype only for this week
- it is not a monitoring surface
- it is not a system-of-record view
- page code still fetches `/api/*` endpoints via SWR, so the current runtime falls into the error state path when those requests fail

Primary drift sources observed:

- `dashboard/README.md`
- `dashboard/PROJECT.md`
- `dashboard/DELIVERY.md`

Those files still describe five working `/api/*` endpoints that are not present in the current app tree.

## OpenClaw Migration Smoke

The migration smoke was executed with explicit `8001` override:

```bash
BASE_URL=http://127.0.0.1:8001 bash migration/openclaw/scripts/verify-migration.sh
```

Observed results:

- API health passed against `8001`
- OpenClaw compat session creation passed
- event append passed
- agent enqueue passed
- skill smoke passed

Preflight warnings:

- `claude` missing
- `docker` missing

Those warnings did not block the local compat and skill smoke executed here.

### Discovery Script

`migration/openclaw/scripts/discover-openclaw-data.sh` originally exited early when
legacy locations were missing or inaccessible under `set -euo pipefail`.

It was adjusted to continue reporting candidates and missing directories instead of
aborting the discovery pass. After the change, the script reported:

- missing `/Volumes/PS1008/Github/openclaw-memory`
- missing `/Volumes/PS1008/Github/openclaw`

## Mac Worker Smoke

This section is limited to the constrained standby flow only:

- `noop`
- `cleanup_appledouble` with `dry_run=true`

Explicitly out of scope:

- YouTube actions
- YouTube autoflow
- Telegram thin ingress
- poller or webhook setup

Worker base URL remained `http://127.0.0.1:8001`.

Observed results:

- standby worker registered successfully
- `noop` run completed on worker `mac-zhuangzhus-MacBook-Air`
- `cleanup_appledouble` dry-run completed on worker `mac-zhuangzhus-MacBook-Air`
- dry-run result recorded `deleted_count=3`
- the lease for the cleanup run transitioned back to inactive after completion

Representative dry-run findings seen in worker logs:

- `/Volumes/AI_LAB/Github/.DS_Store`
- `/Volumes/AI_LAB/Github/claude_cli/.DS_Store`
- `/Volumes/AI_LAB/Github/claude_cli-private/vendor/.DS_Store`

## Outcome

Week 1 validation passed within the planned scope:

- `8001` mainline is usable
- dashboard runs as a prototype and its documentation drift is confirmed
- OpenClaw compat smoke works when explicitly pinned to `BASE_URL=http://127.0.0.1:8001`
- constrained Mac standby worker smoke works for `noop` and `cleanup_appledouble` dry-run

No production role expansion was performed for this MacBook.
