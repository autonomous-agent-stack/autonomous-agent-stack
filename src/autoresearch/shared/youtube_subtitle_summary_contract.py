from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from autoresearch.shared.models import StrictModel


class YouTubeSubtitleSummaryStatus(str, Enum):
    DONE = "done"
    FAILED = "failed"


class YouTubeSubtitleSummaryRequest(StrictModel):
    youtube_url: str = Field(..., min_length=1)
    subtitle_text: str | None = None
    title: str | None = None
    summary_style: str = Field(default="bullet", min_length=1)
    max_key_points: int = Field(default=5, ge=1, le=10)
    max_summary_chars: int = Field(default=1200, ge=200, le=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("youtube_url")
    @classmethod
    def _normalize_youtube_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("youtube_url must be http or https")
        return normalized

    @field_validator("subtitle_text", "title", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class YouTubeSubtitleSummaryResult(StrictModel):
    source_url: str
    title: str
    summary_status: YouTubeSubtitleSummaryStatus
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    error_kind: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


__all__ = [
    "YouTubeSubtitleSummaryRequest",
    "YouTubeSubtitleSummaryResult",
    "YouTubeSubtitleSummaryStatus",
]
