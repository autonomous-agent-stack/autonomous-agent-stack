from __future__ import annotations

import pytest

from autoresearch.core.services.youtube_subtitle_summary import YouTubeSubtitleSummaryService
from autoresearch.shared.youtube_subtitle_summary_contract import (
    YouTubeSubtitleSummaryRequest,
    YouTubeSubtitleSummaryStatus,
)


def test_rejects_non_youtube_url() -> None:
    service = YouTubeSubtitleSummaryService()
    request = YouTubeSubtitleSummaryRequest(
        youtube_url="https://example.com/watch?v=abc",
        subtitle_text="hello",
    )

    result = service.summarize(request)

    assert result.summary_status == YouTubeSubtitleSummaryStatus.FAILED
    assert result.error_kind == "unsupported_url"


def test_requires_subtitle_text() -> None:
    service = YouTubeSubtitleSummaryService()
    request = YouTubeSubtitleSummaryRequest(youtube_url="https://www.youtube.com/watch?v=abc")

    result = service.summarize(request)

    assert result.summary_status == YouTubeSubtitleSummaryStatus.FAILED
    assert result.error_kind == "subtitle_text_required"


def test_summarizes_webvtt_text() -> None:
    service = YouTubeSubtitleSummaryService()
    request = YouTubeSubtitleSummaryRequest(
        youtube_url="https://www.youtube.com/watch?v=abc",
        title="Demo",
        subtitle_text="""WEBVTT

00:00:01.000 --> 00:00:04.000
首先我们介绍这个主题。

00:00:05.000 --> 00:00:08.000
但是真正重要的是执行路径。

00:00:09.000 --> 00:00:12.000
最后总结关键结论。
""",
        max_key_points=2,
    )

    result = service.summarize(request)

    assert result.summary_status == YouTubeSubtitleSummaryStatus.DONE
    assert result.title == "Demo"
    assert result.summary is not None
    assert len(result.key_points) == 2
    assert result.metadata["caption_segments"] == 3


def test_narrative_summary_style() -> None:
    service = YouTubeSubtitleSummaryService()
    request = YouTubeSubtitleSummaryRequest(
        youtube_url="https://youtu.be/abc",
        subtitle_text="First point. Second point. Final summary.",
        summary_style="narrative",
        max_key_points=2,
    )

    result = service.summarize(request)

    assert result.summary_status == YouTubeSubtitleSummaryStatus.DONE
    assert result.summary is not None
    assert not result.summary.startswith("- ")


def test_request_rejects_relative_url() -> None:
    with pytest.raises(ValueError, match="youtube_url must be http or https"):
        YouTubeSubtitleSummaryRequest(youtube_url="youtube.com/watch?v=abc")
