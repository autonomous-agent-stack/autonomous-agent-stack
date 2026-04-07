from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from autoresearch.shared.models import YouTubeFailedStage, YouTubeFailureKind


@dataclass(frozen=True)
class YouTubeFailureClassification:
    failure_kind: YouTubeFailureKind
    retryable: bool = False


class YouTubeAgentError(RuntimeError):
    """Structured YouTube agent failure with stable machine-readable semantics."""

    def __init__(
        self,
        failure_kind: YouTubeFailureKind,
        reason: str,
        *,
        retryable: bool = False,
        failed_stage: YouTubeFailedStage | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(reason)
        self.failure_kind = failure_kind
        self.reason = reason
        self.retryable = retryable
        self.failed_stage = failed_stage
        self.details = details or {}

    def to_api_detail(self) -> dict[str, Any]:
        return {
            "error_kind": self.failure_kind.value,
            "reason": self.reason,
            "retryable": self.retryable,
            "failed_stage": self.failed_stage.value if self.failed_stage else None,
            "details": self.details,
        }


class YouTubeFetchError(YouTubeAgentError):
    """Structured fetch/extractor failure."""


def classify_yt_dlp_failure(stderr: str) -> YouTubeFailureClassification:
    lowered = stderr.lower()
    if any(token in lowered for token in [
        "http error 429",
        "too many requests",
        "sign in to confirm you’re not a bot",
        "sign in to confirm you're not a bot",
    ]):
        return YouTubeFailureClassification(YouTubeFailureKind.RATE_LIMITED, retryable=True)
    if any(token in lowered for token in [
        "failed to resolve",
        "temporary failure in name resolution",
        "name or service not known",
        "nodename nor servname",
        "network is unreachable",
        "connection refused",
        "connection reset by peer",
        "remote end closed connection without response",
        "tlsv1 alert internal error",
        "failed to establish a new connection",
        "can't assign requested address",
        "unable to connect to proxy",
        "proxyerror",
    ]):
        return YouTubeFailureClassification(YouTubeFailureKind.NETWORK_FAILURE, retryable=True)
    if any(token in lowered for token in [
        "timed out",
        "timeout",
        "read timed out",
        "the read operation timed out",
    ]):
        return YouTubeFailureClassification(YouTubeFailureKind.TIMEOUT_FAILURE, retryable=True)
    if any(token in lowered for token in [
        "unsupported url",
        "unsupported or unparseable",
        "incomplete youtube id",
        "unable to recognize tab page",
    ]):
        return YouTubeFailureClassification(YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED)
    if any(token in lowered for token in [
        "video unavailable",
        "private video",
        "this video is unavailable",
        "playback on other websites has been disabled",
        "the uploader has not made this video available",
    ]):
        return YouTubeFailureClassification(YouTubeFailureKind.VIDEO_UNAVAILABLE)
    return YouTubeFailureClassification(YouTubeFailureKind.YT_DLP_EXTRACTOR_FAILURE)
