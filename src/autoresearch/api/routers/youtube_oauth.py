from __future__ import annotations

from html import escape
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from autoresearch.api.dependencies import get_youtube_oauth_service


router = APIRouter(prefix="/api/v1/auth/youtube", tags=["auth", "youtube"])


@router.get("/profiles")
def list_youtube_oauth_profiles(
    oauth_service: Any = Depends(get_youtube_oauth_service),
) -> dict[str, Any]:
    return {"profiles": oauth_service.list_profiles()}


@router.get("/oauth/callback", response_class=HTMLResponse)
def youtube_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    profile: str | None = Query(default=None),
    oauth_service: Any = Depends(get_youtube_oauth_service),
) -> HTMLResponse:
    result = oauth_service.complete_authorization(
        code=code,
        state=state,
        error=error,
        expected_profile_id=profile,
    )
    status = str(result.get("status") or "")
    profile_id = str(result.get("profile_id") or "-")
    reason = str(result.get("reason") or "")
    title = "YouTube OAuth Authorized" if status == "authorized" else "YouTube OAuth Needs Attention"
    body = [
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>YouTube OAuth</title></head>",
        "<body style=\"font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;line-height:1.5;margin:32px;\">",
        f"<h1>{escape(title)}</h1>",
        f"<p>profile: <code>{escape(profile_id)}</code></p>",
        f"<p>status: <code>{escape(status)}</code></p>",
    ]
    if reason:
        body.append(f"<p>reason: {escape(reason)}</p>")
    body.append("<p>You can close this browser tab and return to Telegram.</p>")
    body.append("</body></html>")
    return HTMLResponse("\n".join(body), status_code=200)
