from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_check_subtitle_contract_help() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts" / "check_subtitle_contract.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "subtitle contract checker" in result.stdout.lower()
    assert "--json" in result.stdout
    assert "--markdown" in result.stdout
    assert "--report-json" in result.stdout
    assert "--report-md" in result.stdout
    assert "--strict" in result.stdout
    assert "--no-strict" in result.stdout


def test_check_subtitle_contract_reports_fixture_summary_and_fails_on_anomalies() -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "check_subtitle_contract.py"
    fixtures = kit_root / "fixtures"
    result = subprocess.run(
        [sys.executable, str(script), str(fixtures)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "Checking subtitle contract" in result.stdout
    assert "sample_05_missing_fields.srt" in result.stdout
    assert "missing_text=1" in result.stdout
    assert "sample_07_exception.srt" in result.stdout
    assert "end_before_start=1" in result.stdout
    assert "out_of_order=1" in result.stdout


def test_check_subtitle_contract_returns_zero_for_clean_directory(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "check_subtitle_contract.py"
    clean_fixture = kit_root / "fixtures" / "sample_01_en.vtt"
    copied_fixture = tmp_path / clean_fixture.name
    copied_fixture.write_text(clean_fixture.read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(script), str(tmp_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "sample_01_en.vtt: total_lines=3, missing_text=0, end_before_start=0, out_of_order=0" in result.stdout


def test_check_subtitle_contract_writes_json_report(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "check_subtitle_contract.py"
    fixtures = kit_root / "fixtures"
    report_path = tmp_path / "subtitle-report.json"

    result = subprocess.run(
        [sys.executable, str(script), str(fixtures), "--json", str(report_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert report_path.exists()

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "issues"
    assert report["exit_code"] == 1
    assert report["summary"]["checked_files"] == 7
    assert report["summary"]["issue_totals"]["missing_text"] == 1
    assert report["summary"]["issue_totals"]["end_before_start"] == 1
    assert report["summary"]["issue_totals"]["out_of_order"] == 1


def test_check_subtitle_contract_accepts_report_aliases(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "check_subtitle_contract.py"
    fixtures = kit_root / "fixtures"
    json_path = tmp_path / "batch_check_report.json"
    markdown_path = tmp_path / "batch_check_report.md"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            str(fixtures),
            "--report-json",
            str(json_path),
            "--report-md",
            str(markdown_path),
            "--strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert json_path.exists()
    assert markdown_path.exists()


def test_check_subtitle_contract_no_strict_returns_zero_for_anomalies(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "check_subtitle_contract.py"
    fixtures = kit_root / "fixtures"
    report_path = tmp_path / "subtitle-report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            str(fixtures),
            "--json",
            str(report_path),
            "--no-strict",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert report_path.exists()


def test_check_subtitle_contract_writes_markdown_report(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "check_subtitle_contract.py"
    clean_fixture = kit_root / "fixtures" / "sample_01_en.vtt"
    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()
    (clean_dir / clean_fixture.name).write_text(clean_fixture.read_text(encoding="utf-8"), encoding="utf-8")
    report_path = tmp_path / "subtitle-report.md"

    result = subprocess.run(
        [sys.executable, str(script), str(clean_dir), "--markdown", str(report_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert report_path.exists()

    report = report_path.read_text(encoding="utf-8")
    assert "# Subtitle Contract Report" in report
    assert "| File | Status | total_lines | missing_text | end_before_start | out_of_order | Error |" in report
    assert "| sample_01_en.vtt | ok | 3 | 0 | 0 | 0 |  |" in report
