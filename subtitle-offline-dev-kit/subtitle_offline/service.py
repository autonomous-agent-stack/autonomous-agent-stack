"""Offline subtitle parsing and cleaning helpers."""

from __future__ import annotations

import json
from pathlib import Path

from .contract import SubtitleFileContract, SubtitleLine
from .utils import (
    infer_language_from_filename,
    normalize_subtitle_text,
    parse_time_range,
    split_subtitle_blocks,
    validate_timeline_order,
)


def parse_vtt(content: str, language_hint: str | None = None) -> list[SubtitleLine]:
    """Parse a VTT string into normalized subtitle lines."""

    subtitle_lines: list[SubtitleLine] = []
    for block in split_subtitle_blocks(content):
        block_lines = [line.strip("\ufeff") for line in block.splitlines()]
        if not block_lines:
            continue

        first_line = block_lines[0].strip()
        if first_line == "WEBVTT" or first_line.startswith("NOTE"):
            continue

        timestamp_index = next((i for i, line in enumerate(block_lines) if "-->" in line), None)
        if timestamp_index is None:
            continue

        start, end = parse_time_range(block_lines[timestamp_index])
        text = normalize_subtitle_text(block_lines[timestamp_index + 1 :])
        subtitle_lines.append(_build_line(start, end, text, language_hint))

    validate_timeline_order(subtitle_lines)
    return subtitle_lines


def parse_srt(content: str, language_hint: str | None = None) -> list[SubtitleLine]:
    """Parse an SRT string into normalized subtitle lines."""

    subtitle_lines: list[SubtitleLine] = []
    for block in split_subtitle_blocks(content):
        block_lines = [line.strip("\ufeff") for line in block.splitlines()]
        if not block_lines:
            continue

        timestamp_index = next((i for i, line in enumerate(block_lines) if "-->" in line), None)
        if timestamp_index is None:
            continue

        start, end = parse_time_range(block_lines[timestamp_index])
        text = normalize_subtitle_text(block_lines[timestamp_index + 1 :])
        subtitle_lines.append(_build_line(start, end, text, language_hint))

    validate_timeline_order(subtitle_lines)
    return subtitle_lines


def _build_line(start: float, end: float, text: str, language: str | None) -> SubtitleLine:
    """Construct one normalized subtitle line and annotate obvious local issues."""

    note: str | None = None
    if not text:
        note = "missing_text"
    return SubtitleLine(
        start=start,
        end=end,
        text=text,
        language=language,
        speaker=None,
        note=note,
    )


def clean_subtitle_file(path: str | Path) -> SubtitleFileContract:
    """Normalize one subtitle file into the shared contract."""

    subtitle_path = Path(path)
    content = load_subtitle(subtitle_path)
    language = infer_language_from_filename(subtitle_path)

    suffix = subtitle_path.suffix.lower()
    if suffix == ".vtt":
        lines = parse_vtt(content, language_hint=language)
    elif suffix == ".srt":
        lines = parse_srt(content, language_hint=language)
    else:
        raise ValueError(f"Unsupported subtitle format: {subtitle_path.suffix}")

    total_duration = max((max(line["start"], line["end"]) for line in lines), default=0.0)
    return SubtitleFileContract(
        filename=subtitle_path.name,
        lines=lines,
        total_duration=total_duration,
        language=language,
    )


def load_subtitle(path: str | Path) -> str:
    """Read a subtitle file from disk."""

    subtitle_path = Path(path)
    return subtitle_path.read_text(encoding="utf-8", errors="ignore")


def save_subtitle(contract: SubtitleFileContract, destination: str | Path) -> None:
    """Persist a normalized subtitle record."""

    output_path = Path(destination)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
