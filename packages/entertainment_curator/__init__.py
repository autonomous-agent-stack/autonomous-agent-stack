"""Telegram-only entertainment curator bounded service."""

from .curator import curate, parse_telegram_request
from .schema import (
    EntertainmentCuratorRequest,
    EntertainmentCuratorResult,
    EntertainmentRecommendation,
    NotebookLMPack,
)
from .service import EntertainmentCuratorTelegramService
from .youtube_oauth import (
    YOUTUBE_OAUTH_PROFILES,
    YOUTUBE_READONLY_SCOPE,
    YouTubeOAuthProfileRegistry,
)

__all__ = [
    "EntertainmentCuratorRequest",
    "EntertainmentCuratorResult",
    "EntertainmentCuratorTelegramService",
    "EntertainmentRecommendation",
    "NotebookLMPack",
    "YOUTUBE_OAUTH_PROFILES",
    "YOUTUBE_READONLY_SCOPE",
    "YouTubeOAuthProfileRegistry",
    "curate",
    "parse_telegram_request",
]
