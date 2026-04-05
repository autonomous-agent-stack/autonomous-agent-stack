from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_scan_subtitle_anomalies_reports_only_issue_candidates(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "scan_subtitle_anomalies.py"
    input_dir = tmp_path / "input_subtitles"
    input_dir.mkdir()

    for name in ("sample_01_en.vtt", "sample_05_missing_fields.srt", "sample_07_exception.srt"):
        fixture = kit_root / "fixtures" / name
        (input_dir / name).write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    report_json = tmp_path / "reports" / "scan-report.json"
    report_md = tmp_path / "reports" / "scan-report.md"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(input_dir),
            "--issues-only",
            "--json",
            str(report_json),
            "--markdown",
            str(report_md),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Scanned 2 subtitle files, flagged 2 candidate files." in result.stdout
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["summary"]["total_files"] == 2
    assert payload["summary"]["files_with_issues"] == 2
    assert payload["summary"]["candidate_files"] == 2
    assert payload["summary"]["issue_totals"]["missing_text"] == 1
    assert payload["summary"]["issue_totals"]["end_before_start"] == 1
    assert payload["summary"]["issue_totals"]["out_of_order"] == 1
    assert {record["filename"] for record in payload["records"]} == {
        "sample_05_missing_fields.srt",
        "sample_07_exception.srt",
    }
    markdown = report_md.read_text(encoding="utf-8")
    assert "# Subtitle Anomaly Scan" in markdown
    assert "sample_07_exception.srt" in markdown


def test_scan_subtitle_anomalies_can_downgrade_empty_auto_caption_to_noise(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "scan_subtitle_anomalies.py"
    input_dir = tmp_path / "input_subtitles"
    input_dir.mkdir()

    empty_auto = input_dir / "auto-empty.vtt"
    empty_auto.write_text(
        "\n".join(
            [
                "WEBVTT",
                "",
                "Kind: captions",
                "Language: en",
                "",
                "00:00:00.000 --> 00:00:00.010 align:start position:0%",
                "",
                "",
                "00:00:00.010 --> 00:00:02.000 align:start position:0%",
                "real<00:00:00.500><c> text</c>",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report_json = tmp_path / "scan-noise.json"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(input_dir),
            "--json",
            str(report_json),
            "--ignore-empty-auto-caption",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["summary"]["total_files"] == 1
    assert payload["summary"]["candidate_files"] == 0
    assert payload["summary"]["noise_files"] == 1
    assert payload["records"][0]["category"] == "noise"
    assert payload["records"][0]["summary"]["missing_text"] == 0


def test_scan_subtitle_anomalies_filters_by_language_and_min_lines(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "scan_subtitle_anomalies.py"
    input_dir = tmp_path / "input_subtitles"
    input_dir.mkdir()

    for name in ("sample_01_en.vtt", "sample_02_zh.vtt", "sample_03_dirty.srt"):
        fixture = kit_root / "fixtures" / name
        (input_dir / name).write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    report_json = tmp_path / "scan-filtered.json"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(input_dir),
            "--language",
            "zh",
            "--min-lines",
            "4",
            "--json",
            str(report_json),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["filters"]["languages"] == ["zh"]
    assert payload["filters"]["min_lines"] == 4
    assert payload["summary"]["total_files"] == 1
    assert payload["records"][0]["filename"] == "sample_02_zh.vtt"


def test_scan_subtitle_anomalies_filters_candidate_issue_types(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "scan_subtitle_anomalies.py"
    input_dir = tmp_path / "input_subtitles"
    input_dir.mkdir()

    for name in ("sample_05_missing_fields.srt", "sample_07_exception.srt"):
        fixture = kit_root / "fixtures" / name
        (input_dir / name).write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    report_json = tmp_path / "scan-candidate-issues.json"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(input_dir),
            "--issues-only",
            "--candidate-issue",
            "end_before_start",
            "--candidate-issue",
            "out_of_order",
            "--json",
            str(report_json),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["filters"]["candidate_issues"] == ["end_before_start", "out_of_order"]
    assert payload["summary"]["total_files"] == 1
    assert payload["summary"]["candidate_files"] == 1
    assert payload["records"][0]["filename"] == "sample_07_exception.srt"


def test_scan_subtitle_anomalies_detects_structural_quality_issues(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "scan_subtitle_anomalies.py"
    input_dir = tmp_path / "input_subtitles"
    input_dir.mkdir()

    sample = input_dir / "structural-issues.vtt"
    sample.write_text(
        "\n".join(
            [
                "WEBVTT",
                "",
                "00:00:00.000 --> 00:00:00.050",
                "This repeated subtitle line is long enough to count as a duplicate later.",
                "",
                "00:00:00.060 --> 00:00:00.090",
                "This repeated subtitle line is long enough to count as a duplicate later.",
                "",
                "00:00:45.000 --> 00:00:46.000",
                "This repeated subtitle line is long enough to count as a duplicate later.",
                "",
                "00:00:46.100 --> 00:00:50.000",
                "This cue is intentionally very long so the scanner flags it as a long cue. "
                "It keeps going past a normal subtitle length, adding enough words to exceed "
                "the threshold comfortably and exercise downstream chunking risk detection in "
                "the anomaly report without relying on any external corpus.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report_json = tmp_path / "structural-issues.json"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(input_dir),
            "--issues-only",
            "--json",
            str(report_json),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["summary"]["candidate_files"] == 1
    summary = payload["records"][0]["summary"]
    assert summary["duplicate_cue"] == 2
    assert summary["rapid_repeat"] == 1
    assert summary["large_gap"] == 1
    assert summary["long_cue"] == 1


def test_scan_subtitle_anomalies_respects_threshold_overrides(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "scan_subtitle_anomalies.py"
    input_dir = tmp_path / "input_subtitles"
    input_dir.mkdir()

    sample = input_dir / "structural-issues.vtt"
    sample.write_text(
        "\n".join(
            [
                "WEBVTT",
                "",
                "00:00:00.000 --> 00:00:00.050",
                "This repeated subtitle line is long enough to count as a duplicate later.",
                "",
                "00:00:00.060 --> 00:00:00.090",
                "This repeated subtitle line is long enough to count as a duplicate later.",
                "",
                "00:00:45.000 --> 00:00:46.000",
                "This repeated subtitle line is long enough to count as a duplicate later.",
                "",
                "00:00:46.100 --> 00:00:50.000",
                "This cue is intentionally very long so the scanner flags it as a long cue. "
                "It keeps going past a normal subtitle length, adding enough words to exceed "
                "the threshold comfortably and exercise downstream chunking risk detection in "
                "the anomaly report without relying on any external corpus.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report_json = tmp_path / "threshold-overrides.json"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(input_dir),
            "--issues-only",
            "--duplicate-min-text-len",
            "200",
            "--rapid-repeat-window-seconds",
            "0.005",
            "--large-gap-seconds",
            "100",
            "--long-cue-chars",
            "1000",
            "--json",
            str(report_json),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    assert payload["filters"]["duplicate_min_text_len"] == 200
    assert payload["filters"]["rapid_repeat_window_seconds"] == 0.005
    assert payload["filters"]["large_gap_seconds"] == 100.0
    assert payload["filters"]["long_cue_chars"] == 1000
    assert payload["summary"]["candidate_files"] == 0
    assert payload["summary"]["total_files"] == 0


def test_scan_subtitle_anomalies_errors_when_no_supported_files(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "scan_subtitle_anomalies.py"
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(empty_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "No supported subtitle files found" in result.stderr
