from pathlib import Path

import pytest

from subtitle_offline.service import clean_subtitle_file, load_subtitle, save_subtitle

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.mark.parametrize(
    ("fixture_name", "expected_line_count", "expected_language"),
    [
        ("sample_01_en.vtt", 3, "en"),
        ("sample_02_zh.vtt", 4, "zh"),
        ("sample_03_dirty.srt", 2, None),
        ("sample_04_mixed.vtt", 2, None),
        ("sample_05_missing_fields.srt", 2, None),
        ("sample_06_long.vtt", 2, None),
        ("sample_07_exception.srt", 2, None),
    ],
)
def test_clean_subtitle_file_handles_all_phase2_fixtures(
    fixture_name: str, expected_line_count: int, expected_language: str | None
) -> None:
    subtitle_path = FIXTURE_DIR / fixture_name
    result = clean_subtitle_file(subtitle_path)

    assert result["filename"] == fixture_name
    assert len(result["lines"]) == expected_line_count
    assert result["language"] == expected_language
    assert result["total_duration"] >= 0.0
    assert all(
        {"start", "end", "text", "language", "speaker", "note"} <= set(line)
        for line in result["lines"]
    )


def test_clean_subtitle_file_marks_missing_text() -> None:
    result = clean_subtitle_file(FIXTURE_DIR / "sample_05_missing_fields.srt")

    assert result["lines"][1]["text"] == ""
    assert result["lines"][1]["note"] == "missing_text"


def test_clean_subtitle_file_marks_reversed_timeline() -> None:
    result = clean_subtitle_file(FIXTURE_DIR / "sample_07_exception.srt")

    assert "end_before_start" in (result["lines"][0]["note"] or "")
    assert "out_of_order" in (result["lines"][1]["note"] or "")


def test_load_and_save_subtitle_round_trip(tmp_path: Path) -> None:
    fixture_path = FIXTURE_DIR / "sample_03_dirty.srt"
    contract = clean_subtitle_file(fixture_path)
    output_path = tmp_path / "sample_03_dirty.json"

    original_text = load_subtitle(fixture_path)
    save_subtitle(contract, output_path)

    assert "大家好，这里是最佳拍档" in original_text
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8").strip().startswith("{")


def test_clean_long_fixture_uses_real_non_empty_cues() -> None:
    result = clean_subtitle_file(FIXTURE_DIR / "sample_06_long.vtt")

    assert all(line["text"] for line in result["lines"])
    assert all(line["note"] is None for line in result["lines"])


def test_clean_subtitle_file_rejects_unknown_suffix(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("not a subtitle file", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported subtitle format"):
        clean_subtitle_file(path)
