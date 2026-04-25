"""Tests for youtube_errors — error classification, serialization, hierarchy."""
from __future__ import annotations

import pytest

from autoresearch.core.services.youtube_errors import (
    YouTubeAgentError,
    YouTubeFailureClassification,
    YouTubeFetchError,
    classify_yt_dlp_failure,
)
from autoresearch.shared.models import YouTubeFailedStage, YouTubeFailureKind


class TestYouTubeFailureClassification:
    def test_frozen_dataclass(self) -> None:
        cls = YouTubeFailureClassification(YouTubeFailureKind.NETWORK_FAILURE, retryable=True)
        assert cls.failure_kind == YouTubeFailureKind.NETWORK_FAILURE
        assert cls.retryable is True

    def test_default_not_retryable(self) -> None:
        cls = YouTubeFailureClassification(YouTubeFailureKind.VIDEO_UNAVAILABLE)
        assert cls.retryable is False


class TestYouTubeAgentError:
    def test_basic_construction(self) -> None:
        err = YouTubeAgentError(
            YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE,
            "extractor blew up",
        )
        assert str(err) == "extractor blew up"
        assert err.failure_kind == YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE
        assert err.retryable is False
        assert err.failed_stage is None
        assert err.details == {}

    def test_full_construction(self) -> None:
        err = YouTubeAgentError(
            YouTubeFailureKind.RATE_LIMITED,
            "429 too many",
            retryable=True,
            failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
            details={"url": "https://youtube.com/watch?v=abc"},
        )
        assert err.retryable is True
        assert err.failed_stage == YouTubeFailedStage.TRANSCRIPT_FETCH
        assert err.details["url"] == "https://youtube.com/watch?v=abc"

    def test_to_api_detail(self) -> None:
        err = YouTubeAgentError(
            YouTubeFailureKind.NETWORK_FAILURE,
            "connection refused",
            retryable=True,
            failed_stage=YouTubeFailedStage.METADATA_FETCH,
            details={"retries": 3},
        )
        detail = err.to_api_detail()
        assert detail["error_kind"] == "network_failure"
        assert detail["reason"] == "connection refused"
        assert detail["retryable"] is True
        assert detail["failed_stage"] == "metadata_fetch"
        assert detail["details"]["retries"] == 3

    def test_to_api_detail_no_stage(self) -> None:
        err = YouTubeAgentError(YouTubeFailureKind.TIMEOUT_FAILURE, "timed out")
        detail = err.to_api_detail()
        assert detail["failed_stage"] is None


class TestYouTubeFetchError:
    def test_inherits_from_agent_error(self) -> None:
        err = YouTubeFetchError(YouTubeFailureKind.NETWORK_FAILURE, "DNS fail")
        assert isinstance(err, YouTubeAgentError)
        assert isinstance(err, RuntimeError)

    def test_preserves_fields(self) -> None:
        err = YouTubeFetchError(
            YouTubeFailureKind.RATE_LIMITED,
            "429",
            retryable=True,
            details={"status_code": 429},
        )
        assert err.retryable is True
        assert err.details["status_code"] == 429


class TestClassifyYtDlpFailure:
    def test_rate_limited_429(self) -> None:
        result = classify_yt_dlp_failure("HTTP Error 429: Too Many Requests")
        assert result.failure_kind == YouTubeFailureKind.RATE_LIMITED
        assert result.retryable is True

    def test_rate_limited_bot_check(self) -> None:
        result = classify_yt_dlp_failure("Sign in to confirm you're not a bot")
        assert result.failure_kind == YouTubeFailureKind.RATE_LIMITED
        assert result.retryable is True

    def test_network_dns_failure(self) -> None:
        result = classify_yt_dlp_failure("Failed to resolve hostname")
        assert result.failure_kind == YouTubeFailureKind.NETWORK_FAILURE
        assert result.retryable is True

    def test_network_connection_refused(self) -> None:
        result = classify_yt_dlp_failure("Connection refused by remote host")
        assert result.failure_kind == YouTubeFailureKind.NETWORK_FAILURE
        assert result.retryable is True

    def test_network_proxy_error(self) -> None:
        result = classify_yt_dlp_failure("Unable to connect to proxy server")
        assert result.failure_kind == YouTubeFailureKind.NETWORK_FAILURE
        assert result.retryable is True

    def test_timeout(self) -> None:
        result = classify_yt_dlp_failure("Read timed out after 30 seconds")
        assert result.failure_kind == YouTubeFailureKind.TIMEOUT_FAILURE
        assert result.retryable is True

    def test_unsupported_url(self) -> None:
        result = classify_yt_dlp_failure("Unsupported URL format")
        assert result.failure_kind == YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED
        assert result.retryable is False

    def test_video_unavailable(self) -> None:
        result = classify_yt_dlp_failure("Video unavailable. This video is no longer available")
        assert result.failure_kind == YouTubeFailureKind.VIDEO_UNAVAILABLE
        assert result.retryable is False

    def test_private_video(self) -> None:
        result = classify_yt_dlp_failure("Private video. Sign in to access")
        assert result.failure_kind == YouTubeFailureKind.VIDEO_UNAVAILABLE

    def test_unknown_falls_back_to_extractor_failure(self) -> None:
        result = classify_yt_dlp_failure("Some completely unknown error message")
        assert result.failure_kind == YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE
        assert result.retryable is False

    def test_case_insensitive(self) -> None:
        result = classify_yt_dlp_failure("HTTP ERROR 429: TOO MANY REQUESTS")
        assert result.failure_kind == YouTubeFailureKind.RATE_LIMITED

    def test_empty_stderr_falls_back(self) -> None:
        result = classify_yt_dlp_failure("")
        assert result.failure_kind == YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE
