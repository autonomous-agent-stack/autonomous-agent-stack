from __future__ import annotations

from autoresearch.core.services.telegram_completion_format import (
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
