from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from autoresearch.shared.models import StrictModel


class SubtitleOutputFormat(str, Enum):
    SRT = "srt"
    TXT = "txt"


class SubtitleJobStatus(str, Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class MediaJobSubtitleRequest(StrictModel):
    url: str = Field(..., min_length=1)
    output_format: SubtitleOutputFormat = SubtitleOutputFormat.SRT
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def _normalize_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("subtitle url must be http or https")
        return normalized


class MediaJobContractSubtitle(StrictModel):
    url: str
    title: str
    output_path: str
    output_format: SubtitleOutputFormat
    status: SubtitleJobStatus = SubtitleJobStatus.PENDING
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_subtitle_path: str | None = None
    created_at: datetime
    updated_at: datetime
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def __str__(self) -> str:
        return (
            f"MediaJobContractSubtitle(status={self.status.value}, "
            f"title={self.title!r}, output_path={self.output_path!r})"
        )


MediaJobSubtitleRead = MediaJobContractSubtitle
