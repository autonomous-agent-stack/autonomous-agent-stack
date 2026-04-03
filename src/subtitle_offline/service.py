from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Callable

from autoresearch.core.services.media_jobs_subtitle import (
    MacSubtitleJobService,
    clean_subtitle_file,
    run_subtitle_job,
)
from subtitle_offline.contract import MediaJobContractSubtitle, SubtitleOutputFormat


def fetch_subtitle(
    youtube_url: str,
    output_dir: str | Path,
    *,
    output_format: SubtitleOutputFormat | str = SubtitleOutputFormat.SRT,
    yt_dlp_bin: str = "yt-dlp",
    allowed_domains: set[str] | None = None,
    command_runner: Callable[[list[str]], subprocess.CompletedProcess[str]] | None = None,
) -> MediaJobContractSubtitle:
    service = MacSubtitleJobService(
        yt_dlp_bin=yt_dlp_bin,
        allowed_domains=allowed_domains,
        command_runner=command_runner,
    )
    return service.fetch_subtitle(
        youtube_url,
        output_dir,
        output_format=SubtitleOutputFormat(output_format),
    )


__all__ = [
    "MacSubtitleJobService",
    "clean_subtitle_file",
    "fetch_subtitle",
    "run_subtitle_job",
]
