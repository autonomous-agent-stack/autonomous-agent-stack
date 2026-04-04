from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from autoresearch.shared.media_job_contract_subtitle import (
    MediaJobContractSubtitle,
    SubtitleJobStatus,
    SubtitleOutputFormat,
)
from autoresearch.shared.models import StrictModel


class YoutubeSubtitleSummaryStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class YoutubeSubtitleSummaryRequest(StrictModel):
    youtube_url: str = Field(..., min_length=1)
    output_dir: str = "artifacts/youtube-subtitle-summary"
    output_format: SubtitleOutputFormat = SubtitleOutputFormat.TXT
    yt_dlp_bin: str = "yt-dlp"
    summary_style: str = Field(default="bullet", min_length=1)
    max_key_points: int = Field(default=5, ge=1, le=10)
    max_summary_chars: int = Field(default=1200, ge=200, le=4000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("youtube_url")
    @classmethod
    def _normalize_youtube_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("youtube url must be http or https")
        return normalized


class YoutubeSubtitleSummaryResult(StrictModel):
    source_url: str
    title: str
    subtitle_status: SubtitleJobStatus
    summary_status: YoutubeSubtitleSummaryStatus = YoutubeSubtitleSummaryStatus.PENDING
    error_kind: str | None = None
    subtitle_result: MediaJobContractSubtitle | None = None
    summary: str | None = None
    key_points: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_subtitle_path: str | None = None
    clean_subtitle_path: str | None = None
    created_at: datetime
    updated_at: datetime
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


__all__ = [
    "YoutubeSubtitleSummaryRequest",
    "YoutubeSubtitleSummaryResult",
    "YoutubeSubtitleSummaryStatus",
]
