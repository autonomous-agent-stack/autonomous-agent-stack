from subtitle_offline.contract import (
    SUBTITLE_LINE_FIELDS,
    SUBTITLE_REQUIRED_FIELDS,
    SubtitleFileContract,
    SubtitleLine,
)


def test_required_fields_are_declared() -> None:
    assert SUBTITLE_REQUIRED_FIELDS == ("filename", "lines", "total_duration", "language")
    assert SUBTITLE_LINE_FIELDS == ("start", "end", "text", "language", "speaker", "note")


def test_contract_accepts_minimal_shape() -> None:
    line = SubtitleLine(
        start=0.0,
        end=2.0,
        text="hello world",
        language="en",
        speaker=None,
        note=None,
    )
    contract = SubtitleFileContract(
        filename="sample_01_en.vtt",
        lines=[line],
        total_duration=2.0,
        language="en",
    )

    assert contract["lines"][0]["text"] == "hello world"
