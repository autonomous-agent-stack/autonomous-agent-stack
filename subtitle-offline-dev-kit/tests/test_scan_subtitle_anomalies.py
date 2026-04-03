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
