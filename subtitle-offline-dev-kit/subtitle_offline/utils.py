"""Utility helpers for offline subtitle parsing and validation."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from .contract import SubtitleLine

_TIMESTAMP_SEPARATOR_RE = re.compile(r"\s*-->\s*")
_SRT_TIMECODE_RE = re.compile(r"\d{2}:\d{2}:\d{2},\d{3}")
_VTT_TIMECODE_RE = re.compile(r"\d{2}:\d{2}:\d{2}\.\d{3}")


def split_subtitle_blocks(content: str) -> list[str]:
    """Split subtitle text into logical blocks, independent of newline style."""

    normalized = content.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    return [block for block in re.split(r"\n\s*\n+", normalized) if block.strip()]


def normalize_subtitle_text(lines: Iterable[str]) -> str:
    """Collapse multiline subtitle text into one normalized string."""

    cleaned = [line.strip() for line in lines if line.strip()]
    return " ".join(cleaned)


def time_to_seconds(timestamp: str) -> float:
    """Convert ``hh:mm:ss.xxx`` or ``hh:mm:ss,xxx`` into seconds."""

    hours, minutes, seconds = timestamp.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_time_range(time_line: str) -> tuple[float, float]:
    """Parse a single subtitle time range line."""

    start_text, end_text = _TIMESTAMP_SEPARATOR_RE.split(time_line.strip(), maxsplit=1)
    start_token = start_text.split()[0]
    end_token = end_text.split()[0]
    return time_to_seconds(start_token), time_to_seconds(end_token)


def detect_subtitle_format(text: str) -> str:
    """Infer the subtitle format from raw text."""

    stripped = text.lstrip()
    if stripped.startswith("WEBVTT"):
        return "vtt"
    if _SRT_TIMECODE_RE.search(text):
        return "srt"
    if _VTT_TIMECODE_RE.search(text):
        return "vtt"
    raise ValueError("Unable to detect subtitle format from content")


def infer_language_from_filename(path: str | Path) -> str | None:
    """Guess a language code from a fixture or subtitle file name."""

    stem = Path(path).stem.lower()
    tokens = re.split(r"[^a-z0-9]+", stem)
    for token in tokens:
        if token in {"en", "eng"}:
            return "en"
        if token in {"zh", "zho", "cn"}:
            return "zh"
        if token in {"hans", "zhhans", "zhhansvtt"}:
            return "zh"
    if "zh-hans" in stem or "zh_cn" in stem or "zh-cn" in stem:
        return "zh"
    return None


def merge_note(existing: str | None, new_note: str) -> str:
    """Attach one validation marker to an existing note string."""

    if not existing:
        return new_note
    notes = existing.split(";")
    if new_note in notes:
        return existing
    notes.append(new_note)
    return ";".join(notes)


def validate_timeline_order(lines: list[SubtitleLine]) -> list[str]:
    """Return timeline anomalies while also annotating the affected lines."""

    errors: list[str] = []
    previous_start: float | None = None
    previous_end: float | None = None

    for index, line in enumerate(lines, start=1):
        if line["end"] < line["start"]:
            line["note"] = merge_note(line["note"], "end_before_start")
            errors.append(f"line {index}: end before start")
        if previous_start is not None and line["start"] < previous_start:
            line["note"] = merge_note(line["note"], "out_of_order")
            errors.append(f"line {index}: start is out of order")
        if previous_end is not None and line["start"] < previous_end:
            line["note"] = merge_note(line["note"], "overlap_previous")
            errors.append(f"line {index}: overlaps previous cue")
        previous_start = line["start"]
        previous_end = line["end"]

    return errors
