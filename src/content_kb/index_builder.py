"""Index building for content knowledge base.

Builds and updates topic, speaker, and timeline indexes.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from content_kb.contracts import (
    SpeakerIndex,
    SpeakerIndexEntry,
    TimelineEntry,
    TimelineIndex,
    TopicIndex,
    TopicIndexEntry,
)

logger = logging.getLogger(__name__)


def build_topic_index(
    existing_index: TopicIndex | None,
    entries: list[dict],
) -> TopicIndex:
    """Build or update topic index from content entries.

    Args:
        existing_index: Current topic index, if any
        entries: List of content entries with 'topic', 'title', 'slug' keys

    Returns:
        Updated TopicIndex
    """
    base = existing_index or TopicIndex()

    for entry in entries:
        topic = entry.get("topic", "")
        if not topic:
            continue

        if topic not in base.topics:
            base.topics[topic] = TopicIndexEntry()

        base.topics[topic].count += 1
        base.topics[topic].latest_title = entry.get("title", "")
        base.topics[topic].latest_slug = entry.get("slug", "")

    base.updated_at = date.today().isoformat()
    return base


def build_speaker_index(
    existing_index: SpeakerIndex | None,
    entries: list[dict],
) -> SpeakerIndex:
    """Build or update speaker index from content entries.

    Args:
        existing_index: Current speaker index, if any
        entries: List of content entries with 'speaker' list and 'topic' keys

    Returns:
        Updated SpeakerIndex
    """
    base = existing_index or SpeakerIndex()

    for entry in entries:
        speakers = entry.get("speaker", [])
        if not isinstance(speakers, list):
            continue

        topic = entry.get("topic", "")
        title = entry.get("title", "")

        for speaker in speakers:
            if not speaker:
                continue

            if speaker not in base.speakers:
                base.speakers[speaker] = SpeakerIndexEntry()

            base.speakers[speaker].appearances += 1
            if topic and topic not in base.speakers[speaker].topics:
                base.speakers[speaker].topics.append(topic)
            base.speakers[speaker].latest_title = title

    base.updated_at = date.today().isoformat()
    return base


def build_timeline_index(
    existing_index: TimelineIndex | None,
    entries: list[dict],
) -> TimelineIndex:
    """Build or update timeline index from content entries.

    Args:
        existing_index: Current timeline index, if any
        entries: List of content entries with 'date', 'topic', 'title', 'slug' keys

    Returns:
        Updated TimelineIndex
    """
    base = existing_index or TimelineIndex()

    for entry in entries:
        entry_date = entry.get("created_at", "")
        if not entry_date:
            continue

        # Convert date string to ISO format if needed
        if isinstance(entry_date, date):
            entry_date = entry_date.isoformat()

        timeline_entry = TimelineEntry(
            date=entry_date,
            topic=entry.get("topic", ""),
            title=entry.get("title", ""),
            slug=entry.get("slug", ""),
        )

        base.entries.append(timeline_entry)

    # Sort by date descending
    base.entries.sort(key=lambda e: e.date, reverse=True)
    base.updated_at = date.today().isoformat()
    return base


def write_index_file(index_path: Path, index: TopicIndex | SpeakerIndex | TimelineIndex) -> None:
    """Write index to file as YAML.

    Args:
        index_path: Path to write the index file
        index: Index object to write
    """
    import json

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index.model_dump(), indent=2, ensure_ascii=False))
    logger.info(f"Updated index: {index_path}")
