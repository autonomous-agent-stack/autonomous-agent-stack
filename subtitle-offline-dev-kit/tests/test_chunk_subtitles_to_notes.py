from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_chunk_subtitles_writes_notes_ready_jsonl(tmp_path: Path) -> None:
    kit_root = Path(__file__).resolve().parents[1]
    script = kit_root / "scripts" / "chunk_subtitles_to_notes.py"
    input_dir = tmp_path / "input_subtitles"
    input_dir.mkdir()

    sample_fixture = kit_root / "fixtures" / "sample_02_zh.vtt"
    (input_dir / sample_fixture.name).write_text(
        sample_fixture.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    output_dir = tmp_path / "notes_ready"
    output_file = output_dir / "chunks.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input-dir",
            str(input_dir),
            "--output-dir",
            str(output_dir),
            "--output-file",
            str(output_file),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_file.exists()

    records = [
        json.loads(line)
        for line in output_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 4
    assert all(record["source_file"] == "sample_02_zh.vtt" for record in records)
    assert all(record["source_language"] == "zh" for record in records)
    assert all(record["start"] <= record["end"] for record in records)
    assert all(record["source_checksum"] for record in records)
    assert all(record["chunk_checksum"] for record in records)
