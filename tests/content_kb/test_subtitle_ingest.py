"""Tests for content_kb subtitle ingestion."""
from __future__ import annotations

from pathlib import Path

import pytest

from content_kb.subtitle_ingest import ingest_subtitle, normalize_subtitle, read_subtitle
from content_kb.contracts import IngestStatus


@pytest.fixture()
def srt_file(tmp_path: Path) -> Path:
    p = tmp_path / "test.srt"
    p.write_text("""1
00:00:01,000 --> 00:00:03,000
Hello world

2
00:00:04,000 --> 00:00:06,000
This is a test
""", encoding="utf-8")
    return p


class TestSubtitleIngest:
    def test_read_subtitle(self, srt_file: Path) -> None:
        text = read_subtitle(str(srt_file))
        assert "Hello world" in text

    def test_normalize_strips_timestamps(self, srt_file: Path) -> None:
        raw = read_subtitle(str(srt_file))
        normalized = normalize_subtitle(raw)
        assert "-->" not in normalized
        assert "Hello world" in normalized
        assert "This is a test" in normalized

    def test_normalize_strips_sequence_numbers(self) -> None:
        raw = "1\n00:00:01,000 --> 00:00:02,000\nText\n\n2\n00:00:03,000 --> 00:00:04,000\nMore"
        result = normalize_subtitle(raw)
        lines = [l for l in result.split("\n") if l.strip()]
        assert all(not l.isdigit() for l in lines)

    def test_ingest_full_pipeline(self, srt_file: Path) -> None:
        result = ingest_subtitle(str(srt_file), title="Test Video", topic="vibe-coding")
        assert result.status == IngestStatus.INGESTING
        assert result.metadata is not None
        assert result.metadata["title"] == "Test Video"
        assert result.metadata["topic"] == "vibe-coding"
        assert result.job_id is not None

    def test_read_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_subtitle(str(tmp_path / "missing.srt"))
