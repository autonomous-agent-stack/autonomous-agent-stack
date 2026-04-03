"""Typed subtitle contracts for the offline dev kit."""

from __future__ import annotations

from typing import Optional, TypedDict


SUBTITLE_REQUIRED_FIELDS = (
    "filename",
    "lines",
    "total_duration",
    "language",
)


SUBTITLE_LINE_FIELDS = (
    "start",
    "end",
    "text",
    "language",
    "speaker",
    "note",
)


class SubtitleLine(TypedDict):
    """Normalized subtitle cue used across parsers and tests."""

    start: float
    end: float
    text: str
    language: Optional[str]
    speaker: Optional[str]
    note: Optional[str]


class SubtitleFileContract(TypedDict):
    """Normalized subtitle file shape returned by ``clean_subtitle_file``."""

    filename: str
    lines: list[SubtitleLine]
    total_duration: float
    language: Optional[str]
