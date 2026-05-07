from __future__ import annotations

from pathlib import Path


PROMPT_NAMES = {
    "daily_plan.md",
    "quick_relax.md",
    "funny_social.md",
    "exciting_watch.md",
    "learning_deep_dive.md",
    "music_companion.md",
    "weekend_mix.md",
}


def test_all_entertainment_curator_prompts_exist_and_define_boundary() -> None:
    prompt_dir = Path("packages/entertainment_curator/prompts")
    files = {path.name for path in prompt_dir.glob("*.md")}

    assert files == PROMPT_NAMES
    for name in PROMPT_NAMES:
        text = (prompt_dir / name).read_text(encoding="utf-8").lower()
        assert "copyright boundary" in text or "copyright" in text
        assert "piracy" in text
        assert "paid-platform bypass" in text

