from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib import error, request

from autoresearch.shared.models import PanelAuditLogRead


logger = logging.getLogger(__name__)


class TelegramNotifierService:
    """Thin Telegram Bot API client for operational notifications."""

    def __init__(
        self,
        *,
        bot_token: str | None,
        api_base: str = "https://api.telegram.org",
        timeout_seconds: float = 10.0,
        max_attempts: int = 2,
    ) -> None:
        self._bot_token = (bot_token or "").strip()
        self._api_base = api_base.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_attempts = max(1, max_attempts)

    @property
    def enabled(self) -> bool:
        return bool(self._bot_token)

    def send_message(
        self,
        *,
        chat_id: str,
        text: str,
        disable_web_page_preview: bool = True,
        reply_markup: dict[str, Any] | None = None,
        message_thread_id: int | None = None,
        reply_to_message_id: int | None = None,
    ) -> bool:
        if not self.enabled:
            return False

        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        endpoint = f"{self._api_base}/bot{self._bot_token}/sendMessage"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )
        return self._send_request(
            req=req,
            operation="sendMessage",
            chat_id=str(chat_id),
        )

    def notify_manual_action(
        self,
        *,
        chat_id: str,
        entry: PanelAuditLogRead,
        run_status: str,
    ) -> bool:
        return self.send_message(
            chat_id=chat_id,
            text=self._format_manual_action_message(entry=entry, run_status=run_status),
        )

    def _format_manual_action_message(self, *, entry: PanelAuditLogRead, run_status: str) -> str:
        reason = (entry.reason or "").strip() or "-"
        return (
            "[审计] Web 面板手动操作\n"
            f"- action: {entry.action}\n"
            f"- target: {entry.target_id}\n"
            f"- status: {entry.status}\n"
            f"- run_status: {run_status}\n"
            f"- reason: {reason}\n"
            f"- at: {entry.created_at.isoformat()}"
        )

    def notify_status_magic_link(
        self,
        *,
        chat_id: str,
        summary_lines: list[str],
        magic_link_url: str | None,
        expires_at_iso: str | None,
        is_group_link: bool = False,
        mini_app_url: str | None = None,
        message_thread_id: int | None = None,
    ) -> bool:
        """Send status notification with magic link.

        Args:
            chat_id: Telegram chat ID
            summary_lines: Status summary lines
            magic_link_url: Magic link URL
            expires_at_iso: Link expiration time
            is_group_link: Whether this is a group-scoped link (use Inline Button)
            mini_app_url: Optional Telegram Mini App URL for 1:1 chats

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        # For group links, use Inline Button
        if is_group_link and magic_link_url:
            return self._send_group_magic_link(
                chat_id=chat_id,
                magic_link_url=magic_link_url,
                expires_at_iso=expires_at_iso,
                message_thread_id=message_thread_id,
            )

        # For regular links, use text message (with optional Mini App button)
        lines = ["[状态查询]", *summary_lines]
        if magic_link_url:
            lines.append("")
            lines.append(f"Web 面板: {magic_link_url}")
            if expires_at_iso:
                lines.append(f"链接有效期至(UTC): {expires_at_iso}")

        reply_markup: dict[str, Any] | None = None
        if mini_app_url:
            reply_markup = {
                "inline_keyboard": [
                    [
                        {
                            "text": "打开面板（Mini App）",
                            "web_app": {"url": mini_app_url},
                        }
                    ]
                ]
            }
        return self.send_message(chat_id=chat_id, text="\n".join(lines), reply_markup=reply_markup, message_thread_id=message_thread_id)

    def _send_group_magic_link(
        self,
        *,
        chat_id: str,
        magic_link_url: str,
        expires_at_iso: str | None,
        message_thread_id: int | None = None,
    ) -> bool:
        """Send magic link with Inline Button for group chats.

        Args:
            chat_id: Telegram chat ID
            magic_link_url: Magic link URL
            expires_at_iso: Link expiration time

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False

        # Build Inline Keyboard
        inline_keyboard = {
            "inline_keyboard": [
                [
                    {
                        "text": "📊 查看工作看板",
                        "url": magic_link_url,
                    }
                ]
            ]
        }

        # Build message payload
        text = "✅ 您的专属工作看板已就绪"
        if expires_at_iso:
            text += f"\n\n⏰ 链接有效期至: {expires_at_iso}"

        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": inline_keyboard,
            "disable_web_page_preview": True,
        }
        if message_thread_id is not None:
            payload["message_thread_id"] = message_thread_id

        # Send to Telegram API
        endpoint = f"{self._api_base}/bot{self._bot_token}/sendMessage"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            endpoint,
            data=body,
            headers={"content-type": "application/json"},
            method="POST",
        )

        return self._send_request(
            req=req,
            operation="sendMessage(group_magic_link)",
            chat_id=str(chat_id),
        )

    def _send_request(
        self,
        *,
        req: request.Request,
        operation: str,
        chat_id: str,
    ) -> bool:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                with request.urlopen(req, timeout=self._timeout_seconds) as response:
                    response_payload = json.loads(response.read().decode("utf-8"))
                ok = bool(response_payload.get("ok"))
                if not ok:
                    logger.warning(
                        "Telegram notifier %s returned ok=false on attempt %s for chat_id=%s payload=%s",
                        operation,
                        attempt,
                        chat_id,
                        response_payload,
                    )
                return ok
            except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "Telegram notifier %s failed on attempt %s/%s for chat_id=%s: %s",
                    operation,
                    attempt,
                    self._max_attempts,
                    chat_id,
                    exc,
                )
                if attempt < self._max_attempts:
                    time.sleep(0.5)
        if last_error is not None:
            logger.error(
                "Telegram notifier %s exhausted retries for chat_id=%s: %s",
                operation,
                chat_id,
                last_error,
            )
        return False
