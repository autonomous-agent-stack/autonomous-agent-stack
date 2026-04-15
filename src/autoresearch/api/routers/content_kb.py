"""Content Knowledge Base API router.

Provides HTTP endpoints for subtitle ingestion, topic classification,
repo selection, and index building.

Kept as a thin wrapper over existing src/content_kb/ modules.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from content_kb.contracts import (
    ChooseRepoRequest,
    ChooseRepoResult,
    ContentKBProfile,
    ContentTopic,
    IngestRequest,
    IngestResult,
    IngestStatus,
    SpeakerIndex,
    TimelineIndex,
    TopicClassificationResult,
    TopicIndex,
)
from content_kb.index_builder import (
    build_speaker_index,
    build_timeline_index,
    build_topic_index,
)
from content_kb.repo_selector import select_repo
from content_kb.subtitle_ingest import infer_topic_from_subtitle, ingest_subtitle
from content_kb.topic_classifier import classify_by_keywords

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1/content-kb", tags=["content_kb"])


# ============================================================================
# Request/Response Models
# ============================================================================


class HealthRead(BaseModel):
    """Health check response."""

    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    service: str = "content_kb"
    version: str = "1.0.0"
    capabilities: list[str] = []


class TopicCandidateRead(BaseModel):
    """Topic candidate for classification result."""

    topic: str
    confidence: float


class ClassifyResult(BaseModel):
    """Topic classification result."""

    model_config = ConfigDict(extra="allow")

    primary_topic: str
    confidence: float
    alternatives: list[TopicCandidateRead] = []
    valid_topics: list[str] = []


class BuildIndexResult(BaseModel):
    """Build index result."""

    model_config = ConfigDict(extra="allow")

    status: str
    index_type: str
    entries_count: int
    index: dict[str, Any] | None = None
    written_to: str | None = None


# ============================================================================
# HTTP Error Helpers
# ============================================================================


def _http_exception(message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR) -> HTTPException:
    """Create HTTP exception with message."""
    return HTTPException(status_code=status_code, detail={"message": message})


# ============================================================================
# Default Profile
# ============================================================================


def _get_default_profile() -> ContentKBProfile:
    """Get default content_kb profile."""
    return ContentKBProfile(
        profile_name="default",
        owner="knowledge-base",
        default_repo="knowledge-base",
        language="zh-CN",
    )


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/health", tags=["content_kb"])
def get_health() -> HealthRead:
    """Health check endpoint."""
    return HealthRead(
        status="ok",
        service="content_kb",
        version="1.0.0",
        capabilities=[
            "classify",
            "choose-repo",
            "ingest",
            "build-index",
        ],
    )


@router.post("/classify", tags=["content_kb"])
def classify_topic(
    text: str = Body(..., embed=True, description="Text to classify"),
) -> ClassifyResult:
    """Classify text into a content topic using keyword matching.

    Args:
        text: Text content to classify

    Returns:
        Classification result with primary_topic, confidence, and alternatives
    """
    if not text:
        raise _http_exception("text field is required", status.HTTP_400_BAD_REQUEST)

    try:
        result: TopicClassificationResult = classify_by_keywords(text)
        return ClassifyResult(
            primary_topic=result.primary_topic,
            confidence=result.confidence,
            alternatives=[TopicCandidateRead(topic=a.topic, confidence=a.confidence) for a in result.alternatives],
            valid_topics=[t.value for t in ContentTopic],
        )
    except Exception as exc:
        logger.exception("Error during topic classification")
        raise _http_exception(str(exc)) from exc


@router.post("/choose-repo", tags=["content_kb"])
def choose_repo(
    owner_profile: str = Body("default", embed=True),
    source_title: str = Body("", embed=True),
    topic_guess: str | None = Body(None, embed=True),
    source_url: str = Body("", embed=True),
    language: str = Body("zh-CN", embed=True),
) -> ChooseRepoResult:
    """Select the best repository and directory for content ingestion.

    Args:
        owner_profile: Profile name for the owner
        source_title: Title of the content being ingested
        topic_guess: Optional topic hint
        source_url: Optional source URL
        language: Content language

    Returns:
        ChooseRepoResult with repo_full_name, directory, reason, and needs_new_repo flag
    """
    try:
        # Build ChooseRepoRequest from parameters
        choose_request = ChooseRepoRequest(
            owner_profile=owner_profile,
            content_type="subtitle",
            topic_guess=topic_guess,
            source_title=source_title,
            source_url=source_url,
            language=language,
        )

        # Get profile and existing repos (empty for now - could be extended)
        profile = _get_default_profile()
        existing_repos: list[str] = []  # Could be fetched from GitHub API

        # Select repo
        result: ChooseRepoResult = select_repo(
            request=choose_request,
            profile=profile,
            existing_repos=existing_repos or None,
        )

        return result

    except Exception as exc:
        logger.exception("Error during repo selection")
        raise _http_exception(str(exc)) from exc


@router.post("/ingest", tags=["content_kb"])
def ingest_content(
    subtitle_text_path: str = Body(..., embed=True),
    title: str = Body("", embed=True),
    topic: str = Body("", embed=True),
    source_url: str = Body("", embed=True),
    job_id: str | None = Body(None, embed=True),
) -> IngestResult:
    """Ingest subtitle content into the knowledge base.

    Args:
        subtitle_text_path: Path to the SRT subtitle file
        title: Content title
        topic: Content topic. If omitted, the router infers it from subtitle text.
        source_url: Optional source URL
        job_id: Optional job identifier

    Returns:
        IngestResult with job_id, status, metadata, and files_written
    """
    if not subtitle_text_path:
        raise _http_exception("subtitle_text_path is required", status.HTTP_400_BAD_REQUEST)

    try:
        # Verify file exists
        path = Path(subtitle_text_path)
        if not path.exists():
            raise _http_exception(f"Subtitle file not found: {subtitle_text_path}", status.HTTP_404_NOT_FOUND)

        resolved_topic = topic.strip() if topic else infer_topic_from_subtitle(path)

        # Run ingestion
        result: IngestResult = ingest_subtitle(
            file_path=path,
            job_id=job_id or str(uuid.uuid4()),
            title=title,
            topic=resolved_topic,
            source_url=source_url,
        )

        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error during content ingestion")
        raise _http_exception(str(exc)) from exc


@router.post("/build-index", tags=["content_kb"])
def build_index(
    index_type: str = Body("topic", embed=True),
    entries: list[dict[str, Any]] = Body(..., embed=True),
    existing_index: dict[str, Any] | None = Body(None, embed=True),
    output_path: str | None = Body(None, embed=True),
) -> BuildIndexResult:
    """Build or update a content index (topic/speaker/timeline).

    Args:
        index_type: Type of index to build (topic/speaker/timeline)
        entries: List of content entries to index
        existing_index: Optional existing index to update
        output_path: Optional path to write the index file

    Returns:
        BuildIndexResult with index data and write status
    """
    if not entries:
        raise _http_exception("entries field is required and must be non-empty", status.HTTP_400_BAD_REQUEST)

    try:
        result_data: dict[str, Any] = {
            "index_type": index_type,
            "entries_count": len(entries),
        }

        if index_type == "topic":
            existing = TopicIndex(**existing_index) if existing_index else None
            updated_index: TopicIndex = build_topic_index(existing, entries)
            result_data["index"] = updated_index.model_dump()

        elif index_type == "speaker":
            existing = SpeakerIndex(**existing_index) if existing_index else None
            updated_index: SpeakerIndex = build_speaker_index(existing, entries)
            result_data["index"] = updated_index.model_dump()

        elif index_type == "timeline":
            existing = TimelineIndex(**existing_index) if existing_index else None
            updated_index: TimelineIndex = build_timeline_index(existing, entries)
            result_data["index"] = updated_index.model_dump()

        else:
            raise _http_exception(
                f"unknown index_type: {index_type}. valid: topic, speaker, timeline",
                status.HTTP_400_BAD_REQUEST,
            )

        # Write to file if output_path provided
        if output_path:
            from content_kb.index_builder import write_index_file

            output = Path(output_path)
            output.parent.mkdir(parents=True, exist_ok=True)

            # Map index_type to actual index object
            index_map = {
                "topic": TopicIndex(**result_data["index"]),
                "speaker": SpeakerIndex(**result_data["index"]),
                "timeline": TimelineIndex(**result_data["index"]),
            }
            write_index_file(output, index_map[index_type])
            result_data["written_to"] = str(output)

        return BuildIndexResult(
            status="completed",
            **result_data,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error during index building")
        raise _http_exception(str(exc)) from exc
