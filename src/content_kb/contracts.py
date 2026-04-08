"""Domain contracts for the content_kb agent.

Subtitle ingestion, topic classification, knowledge base indexing.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ContentTopic(str, Enum):
    AI_STATUS_AND_OUTLOOK = "ai-status-and-outlook"
    VIBE_CODING = "vibe-coding"
    ENTERTAINMENT_STANDUP = "entertainment-standup"
    FILM_TV_RECOMMENDATION = "film-tv-recommendation"
    ECONOMY = "economy"
    WORLDVIEW = "worldview"
    WELLNESS = "wellness"


class ContentType(str, Enum):
    SUBTITLE = "subtitle"
    TRANSCRIPT = "transcript"
    ARTICLE = "article"


class IngestStatus(str, Enum):
    PENDING = "pending"
    CLASSIFYING = "classifying"
    SELECTING_REPO = "selecting_repo"
    INGESTING = "ingesting"
    INDEXING = "indexing"
    COMPLETED = "completed"
    FAILED = "failed"


VALID_TOPICS = [t.value for t in ContentTopic]


class TopicCandidate(StrictModel):
    topic: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @field_validator("topic")
    @classmethod
    def _validate_topic(cls, v: str) -> str:
        if v not in VALID_TOPICS:
            raise ValueError(f"unknown topic: {v}")
        return v


class TopicClassificationResult(StrictModel):
    primary_topic: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    alternatives: list[TopicCandidate] = Field(default_factory=list)

    @field_validator("primary_topic")
    @classmethod
    def _validate_primary(cls, v: str) -> str:
        if v not in VALID_TOPICS:
            raise ValueError(f"unknown topic: {v}")
        return v


class RepoSelection(StrictModel):
    recommended_repo: str = Field(..., min_length=1)
    recommended_directory: str = Field(..., min_length=1)
    reason: str = ""
    needs_new_repo: bool = False


class SubtitleMetadata(StrictModel):
    title: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)
    speaker: list[str] = Field(default_factory=list)
    source_url: str = ""
    language: str = "zh-CN"
    created_at: date = Field(default_factory=date.today)
    tags: list[str] = Field(default_factory=list)
    summary: str = ""
    word_count: int = Field(default=0, ge=0)
    duration_seconds: int | None = None

    @field_validator("topic")
    @classmethod
    def _validate_topic(cls, v: str) -> str:
        if v not in VALID_TOPICS:
            raise ValueError(f"unknown topic: {v}")
        return v


class ContentKBProfile(StrictModel):
    profile_name: str = Field(..., min_length=1)
    owner: str = Field(..., min_length=1)
    default_repo: str = "knowledge-base"
    language: str = "zh-CN"
    gh_token_env: str = "GH_TOKEN"
    gh_host: str = "github.com"


class IngestOptions(StrictModel):
    generate_summary: bool = True
    generate_tags: bool = True
    update_indexes: bool = True
    open_pr: bool = False


class IngestRequest(StrictModel):
    owner_profile: str = Field(..., min_length=1)
    content_type: ContentType = ContentType.SUBTITLE
    topic: str | None = None
    title: str = Field(..., min_length=1)
    source_url: str = ""
    subtitle_text_path: str = Field(..., min_length=1)
    language: str = "zh-CN"
    options: IngestOptions = Field(default_factory=lambda: IngestOptions())


class IngestResult(StrictModel):
    job_id: str = Field(..., min_length=1)
    status: IngestStatus = IngestStatus.PENDING
    topic: str | None = None
    repo: str | None = None
    directory: str | None = None
    files_written: list[str] = Field(default_factory=list)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicIndexEntry(StrictModel):
    count: int = Field(default=0, ge=0)
    latest_title: str = ""
    latest_slug: str = ""


class TopicIndex(StrictModel):
    version: Literal["topics/v1"] = "topics/v1"
    updated_at: str = Field(default_factory=lambda: date.today().isoformat())
    topics: dict[str, TopicIndexEntry] = Field(default_factory=dict)


class SpeakerIndexEntry(StrictModel):
    appearances: int = Field(default=0, ge=0)
    topics: list[str] = Field(default_factory=list)
    latest_title: str = ""


class SpeakerIndex(StrictModel):
    version: Literal["speakers/v1"] = "speakers/v1"
    updated_at: str = Field(default_factory=lambda: date.today().isoformat())
    speakers: dict[str, SpeakerIndexEntry] = Field(default_factory=dict)


class TimelineEntry(StrictModel):
    date: str
    topic: str
    title: str
    slug: str = ""


class TimelineIndex(StrictModel):
    version: Literal["timeline/v1"] = "timeline/v1"
    updated_at: str = Field(default_factory=lambda: date.today().isoformat())
    entries: list[TimelineEntry] = Field(default_factory=list)


class ChooseRepoRequest(StrictModel):
    owner_profile: str = Field(..., min_length=1)
    content_type: ContentType = ContentType.SUBTITLE
    topic_guess: str | None = None
    source_title: str = ""
    source_url: str = ""
    language: str = "zh-CN"


class ChooseRepoResult(StrictModel):
    profile_name: str
    repo_full_name: str
    directory: str
    reason: str
    needs_new_repo: bool = False
