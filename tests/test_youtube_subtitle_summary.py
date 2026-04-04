from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from autoresearch.core.services.youtube_subtitle_summary import YoutubeSubtitleSummaryService
from autoresearch.shared.media_job_contract_subtitle import MediaJobContractSubtitle, SubtitleJobStatus, SubtitleOutputFormat
from autoresearch.shared.youtube_subtitle_summary_contract import (
    YoutubeSubtitleSummaryRequest,
    YoutubeSubtitleSummaryStatus,
)


def _subtitle_result(
    *,
    output_path: Path,
    error: str | None = None,
    status: SubtitleJobStatus = SubtitleJobStatus.DONE,
    title: str = "demo-video",
    metadata: dict[str, object] | None = None,
) -> MediaJobContractSubtitle:
    return MediaJobContractSubtitle(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        title=title,
        output_path=output_path.as_posix(),
        output_format=SubtitleOutputFormat.TXT,
        status=status,
        metadata=metadata or {"source_kind": "yt-dlp"},
        raw_subtitle_path=(output_path.parent / "raw.srt").as_posix(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        error=error,
    )


def test_youtube_subtitle_summary_service_builds_structured_summary(tmp_path: Path) -> None:
    clean_path = tmp_path / "clean.txt"
    clean_path.write_text(
        "第一句是主题。第二句解释原因。\n"
        "第三句给出结论。第四句补充背景。",
        encoding="utf-8",
    )

    def _fetcher(*args, **kwargs) -> MediaJobContractSubtitle:
        return _subtitle_result(output_path=clean_path)

    service = YoutubeSubtitleSummaryService(subtitle_fetcher=_fetcher)
    result = service.summarize(
        YoutubeSubtitleSummaryRequest(
            youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            output_dir=tmp_path.as_posix(),
            max_key_points=3,
        )
    )

    assert result.subtitle_status is SubtitleJobStatus.DONE
    assert result.summary_status is YoutubeSubtitleSummaryStatus.DONE
    assert result.error_kind is None
    assert result.source_url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert result.subtitle_result is not None
    assert result.summary is not None
    assert result.key_points
    assert result.metadata["summary_reason"] == "subtitle_ok"
    assert result.metadata["captions_segments"] >= 2
    assert "第一句是主题" in result.summary


def test_youtube_subtitle_summary_service_rejects_non_youtube_url(tmp_path: Path) -> None:
    service = YoutubeSubtitleSummaryService()
    result = service.summarize(
        YoutubeSubtitleSummaryRequest(
            youtube_url="https://example.com/watch?v=abc",
            output_dir=tmp_path.as_posix(),
        )
    )

    assert result.subtitle_status is SubtitleJobStatus.FAILED
    assert result.summary_status is YoutubeSubtitleSummaryStatus.FAILED
    assert result.error_kind == "unsupported_url"
    assert result.summary is None
    assert result.subtitle_result is None


@pytest.mark.parametrize(
    ("error_text", "metadata", "expected_kind"),
    [
        ("HTTP Error 429: Too Many Requests", {}, "rate_limited"),
        ("SSL: WRONG_VERSION_NUMBER", {}, "network_ssl"),
        ("did not produce an .srt file", {}, "no_subtitle_output"),
        ("unknown transport failure", {}, "unknown_download_error"),
        ("", {"download_warning": "too many requests"}, "rate_limited"),
    ],
)
def test_youtube_subtitle_summary_service_classifies_subtitle_failures(
    tmp_path: Path,
    error_text: str,
    metadata: dict[str, object],
    expected_kind: str,
) -> None:
    clean_path = tmp_path / "clean.txt"
    clean_path.write_text("unused", encoding="utf-8")

    def _fetcher(*args, **kwargs) -> MediaJobContractSubtitle:
        return _subtitle_result(
            output_path=clean_path,
            status=SubtitleJobStatus.FAILED,
            error=error_text or None,
            metadata=metadata,
        )

    service = YoutubeSubtitleSummaryService(subtitle_fetcher=_fetcher)
    result = service.summarize(
        YoutubeSubtitleSummaryRequest(
            youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            output_dir=tmp_path.as_posix(),
        )
    )

    assert result.subtitle_status is SubtitleJobStatus.FAILED
    assert result.summary_status is YoutubeSubtitleSummaryStatus.FAILED
    assert result.error_kind == expected_kind
    assert result.summary is None
    assert result.subtitle_result is not None


def test_youtube_subtitle_summary_render_message_is_fail_closed(tmp_path: Path) -> None:
    clean_path = tmp_path / "clean.txt"
    clean_path.write_text("unused", encoding="utf-8")

    def _fetcher(*args, **kwargs) -> MediaJobContractSubtitle:
        return _subtitle_result(
            output_path=clean_path,
            status=SubtitleJobStatus.FAILED,
            error="HTTP Error 429: Too Many Requests",
        )

    service = YoutubeSubtitleSummaryService(subtitle_fetcher=_fetcher)
    result = service.summarize(
        YoutubeSubtitleSummaryRequest(
            youtube_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            output_dir=tmp_path.as_posix(),
        )
    )

    rendered = service.render_telegram_message(result)
    assert "subtitle_status:" in rendered
    assert "summary_status:" in rendered
    assert "error_kind:" in rendered
