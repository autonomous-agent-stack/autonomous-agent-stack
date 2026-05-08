# Study Workbench Sync MVP

This runbook wires iPad study apps into AAS without treating them as the source
of truth. Obsidian and Git keep the durable knowledge record; GoodNotes is the
handwriting workbench; MarginNote4 is the close-reading workbench; AAS prepares
and recovers files in the background.

## Shape

Study Workbench Sync is part of the optional `personal.study_workspace` package. Enable it before startup:

```bash
export AUTORESEARCH_ENABLED_PERSONAL_PACKAGES="personal.study_workspace"
```

The MVP uses three worker task types on the existing Mac standby worker:

- `study_prepare`: read an Obsidian study item or explicit Markdown, render a
  minimal PDF, and copy it into GoodNotes / MarginNote inbox folders.
- `study_ingest`: scan GoodNotes backup and MarginNote export folders, dedupe
  by fingerprint, clean text-like exports, and write Markdown into Obsidian
  `inbox_review/YYYY-MM-DD/`.
- `study_git_sync`: commit only the generated review inbox files in the
  configured Obsidian Git repository.

There is no new daemon. Scheduling still uses `/api/v1/worker-schedules`, and
execution still uses the existing worker queue / claim / report loop.

## Configuration

Set the paths for your local bridge folders:

```bash
export AUTORESEARCH_STUDY_OBSIDIAN_VAULT_DIR="$HOME/Obsidian/MainVault"
export AUTORESEARCH_STUDY_GOODNOTES_INBOX_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AAS/GoodNotes-Inbox"
export AUTORESEARCH_STUDY_GOODNOTES_BACKUP_DIRS="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AAS/GoodNotes-Backup"
export AUTORESEARCH_STUDY_MARGINNOTE_INBOX_DIR="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AAS/MarginNote-Inbox"
export AUTORESEARCH_STUDY_MARGINNOTE_EXPORT_DIRS="$HOME/Library/Mobile Documents/com~apple~CloudDocs/AAS/MarginNote-Export"
export AUTORESEARCH_STUDY_GIT_REPO_DIR="$HOME/Obsidian/MainVault"
export AUTORESEARCH_STUDY_REVIEW_INBOX_RELATIVE_DIR="inbox_review"
export AUTORESEARCH_STUDY_GIT_PUSH_ENABLED=false
```

Optional OCR hook:

```bash
export AUTORESEARCH_STUDY_OCR_COMMAND="your-ocr-command"
```

If OCR is not configured or unavailable, pure handwritten PDFs are reported as
degraded instead of being silently treated as successful OCR.

## Manual Smoke

Start the API and Mac worker as usual:

```bash
make start
./scripts/start-mac-worker.sh
```

Check readiness:

```bash
curl http://127.0.0.1:8001/api/v1/study-workbench/health
```

Prepare one note for iPad study:

```bash
curl -X POST http://127.0.0.1:8001/api/v1/study-workbench/prepare \
  -H 'Content-Type: application/json' \
  -d '{
    "title": "Transformer Self Attention",
    "markdown_text": "# Transformer Self Attention\n\nQ/K/V and multi-head attention notes.",
    "targets": ["goodnotes", "marginnote"],
    "requested_by": "runbook"
  }'
```

Ingest exported study notes:

```bash
curl -X POST http://127.0.0.1:8001/api/v1/study-workbench/ingest \
  -H 'Content-Type: application/json' \
  -d '{"requested_by": "runbook"}'
```

`study_ingest` automatically enqueues `study_git_sync` when it writes review
notes. By default the git task creates a local commit only; it does not push.

## Boundaries

- GoodNotes and MarginNote4 still require the iPad-side import/open action.
- AAS prepares inbox files and recovers exports; it does not claim full app
  automation.
- `study_git_sync` only commits files under the configured review inbox.
- Push is disabled unless `AUTORESEARCH_STUDY_GIT_PUSH_ENABLED=true`.
