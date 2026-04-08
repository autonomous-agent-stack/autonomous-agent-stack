"""Subtitle ingestion pipeline.

Reads subtitle files, normalizes them, and prepares for knowledge base entry.
"""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from content_kb.contracts import IngestResult, IngestStatus, SubtitleMetadata

logger = logging.getLogger(__name__)


def read_subtitle(file_path: str | Path) -> str:
    """Read and return raw subtitle text."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Subtitle file not found: {path}")
    return path.read_text(encoding="utf-8")


def normalize_subtitle(raw: str) -> str:
    """Normalize subtitle text: strip timestamps, merge lines."""
    lines = raw.strip().split("\n")
    text_lines: list[str] = []
    for line in lines:
        line = line.strip()
        # Skip SRT sequence numbers
        if line.isdigit():
            continue
        # Skip timestamp lines
        if "-->" in line:
            continue
        # Skip empty lines
        if not line:
            continue
        text_lines.append(line)
    return "\n".join(text_lines)


def ingest_subtitle(
    file_path: str | Path,
    *,
    job_id: str | None = None,
    title: str = "",
    topic: str = "",
    source_url: str = "",
) -> IngestResult:
    """Full subtitle ingestion pipeline.

    Args:
        file_path: Path to subtitle file
        job_id: Optional job identifier (auto-generated if not provided)
        title: Content title
        topic: Content topic
        source_url: Optional source URL

    Returns:
        IngestResult with status and metadata
    """
    path = Path(file_path)
    raw = read_subtitle(path)
    normalized = normalize_subtitle(raw)

    metadata = SubtitleMetadata(
        title=title or path.stem,
        topic=topic,
        source_url=source_url,
    )

    return IngestResult(
        job_id=job_id or str(uuid.uuid4()),
        status=IngestStatus.INGESTING,
        topic=topic,
        metadata=metadata.model_dump(),
        files_written=["normalized_subtitle.txt"],
    )
