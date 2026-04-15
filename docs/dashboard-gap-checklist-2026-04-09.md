# Dashboard Gap Checklist

Date: 2026-04-09

## Positioning

For the current MacBook validation lane, `dashboard/` is a standalone UI prototype.
It is not a monitoring surface and it is not a system-of-record view.

## Confirmed Runtime Facts

- `npm install && npm run dev` starts the app on `http://localhost:3000`
- page routes currently present under `dashboard/app/`:
  - `/`
  - `/agents`
  - `/tests`
  - `/parity`
- these documented API routes currently return `404 Not Found`:
  - `/api/status`
  - `/api/agents`
  - `/api/tests`
  - `/api/parity`
  - `/api/commits`

## Confirmed Drift

The following docs still describe the dashboard as if the API layer exists and is complete:

- `dashboard/README.md`
- `dashboard/PROJECT.md`
- `dashboard/DELIVERY.md`

Current code shape does not match that description:

- `dashboard/app/` contains page routes only
- `dashboard/app/api/` does not exist
- page components still use SWR to fetch the missing `/api/*` endpoints
- the current runtime therefore resolves to error-state behavior instead of real data rendering

## Gap List

1. Route implementation gap
- Missing `app/api/status/route.ts`
- Missing `app/api/agents/route.ts`
- Missing `app/api/tests/route.ts`
- Missing `app/api/parity/route.ts`
- Missing `app/api/commits/route.ts`

2. Documentation drift
- Project-level docs claim the five API routes already exist
- file tree examples still show `app/api/*`
- “completed and usable” language is too strong for the current runtime

3. Runtime behavior gap
- page routes return `200 OK`
- underlying data fetches fail with `404`
- current dashboard should be treated as a prototype shell, not a health source

4. Tooling drift
- Next dev emits metadata warnings for viewport/themeColor exports
- Playwright skill wrapper currently assumes `playwright-cli`, while `@playwright/mcp` exposes `npx @playwright/mcp`

## Non-Goals For This Checklist

- do not promote the dashboard into the main control plane
- do not treat dashboard health as AAS health
- do not add new control-plane APIs just to satisfy the prototype
- do not mix dashboard work with Telegram, webhook, or poller setup

## Minimum Week 2 Follow-Up

1. Reconcile docs with current prototype status
- mark the dashboard as prototype-only until real route handlers exist

2. Decide the next implementation lane
- either add the documented `app/api/*` routes inside the dashboard
- or rewrite the docs to say the prototype uses placeholder/mock data only

3. Keep validation scoped
- continue using `127.0.0.1:8001/health`, `/docs`, and `/panel` as the only mainline acceptance surface

## First Read-Only Wiring Status

The first read-only wiring step is complete at the dashboard-local layer only:

- `dashboard/app/api/status/route.ts`
- `dashboard/app/api/agents/route.ts`
- `dashboard/app/api/tests/route.ts`
- `dashboard/app/api/parity/route.ts`
- `dashboard/app/api/commits/route.ts`

Current behavior after that step:

- `status` and `agents` proxy/map existing control-plane read-only data
- `tests`, `parity`, and `commits` return dashboard-local empty prototype structures instead of `404`
- dashboard pages can render without treating the dashboard as a formal monitoring surface
- only `status` and `agents` require the `127.0.0.1:8001` baseline; the empty prototype routes do not gate on control-plane health
