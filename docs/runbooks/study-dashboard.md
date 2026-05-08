# Study Dashboard

The Study Dashboard is the iPad-friendly study surface for AAS. It turns saved
technical sources into a daily GoodNotes PDF, a MarginNote4 deep-reading package,
and durable review items in the control plane.

## Surfaces

- PWA: `http://127.0.0.1:3000/study`
- API state: `http://127.0.0.1:8001/api/v1/study-dashboard/state`
- Manual refresh: `POST /api/v1/study-dashboard/refresh`
- Daily brief: `POST /api/v1/study-dashboard/briefs/daily`
- Export: `POST /api/v1/study-dashboard/briefs/{brief_id}/export`

## Sources

Configure only the sources you want. Missing credentials show as disconnected
and do not block local project topics.

```bash
export AUTORESEARCH_STUDY_DASHBOARD_X_USER_ID="123456"
export AUTORESEARCH_STUDY_DASHBOARD_X_BEARER_TOKEN="..."
export AUTORESEARCH_STUDY_DASHBOARD_YOUTUBE_API_KEY="..."
export AUTORESEARCH_STUDY_DASHBOARD_YOUTUBE_PLAYLIST_ID="PL..."
export AUTORESEARCH_STUDY_DASHBOARD_RSS_URLS="https://example.com/feed.xml,https://example.org/rss"
export AUTORESEARCH_STUDY_DASHBOARD_DAILY_HOUR=8
export AUTORESEARCH_STUDY_DASHBOARD_DAILY_TIMEZONE="Asia/Taipei"
```

Use a dedicated YouTube playlist for deep technical videos. The dashboard action
for a YouTube item queues the existing `youtube_autoflow` worker so transcripts,
digests, and knowledge-base publishing stay on the governed worker path.

## iPad Study Flow

1. Open `/study` from iPad Safari and add it to the Home Screen.
2. Tap refresh to update X bookmarks, the dedicated YouTube playlist, RSS, and local topics.
3. Tap the daily brief action to generate and export a GoodNotes-ready PDF.
4. Export the same brief to MarginNote4 to receive the PDF plus Markdown sidecar.
5. After annotation, export GoodNotes or MarginNote4 notes back into the configured inbox folders and run `study_ingest`.

## Storage

- Study Dashboard items and briefs are stored in the API SQLite database.
- PDF and Markdown artifacts are written under the API artifact directory.
- GoodNotes and MarginNote4 inbox paths are still provided by Study Workbench settings.
- Obsidian/Git remains the durable knowledge source after review ingestion.
