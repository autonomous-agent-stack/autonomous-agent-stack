from __future__ import annotations

from autoresearch.core.services.telegram_completion_format import polish_butler_completion_card


def test_polish_collapses_excessive_blank_lines() -> None:
    raw = "A\n\n\n\n\nB"
    out = polish_butler_completion_card(raw)
    assert "A" in out
    assert "B" in out
    assert "\n\n\n\n" not in out


def test_polish_truncates_long_text() -> None:
    raw = "x" * 5000
    out = polish_butler_completion_card(raw, max_chars=200)
    assert len(out) <= 250
    assert "截断" in out
