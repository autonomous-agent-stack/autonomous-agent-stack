from __future__ import annotations

import json
from typing import Any

from .curator import curate, parse_telegram_request
from .schema import EntertainmentCuratorResult
from .youtube_oauth import YouTubeOAuthProfileRegistry, select_profile_for_curator_payload


class EntertainmentCuratorTelegramService:
    """Telegram-only bounded service for legal entertainment planning."""

    capability_id = "entertainment_curator"
    channel = "telegram"

    def __init__(self, *, oauth_registry: Any | None = None) -> None:
        self._oauth_registry = oauth_registry or YouTubeOAuthProfileRegistry()

    def handle_telegram_message(
        self,
        text: str,
        *,
        requested_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        request = parse_telegram_request(text, requested_by=requested_by, metadata=metadata)
        result = curate(request)
        return self.to_telegram_payload(result)

    def to_telegram_payload(self, result: EntertainmentCuratorResult) -> dict[str, Any]:
        payload = result.model_dump(mode="json")
        selected_profile = select_profile_for_curator_payload(payload)
        profile_status = self._oauth_registry.profile_status(selected_profile)
        payload["account_profile"] = {
            **(payload.get("account_profile") if isinstance(payload.get("account_profile"), dict) else {}),
            "selected_profile": selected_profile,
            "auth_status": profile_status["auth_status"],
            "scopes": profile_status["scopes"],
            "profile_display_name": profile_status["display_name"],
        }
        payload["metadata"] = {
            "capability_id": self.capability_id,
            "channel": self.channel,
            "account_profile": selected_profile,
            "auth_status": profile_status["auth_status"],
            "scopes": profile_status["scopes"],
        }
        payload["capability_id"] = self.capability_id
        payload["source"] = "entertainment_curator_service"
        payload["answer"] = json.dumps(
            {
                "title": payload["title"],
                "mood": payload["mood"],
                "time_available": payload["time_available"],
                "company": payload["company"],
                "recommendations": payload["recommendations"],
                "notebooklm_pack": payload["notebooklm_pack"],
                "copyright_boundary": payload["copyright_boundary"],
            },
            ensure_ascii=False,
            indent=2,
        )
        return payload
