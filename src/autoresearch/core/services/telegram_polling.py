"""Telegram long-polling daemon for AAS.

Runs alongside the FastAPI app in a background thread. Calls the same
``_handle_telegram_webhook`` logic that the webhook endpoint uses, but
sources updates via ``getUpdates`` long-polling instead.

Enable with environment variables::

    AUTORESEARCH_TELEGRAM_POLLING_ENABLED=true
    AUTORESEARCH_TELEGRAM_PROXY_URL=http://127.0.0.1:7890   # optional
    AUTORESEARCH_TELEGRAM_POLLING_TIMEOUT=30                  # optional
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

import httpx

from autoresearch.api.settings import get_telegram_settings

logger = logging.getLogger(__name__)

# The daemon is a simple thread that loops forever.  It keeps a single
# ``last_offset`` so it only fetches new updates.


class TelegramPollingDaemon:
    def __init__(self) -> None:
        self._last_offset: int = 0
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="tg-polling")
        self._thread.start()
        logger.info("Telegram polling daemon started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
        logger.info("Telegram polling daemon stopped")

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    @property
    def _base_url(self) -> str:
        settings = get_telegram_settings()
        return f"{settings.api_base}/bot{settings.bot_token}"

    def _run(self) -> None:
        settings = get_telegram_settings()
        if not settings.bot_token:
            logger.error("Telegram polling: no bot_token configured, exiting")
            return

        # Delete any existing webhook so polling works.
        proxy = settings.proxy_url or os.getenv("HTTPS_PROXY", "")
        self._delete_webhook(proxy=proxy)

        proxy = settings.proxy_url or os.getenv("HTTPS_PROXY", "")
        logger.info("Telegram polling: proxy=%s timeout=%ds", proxy or "none", settings.polling_timeout)

        while not self._stop_event.is_set():
            try:
                updates = self._poll(timeout=settings.polling_timeout, proxy=proxy)
            except Exception:
                logger.exception("Telegram polling error, retrying in 5s")
                self._stop_event.wait(5)
                continue

            for update in updates:
                self._dispatch(update)
                self._last_offset = update.get("update_id", self._last_offset) + 1

    def _delete_webhook(self, proxy: str = "") -> None:
        try:
            kwargs: dict[str, Any] = {"params": {"drop_pending_updates": False}, "timeout": 15}
            if proxy:
                kwargs["proxy"] = proxy
            resp = httpx.post(f"{self._base_url}/deleteWebhook", **kwargs)
            data = resp.json()
            if data.get("ok"):
                logger.info("Telegram polling: deleted existing webhook")
            else:
                logger.warning("Telegram polling: deleteWebhook returned %s", data)
        except Exception:
            logger.exception("Telegram polling: failed to delete webhook")

    def _poll(self, *, timeout: int, proxy: str) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "timeout": timeout,
            "limit": 10,
            "offset": self._last_offset,
        }
        kwargs: dict[str, Any] = {"params": params, "timeout": timeout + 15}
        if proxy:
            kwargs["proxy"] = proxy

        resp = httpx.get(f"{self._base_url}/getUpdates", **kwargs)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("ok"):
            logger.error("Telegram polling: getUpdates error: %s", data)
            return []
        return data.get("result", [])

    def _dispatch(self, update: dict[str, Any]) -> None:
        """Forward an update to the local FastAPI webhook handler."""
        try:
            import httpx as _httpx

            from autoresearch.api.settings import get_runtime_settings

            settings = get_telegram_settings()
            headers: dict[str, str] = {"content-type": "application/json"}
            if settings.secret_token:
                headers["x-telegram-bot-api-secret-token"] = settings.secret_token

            port = get_runtime_settings().api_port
            host = get_runtime_settings().api_host
            resp = _httpx.post(
                f"http://{host}:{port}/api/v1/gateway/telegram/webhook",
                json=update,
                headers=headers,
                timeout=30,
            )
            logger.info("Telegram polling: dispatched update_id=%s -> %s", update.get("update_id"), resp.status_code)
        except Exception:
            logger.exception("Telegram polling: dispatch failed for update %s", update.get("update_id"))
