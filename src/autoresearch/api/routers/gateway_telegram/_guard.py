from __future__ import annotations

import threading
import time
from typing import Any

from fastapi import HTTPException, Request, status

from autoresearch.api.settings import load_runtime_settings, load_telegram_settings
from autoresearch.core.services.telegram_webhook_dedup import claim_first_telegram_update

from ._extract import _safe_int, _safe_str

_RATE_WINDOW_SECONDS = 60
_RATE_MAX_REQUESTS_PER_CHAT = 30
_CHAT_RATE_WINDOWS: dict[str, list[float]] = {}
_GUARD_LOCK = threading.Lock()


def _validate_secret_token(raw_request: Request) -> None:
    expected = (load_telegram_settings().secret_token or "").strip()
    if _is_production_env() and not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="telegram secret token is required in production",
        )
    if not expected:
        return
    provided = raw_request.headers.get("x-telegram-bot-api-secret-token", "").strip()
    if provided != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid telegram secret token")


def _is_production_env() -> bool:
    return load_runtime_settings().is_production


def _guard_webhook_replay_and_rate(update: dict[str, Any]) -> None:
    update_id = _safe_int(update.get("update_id"))
    if update_id is None:
        return
    message = update.get("message") or update.get("edited_message") or {}
    chat_id = _safe_str((message.get("chat") or {}).get("id"))
    now_ts = time.time()

    with _GUARD_LOCK:
        _gc_guard_state(now_ts)
        try:
            if not claim_first_telegram_update(load_runtime_settings().api_db_path, int(update_id)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="duplicate telegram update rejected",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="telegram update dedup store unavailable",
            ) from exc

        if not chat_id:
            return
        window = _CHAT_RATE_WINDOWS.setdefault(chat_id, [])
        window_start = now_ts - _RATE_WINDOW_SECONDS
        window[:] = [ts for ts in window if ts >= window_start]
        if len(window) >= _RATE_MAX_REQUESTS_PER_CHAT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="telegram webhook rate limit exceeded",
            )
        window.append(now_ts)


def _gc_guard_state(now_ts: float) -> None:
    empty_chats: list[str] = []
    rate_cutoff = now_ts - _RATE_WINDOW_SECONDS
    for chat_id, timestamps in _CHAT_RATE_WINDOWS.items():
        timestamps[:] = [ts for ts in timestamps if ts >= rate_cutoff]
        if not timestamps:
            empty_chats.append(chat_id)
    for chat_id in empty_chats:
        _CHAT_RATE_WINDOWS.pop(chat_id, None)
