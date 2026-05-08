# Life Companion Personal Package

`personal.life_companion` is the optional personal learning and entertainment operating layer for AAS. It depends on `personal.study_workspace` and `personal.entertainment_curator`.

## Enable

```bash
AUTORESEARCH_ENABLED_PERSONAL_PACKAGES=personal.study_workspace,personal.entertainment_curator,personal.life_companion
```

The package is disabled by default in both minimal and full modes.

Remote `/study` access is also disabled by default. To issue short-lived personal console links:

```bash
AUTORESEARCH_PERSONAL_REMOTE_ENABLED=true
AUTORESEARCH_PANEL_JWT_SECRET=change-me
AUTORESEARCH_PERSONAL_REMOTE_BASE_URL=http://127.0.0.1:3000/study
```

## What It Does

- Builds a unified personal content graph for study items, highlights, notes, cards, reviews, recommendations, feedback, daily plans, exports, source accounts, and activity events.
- Indexes object-style nodes, blocks, explicit backlinks, unlinked mentions, stable `item_id` / `card_id` / `plan_id` references, tags, and saved canvas layouts.
- Composes an AI-arranged interface instead of a fixed-only dashboard. The layout planner can choose Today Home, filtered views, object dashboards, graph, canvas, portals, review queue, entertainment DJ, export status, blind spots, deduped hot feed, tracking, and boredom-scroll panels.
- Surfaces knowledge blind spots and anti-filter-bubble exploration by looking for weak backlinks, missing cards, missing reviews, unlinked mentions, and orphan objects.
- Dedupes hot items across available sources by URL/title/topic clusters, downranks already-seen material, and lets followed topics rise again when they have new signal.
- Generates rows inspired by mature reader, review, and recommender products: continue learning, deep study, review queue, entertainment DJ, and export next.
- Creates daily study and entertainment plans with study blocks, review blocks, reward blocks, and automatic export.
- Generates GoodNotes PDFs and card CSV files, plus MarginNote4 PDFs and Markdown sidecars with stable `item_id`, `plan_id`, and `card_id` backlinks, source pins, and graph seeds.
- Scans configured GoodNotes backup and MarginNote export folders to backfill notes and trace exported study records.

## API

- `GET /api/v1/personal/state`
- `POST /api/v1/personal/ingest`
- `POST /api/v1/personal/recommendations`
- `POST /api/v1/personal/plans/daily`
- `POST /api/v1/personal/reviews`
- `POST /api/v1/personal/cards`
- `POST /api/v1/personal/entertainment/session`
- `POST /api/v1/personal/exports`
- `POST /api/v1/personal/feedback`
- `POST /api/v1/personal/promote`
- `GET /api/v1/personal/search?q=...`
- `POST /api/v1/personal/access/magic-link`
- `GET /api/v1/personal/access/verify`
- `GET /api/v1/personal/nodes`
- `GET /api/v1/personal/nodes/{node_id}`
- `GET /api/v1/personal/nodes/{node_id}/backlinks`
- `GET /api/v1/personal/links`
- `POST /api/v1/personal/links`
- `DELETE /api/v1/personal/links/{link_id}`
- `GET /api/v1/personal/mentions`
- `POST /api/v1/personal/mentions/{mention_id}/promote`
- `GET /api/v1/personal/graph`
- `GET /api/v1/personal/canvas`
- `POST /api/v1/personal/canvas`
- `POST /api/v1/personal/layout`

## Telegram

The package handles `/life`, `/open-study`, `/personal`, `/today`, `/for-you`, `/review`, `/cards`, `/dj`, `/reward`, `/export`, `/promote`, and `/feedback` directly. Disabled, remote-disabled, or missing-dependency commands return a package result and do not create a control-plane task or worker run.

`/life` and `/open-study` return a tokenized `/study` link only when `AUTORESEARCH_PERSONAL_REMOTE_ENABLED=true` and panel signing is configured.

## Attention Policy

- Interrupt only for due reviews, tracked high-signal deltas, failed exports, or explicit user asks.
- Keep non-urgent hot clusters in a low-pressure feed for idle browsing.
- Reduce repeat exposure after `done` or negative feedback unless the target is explicitly followed with `saved` or `more_like_this`.
- Preserve anti-bubble space by always surfacing blind spots and weakly connected objects.

## Export Setup

Use the existing study workbench paths:

```bash
AUTORESEARCH_STUDY_GOODNOTES_INBOX_DIR=/path/to/GoodNotes-Inbox
AUTORESEARCH_STUDY_GOODNOTES_BACKUP_DIRS=/path/to/GoodNotes-Backup
AUTORESEARCH_STUDY_MARGINNOTE_INBOX_DIR=/path/to/MarginNote-Inbox
AUTORESEARCH_STUDY_MARGINNOTE_EXPORT_DIRS=/path/to/MarginNote-Export
```

The package writes files to the configured inbox folders and tracks export status as `prepared`, `copied`, `awaiting_import`, `imported`, `backfilled`, or `failed`.

## Boundaries

The package stores metadata, notes, summaries, highlights, cards, export files, local paths, and official/source URLs. It does not store protected media files or write into GoodNotes or MarginNote private databases.
