from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from pydantic import Field

from autoresearch.shared.models import StrictModel
from subtitle_offline.contract import MediaJobContractSubtitle, SubtitleOutputFormat
from subtitle_offline.service import fetch_subtitle, run_subtitle_job


router = APIRouter(prefix="/api/v1/subtitle", tags=["subtitle-offline"])


class OfflineSubtitleRequest(StrictModel):
    input_path: str = Field(..., min_length=1)
    output_dir: str = "artifacts/subtitles-api"
    output_format: SubtitleOutputFormat = SubtitleOutputFormat.SRT


class OnlineSubtitleRequest(StrictModel):
    url: str = Field(..., min_length=1)
    output_dir: str = "artifacts/subtitles-api"
    output_format: SubtitleOutputFormat = SubtitleOutputFormat.SRT
    yt_dlp_bin: str = "yt-dlp"


@router.post("/offline", response_model=MediaJobContractSubtitle)
def subtitle_offline(payload: OfflineSubtitleRequest) -> MediaJobContractSubtitle:
    return run_subtitle_job(
        raw_path=Path(payload.input_path),
        output_dir=Path(payload.output_dir),
        output_format=payload.output_format,
    )


@router.post("/online", response_model=MediaJobContractSubtitle)
def subtitle_online(payload: OnlineSubtitleRequest) -> MediaJobContractSubtitle:
    return fetch_subtitle(
        youtube_url=payload.url,
        output_dir=payload.output_dir,
        output_format=payload.output_format,
        yt_dlp_bin=payload.yt_dlp_bin,
    )
