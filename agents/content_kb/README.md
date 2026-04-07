# Content KB Agent

Subtitle ingestion, topic classification, knowledge base indexing, and README maintenance.

## Architecture

One agent, two profiles (`lisa_content`, `dd_content`). Same taxonomy, different owners.

```
subtitle.srt → parse → classify topic → select repo/dir → write normalized content
                                                     → generate metadata.json + summary.md + tags
                                                     → update topics.json, speakers.json, timeline.json
                                                     → update README.md
```

## Topic Taxonomy

- `ai-status-and-outlook`
- `vibe-coding`
- `entertainment-standup`
- `film-tv-recommendation`
- `economy`
- `worldview`
- `wellness`

## Repo Layout

Each owner has one `knowledge-base` repo:

```
knowledge-base/
  subtitles/
    <topic>/
      <slug>/
        content.txt
        metadata.json
        summary.md
  indexes/
    topics.json
    speakers.json
    timeline.json
  digests/
    weekly/
    monthly/
  README.md
```

## API

- `POST /api/jobs/content-kb/choose-repo` — select target repo
- `POST /api/jobs/content-kb/ingest` — full ingestion pipeline

## Design Principles

1. LLM does classification, summarization, tagging — not content rewriting
2. Original subtitle text is preserved verbatim in `content.txt`
3. All indexes are append-only (no deletions without explicit approval)
4. Each profile runs under its own GitHub credentials
