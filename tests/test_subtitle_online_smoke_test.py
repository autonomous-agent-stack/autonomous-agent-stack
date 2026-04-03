from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from subtitle_offline.contract import MediaJobContractSubtitle, SubtitleJobStatus, SubtitleOutputFormat
from autoresearch.shared.models import utc_now

REPO_ROOT = Path(__file__).resolve().parents[1]
SMOKE_SCRIPT = REPO_ROOT / "scripts" / "subtitle_online_smoke_test.py"


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("subtitle_online_smoke_test", SMOKE_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _job(tmp_path: Path, *, status: SubtitleJobStatus) -> MediaJobContractSubtitle:
    output_path = tmp_path / "online_clean.srt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n", encoding="utf-8")
    return MediaJobContractSubtitle(
        url="https://www.youtube.com/watch?v=demo",
        title="remote-demo",
        output_path=output_path.as_posix(),
        output_format=SubtitleOutputFormat.SRT,
        status=status,
        metadata={"mode": "smoke"},
        raw_subtitle_path=(tmp_path / "remote.srt").as_posix(),
        created_at=utc_now(),
        updated_at=utc_now(),
        error=None if status is SubtitleJobStatus.DONE else "boom",
    )


def test_online_smoke_script_emits_json_for_done_result(tmp_path: Path, monkeypatch, capsys) -> None:
    smoke = _load_smoke_module()

    def _fake_fetch_subtitle(*, youtube_url, output_dir, output_format, yt_dlp_bin):
        assert youtube_url == "https://www.youtube.com/watch?v=demo"
        assert Path(output_dir) == tmp_path / "artifacts"
        assert output_format is SubtitleOutputFormat.TXT
        assert yt_dlp_bin == "yt-dlp"
        job = _job(tmp_path, status=SubtitleJobStatus.DONE)
        return job.model_copy(update={"output_format": SubtitleOutputFormat.TXT})

    monkeypatch.setattr(smoke, "fetch_subtitle", _fake_fetch_subtitle)

    exit_code = smoke.main(
        [
            "--url",
            "https://www.youtube.com/watch?v=demo",
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--format",
            "txt",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["status"] == "done"
    assert payload["title"] == "remote-demo"


def test_online_smoke_script_raises_for_failed_result(tmp_path: Path, monkeypatch) -> None:
    smoke = _load_smoke_module()

    def _fake_fetch_subtitle(*, youtube_url, output_dir, output_format, yt_dlp_bin):
        return _job(tmp_path, status=SubtitleJobStatus.FAILED)

    monkeypatch.setattr(smoke, "fetch_subtitle", _fake_fetch_subtitle)

    with pytest.raises(RuntimeError, match="boom"):
        smoke.main(
            [
                "--url",
                "https://www.youtube.com/watch?v=demo",
                "--output-dir",
                str(tmp_path / "artifacts"),
            ]
        )


def test_online_smoke_script_classifies_rate_limit_warning_on_done_result(tmp_path: Path) -> None:
    smoke = _load_smoke_module()
    job = _job(tmp_path, status=SubtitleJobStatus.DONE).model_copy(
        update={
            "metadata": {
                "download_warning": "ERROR: Unable to download video subtitles for 'ab-en': HTTP Error 429: Too Many Requests"
            }
        }
    )

    classified = smoke._classify_result(job)

    assert classified.metadata["error_kind"] == "rate_limited"
    assert "download_warning" in classified.metadata


def test_online_smoke_script_classifies_ssl_failure(tmp_path: Path) -> None:
    smoke = _load_smoke_module()
    job = _job(tmp_path, status=SubtitleJobStatus.FAILED).model_copy(
        update={"error": "SSL: UNEXPECTED_EOF_WHILE_READING"}
    )

    classified = smoke._classify_result(job)

    assert classified.metadata["error_kind"] == "network_ssl"
    assert classified.metadata["download_warning"] == "yt-dlp failed with an SSL/network transport error"


def test_online_smoke_script_writes_json_file(tmp_path: Path, monkeypatch, capsys) -> None:
    smoke = _load_smoke_module()
    json_out = tmp_path / "result.json"

    def _fake_fetch_subtitle(*, youtube_url, output_dir, output_format, yt_dlp_bin):
        return _job(tmp_path, status=SubtitleJobStatus.DONE)

    monkeypatch.setattr(smoke, "fetch_subtitle", _fake_fetch_subtitle)

    exit_code = smoke.main(
        [
            "--url",
            "https://www.youtube.com/watch?v=demo",
            "--output-dir",
            str(tmp_path / "artifacts"),
            "--json-out",
            str(json_out),
        ]
    )

    assert exit_code == 0
    assert json_out.exists()
    payload = json.loads(json_out.read_text(encoding="utf-8"))
    assert payload["status"] == "done"
    assert payload["title"] == "remote-demo"
