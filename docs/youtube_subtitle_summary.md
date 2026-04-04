# YouTube Subtitle Summary

## Usage

- The Telegram gateway routes a message to `youtube_subtitle_summary` only when it contains a YouTube URL and an explicit summary intent.
- The special agent first reuses the PR #33 subtitle pipeline, then produces a deterministic extractive summary from the cleaned subtitle text.

Example:

```text
请总结这个 YouTube 视频 https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

## Failure Behavior

- If subtitle fetching fails, the agent returns a fail-closed result.
- It does not guess video content.
- It does not silently fall back to a generic webpage summary.
- Supported failure kinds include `rate_limited`, `network_ssl`, `no_subtitle_output`, and `unknown_download_error`.

## Handoff Notes

- Reuse `src/subtitle_offline/*` and `src/autoresearch/core/services/media_jobs_subtitle.py` as the subtitle base.
- Keep routing explicit in `src/autoresearch/api/routers/gateway_telegram.py`.
- Do not move this logic into `claude_agents.py`.
- The current scope is YouTube only.
