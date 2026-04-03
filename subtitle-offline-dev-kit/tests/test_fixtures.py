from pathlib import Path
import json


FIXTURES = (
    "sample_01_en.vtt",
    "sample_02_zh.vtt",
    "sample_03_dirty.srt",
    "sample_04_mixed.vtt",
    "sample_05_missing_fields.srt",
    "sample_06_long.vtt",
    "sample_07_exception.srt",
)


def test_all_phase1_fixtures_exist_and_are_non_empty() -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"

    for name in FIXTURES:
        path = fixtures_dir / name
        assert path.exists(), f"missing fixture: {name}"
        assert path.read_text(encoding="utf-8").strip(), f"empty fixture: {name}"


def test_fixtures_no_longer_contain_placeholder_todos() -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"

    for name in FIXTURES:
        content = (fixtures_dir / name).read_text(encoding="utf-8")
        assert "[TODO]" not in content
        assert "NOTE TODO" not in content


def test_fixture_manifest_covers_all_fixture_files() -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"
    manifest = json.loads((fixtures_dir / "manifest.json").read_text(encoding="utf-8"))
    outputs = {item["output"] for item in manifest["fixtures"]}

    assert outputs == set(FIXTURES)
