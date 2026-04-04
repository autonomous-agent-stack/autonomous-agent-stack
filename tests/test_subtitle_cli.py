from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from subtitle_offline.contract import MediaJobContractSubtitle, SubtitleJobStatus
from subtitle_offline.service import run_subtitle_job

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_SCRIPT = REPO_ROOT / "scripts" / "subtitle_cli.py"
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "subtitles" / "basic-webvtt.vtt"


def _load_cli_module():
    spec = importlib.util.spec_from_file_location("subtitle_cli", CLI_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_subtitle_offline_import_surface_runs_fixture(tmp_path: Path) -> None:
    job = run_subtitle_job(FIXTURE, tmp_path / "artifacts")

    assert isinstance(job, MediaJobContractSubtitle)
    assert job.status is SubtitleJobStatus.DONE
    assert Path(job.output_path).exists()


def test_subtitle_cli_offline_mode_outputs_json(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(CLI_SCRIPT),
            "--input",
            str(FIXTURE),
            "--offline",
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--format",
            "txt",
        ],
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "done"
    assert payload["output_format"] == "txt"
    assert Path(payload["output_path"]).exists()


def test_subtitle_cli_online_mode_uses_fetch_subtitle(tmp_path: Path, monkeypatch, capsys) -> None:
    cli = _load_cli_module()

    def _fake_fetch_subtitle(input_value, output_dir, *, output_format, yt_dlp_bin):
        output_path = Path(output_dir) / "online_clean.srt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("stub\n", encoding="utf-8")
        return MediaJobContractSubtitle(
            url=input_value,
            title="remote-demo",
            output_path=output_path.as_posix(),
            output_format=output_format,
            status=SubtitleJobStatus.DONE,
            metadata={"mode": "online"},
            raw_subtitle_path=None,
            created_at=job_time(),
            updated_at=job_time(),
        )

    monkeypatch.setattr(cli, "fetch_subtitle", _fake_fetch_subtitle)

    exit_code = cli.main(
        [
            "--input",
            "https://www.youtube.com/watch?v=demo",
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--format",
            "srt",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "done"
    assert payload["title"] == "remote-demo"
    assert payload["metadata"]["mode"] == "online"


def job_time():
    from autoresearch.shared.models import utc_now

    return utc_now()
