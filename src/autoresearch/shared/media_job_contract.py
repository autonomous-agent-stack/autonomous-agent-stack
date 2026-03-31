from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import Field, field_validator

from autoresearch.shared.models import StrictModel

_ALLOWED_FILENAME_TOKENS = {"{title}", "{id}", "{uploader}", "{upload_date}"}


class MediaJobMode(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    SUBTITLE = "subtitle"
    METADATA = "metadata"


class MediaJobPostprocess(str, Enum):
    NONE = "none"
    MP3 = "mp3"
    MP4 = "mp4"


class MediaTargetBucket(str, Enum):
    INBOX = "inbox"
    AUDIO = "audio"
    VIDEO = "video"
    SUBTITLES = "subtitles"
    META = "meta"


class MediaJobStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MediaJobRequest(StrictModel):
    url: str = Field(..., min_length=1)
    mode: MediaJobMode
    target_bucket: MediaTargetBucket
    filename_template: str = "{title}-{id}"
    postprocess: MediaJobPostprocess = MediaJobPostprocess.NONE
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("url")
    @classmethod
    def _normalize_url(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith(("http://", "https://")):
            raise ValueError("media url must be http or https")
        return normalized

    @field_validator("filename_template")
    @classmethod
    def _validate_template(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("filename_template is required")
        parts = [part for part in normalized.split("-") if part]
        if not parts:
            raise ValueError("filename_template must include at least one token")
        for part in parts:
            if part not in _ALLOWED_FILENAME_TOKENS:
                raise ValueError(f"unsupported filename token: {part}")
        return "-".join(parts)


class MediaJobRead(StrictModel):
    job_id: str
    url: str
    mode: MediaJobMode
    target_bucket: MediaTargetBucket
    filename_template: str
    postprocess: MediaJobPostprocess
    status: MediaJobStatus = MediaJobStatus.CREATED
    output_files: list[str] = Field(default_factory=list)
    title: str | None = None
    duration_seconds: int | None = None
    uploader: str | None = None
    subtitle_path: str | None = None
    metadata_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    error: str | None = None


class MediaJobEventRead(StrictModel):
    event_id: str
    job_id: str
    stage: str
    status: str
    detail: str = ""
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
