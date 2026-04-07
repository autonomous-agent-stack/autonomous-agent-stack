from __future__ import annotations

from autoresearch.core.services.youtube_errors import YouTubeAgentError, classify_yt_dlp_failure
from autoresearch.shared.models import YouTubeFailedStage, YouTubeFailureKind


def test_classify_yt_dlp_failure_maps_target_kinds() -> None:
    assert classify_yt_dlp_failure("HTTP Error 429: Too Many Requests").failure_kind == YouTubeFailureKind.RATE_LIMITED
    assert classify_yt_dlp_failure("Temporary failure in name resolution").failure_kind == YouTubeFailureKind.NETWORK_FAILURE
    assert classify_yt_dlp_failure(
        "Unable to connect to proxy: Failed to establish a new connection: [Errno 49] Can't assign requested address"
    ).failure_kind == YouTubeFailureKind.NETWORK_FAILURE
    assert classify_yt_dlp_failure("Read timed out while downloading webpage").failure_kind == YouTubeFailureKind.TIMEOUT_FAILURE
    assert classify_yt_dlp_failure("ERROR: [youtube] abc123: Video unavailable").failure_kind == YouTubeFailureKind.VIDEO_UNAVAILABLE
    assert classify_yt_dlp_failure("ERROR: unable to extract uploader id").failure_kind == YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE


def test_youtube_agent_error_api_detail_includes_failed_stage() -> None:
    detail = YouTubeAgentError(
        YouTubeFailureKind.TIMEOUT_FAILURE,
        "yt-dlp timed out",
        retryable=True,
        failed_stage=YouTubeFailedStage.DISCOVERY,
    ).to_api_detail()

    assert detail["error_kind"] == "timeout_failure"
    assert detail["failed_stage"] == "discovery"
    assert detail["retryable"] is True
