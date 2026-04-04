from __future__ import annotations

import os
from pathlib import Path
import shutil

import pytest

from subtitle_offline.contract import SubtitleJobStatus, SubtitleOutputFormat
from subtitle_offline.service import fetch_subtitle


@pytest.mark.skipif(
    os.getenv("RUN_SUBTITLE_ONLINE_SMOKE") != "1",
    reason="set RUN_SUBTITLE_ONLINE_SMOKE=1 to enable the real network smoke test",
)
def test_online_smoke_real_ytdlp(tmp_path: Path) -> None:
    url = os.getenv("SUBTITLE_ONLINE_SMOKE_URL", "").strip()
    if not url:
        pytest.skip("set SUBTITLE_ONLINE_SMOKE_URL to a YouTube URL before running the smoke test")
    if shutil.which("yt-dlp") is None:
        pytest.skip("yt-dlp is not available on PATH")

    job = fetch_subtitle(
        youtube_url=url,
        output_dir=tmp_path / "subtitles-smoke",
        output_format=SubtitleOutputFormat.SRT,
    )

    assert job.status is SubtitleJobStatus.DONE
    assert job.url == url
    assert job.title
    assert Path(job.output_path).exists()
    assert Path(job.output_path).read_text(encoding="utf-8").strip() != ""
