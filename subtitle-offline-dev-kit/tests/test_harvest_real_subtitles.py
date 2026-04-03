from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_harvest_real_subtitles_writes_fixture_copies_and_manifests(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "harvest_real_subtitles.py"
    input_dir = tmp_path / "input_subtitles"
    input_dir.mkdir()

    sample_en = kit_root / "fixtures" / "sample_01_en.vtt"
    sample_dirty = kit_root / "fixtures" / "sample_07_exception.srt"
    (input_dir / sample_en.name).write_text(sample_en.read_text(encoding="utf-8"), encoding="utf-8")
    (input_dir / sample_dirty.name).write_text(
        sample_dirty.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    output_dir = tmp_path / "fixtures" / "harvested"
    report_json = tmp_path / "reports" / "harvested-manifest.json"
    report_md = tmp_path / "reports" / "harvested-manifest.md"

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--manifest-json",
            str(report_json),
            "--manifest-md",
            str(report_md),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_dir.joinpath(sample_en.name).exists()
    assert output_dir.joinpath(sample_dirty.name).exists()
    assert report_json.exists()
    assert report_md.exists()

    manifest = json.loads(report_json.read_text(encoding="utf-8"))
    assert manifest["summary"]["total_files"] == 2
    assert manifest["summary"]["copied_files"] == 2
    assert {record["filename"] for record in manifest["records"]} == {
        "sample_01_en.vtt",
        "sample_07_exception.srt",
    }
    assert all("checksum" in record for record in manifest["records"])
    assert any("end_before_start" in record["anomalies"] for record in manifest["records"])
