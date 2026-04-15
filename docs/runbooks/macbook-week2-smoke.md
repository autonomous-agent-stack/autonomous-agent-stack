# MacBook Week 2 Smoke

This runbook freezes the validated MacBook smoke lane to a local-only, low-risk flow:

- API on `127.0.0.1:8001`
- Mac standby worker
- `noop`
- `cleanup_appledouble` with `dry_run=true`

Out of scope:

- YouTube actions
- YouTube autoflow
- Telegram webhook ingress
- cloudflared
- pollers
- production promotion

## One-command path

```bash
scripts/macbook-week2-smoke.sh
```

Useful overrides:

```bash
PORT=8001 \
CLEANUP_ROOT=/Volumes/AI_LAB/Github \
WORKER_ID=macbook-week2 \
scripts/macbook-week2-smoke.sh
```

## Expected outcome

- API health passes on `http://127.0.0.1:8001/health`
- worker registers against the same control plane
- `noop` finishes as `completed`
- `cleanup_appledouble` finishes as `completed`
- SQLite shows inactive lease after each terminal run

## Dry-run result caveat

The current persisted result still uses `result.deleted_count`.
When `dry_run=true`, interpret that number as:

- candidate count
- or “would delete” count

Do not interpret it as confirmed deletion.
