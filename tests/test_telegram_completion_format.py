from __future__ import annotations

from autoresearch.core.services.telegram_completion_format import (
    format_butler_live_status_message,
    polish_butler_completion_card,
    strip_trailing_eof_marker,
)


def test_polish_collapses_excessive_blank_lines() -> None:
    raw = "A\n\n\n\n\nB"
    out = polish_butler_completion_card(raw)
    assert "A" in out
    assert "B" in out
    assert "\n\n\n\n" not in out


def test_strip_trailing_eof_marker() -> None:
    assert strip_trailing_eof_marker("line1\nEOF") == "line1"
    assert strip_trailing_eof_marker("EOF") == ""


def test_polish_strips_eof_then_collapses() -> None:
    raw = "A\n\nEOF\n"
    out = polish_butler_completion_card(raw)
    assert not out.rstrip().endswith("EOF")
    assert "A" in out


def test_polish_truncates_long_text() -> None:
    raw = "x" * 5000
    out = polish_butler_completion_card(raw, max_chars=200)
    assert len(out) <= 250
    assert "截断" in out


def test_live_status_custom_title_overrides_hermes_line() -> None:
    text = format_butler_live_status_message(
        brand="",
        message="progress",
        metrics={
            "telegram_live_card_title": "YouTube 自动流运行中 · digest / YouTube autoflow · digest",
            "telegram_live_elapsed_s": 3,
            "telegram_display_runtime_id": "youtube_autoflow",
            "telegram_display_agent_name": "youtube_ops",
        },
    )
    assert "Hermes 运行中" not in text
    assert "YouTube 自动流运行中" in text
    assert "digest" in text


def test_live_status_default_title_for_hermes_path() -> None:
    text = format_butler_live_status_message(
        brand="",
        message="tick",
        metrics={
            "telegram_live_phase": "running",
            "hermes_status": "running",
        },
    )
    assert "Hermes 运行中" in text
