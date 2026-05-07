# Entertainment Curator

Telegram-only bounded service for AAS entertainment planning.

It generates structured JSON recommendations from mood, time, interests, focus level, and company. The default path works without account access. Optional YouTube OAuth profiles are read-only and do not log in to YouTube Music or NotebookLM web sessions.

## Accounts

- `youtube_music`: YouTube Premium/Music profile for music, relaxation, and companion plans.
- `youtube_learning`: YouTube + NotebookLM profile for learning, AI, business, documentary, and source organization plans.
- NotebookLM is used as a manual study workflow: the service suggests sources to collect, questions to ask, and an organization path.

Both YouTube profiles use the same Google OAuth Client but store separate local refresh tokens. The only allowed scope is:

```text
https://www.googleapis.com/auth/youtube.readonly
```

## Telegram Auth Commands

```text
/youtube-auth youtube_music
/youtube-auth youtube_learning
/youtube-auth-status
/youtube-auth-revoke youtube_music
```

Set the OAuth client credentials locally, outside git:

```text
AUTORESEARCH_GOOGLE_OAUTH_CLIENT_ID=...
AUTORESEARCH_GOOGLE_OAUTH_CLIENT_SECRET=...
AUTORESEARCH_YOUTUBE_OAUTH_REDIRECT_URI=http://127.0.0.1:8001/api/v1/auth/youtube/oauth/callback
```

Tokens are stored under `~/.config/autoresearch/google/youtube_profiles/` by default and are never returned to Telegram.

## Copyright Boundary

The service only recommends legal, official, public, free, or normal paid-account entitlements. It must not generate piracy, cracking, or paid-platform bypass advice. YouTube Music recommendations use official YouTube data only; NotebookLM remains a manual import and organization workflow.

## Local Use

```python
from packages.entertainment_curator.service import EntertainmentCuratorTelegramService

service = EntertainmentCuratorTelegramService()
result = service.handle_telegram_message("今晚 1小时 想听音乐放松")
```

The AAS integration is intentionally Telegram-only. Control Plane records the task, then executes it as a local immediate result without worker queue dispatch.
