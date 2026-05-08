# Life Companion Personal Package

`personal.life_companion` is the optional personal learning and entertainment operating layer for AAS. It depends on `personal.study_workspace` and `personal.entertainment_curator`.

## Enable

```bash
AUTORESEARCH_ENABLED_PERSONAL_PACKAGES=personal.study_workspace,personal.entertainment_curator,personal.life_companion
```

The package is disabled by default in both minimal and full modes.

## What It Does

- Builds a unified personal content graph for study items, notes, cards, recommendations, feedback, daily plans, exports, and activity events.
- Generates rows inspired by mature reader, review, and recommender products: continue learning, deep study, review queue, entertainment DJ, and export next.
- Creates daily study and entertainment plans with study blocks, review blocks, reward blocks, and automatic export.
- Generates GoodNotes PDFs and card CSV files, plus MarginNote4 PDFs and Markdown sidecars with stable `item_id`, `plan_id`, and `card_id` backlinks.
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

## Telegram

The package handles `/personal`, `/today`, `/for-you`, `/review`, `/cards`, `/dj`, `/reward`, `/export`, `/promote`, and `/feedback` directly. Disabled or missing-dependency commands return a package result and do not create a control-plane task or worker run.

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
