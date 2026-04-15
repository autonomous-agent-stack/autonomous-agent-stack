from __future__ import annotations

from pathlib import Path

from autoresearch.core.repositories.youtube import InMemoryYouTubeRepository
from autoresearch.core.services.standby_youtube_bridge import StandbyYouTubeBridgeService
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.youtube_digest import YouTubeDigestService
from autoresearch.core.services.youtube_errors import YouTubeAgentError
from autoresearch.core.services.youtube_fetcher import (
    YouTubeSourceDescriptor,
    YouTubeTranscriptPayload,
    YouTubeVideoSnapshot,
)
from autoresearch.shared.models import (
    JobStatus,
    YouTubeFailedStage,
    YouTubeFailureKind,
    YouTubeResultKind,
    YouTubeSubscriptionCheckRequest,
    YouTubeSubscriptionCreateRequest,
    YouTubeTargetKind,
)


class FakeBridgeFetcher:
    def __init__(self) -> None:
        self._descriptor = YouTubeSourceDescriptor(
            normalized_url="https://www.youtube.com/watch?v=video-001",
            target_kind=YouTubeTargetKind.VIDEO,
            external_id="video-001",
            title="Demo Video",
        )
        self._snapshot = YouTubeVideoSnapshot(
            video_id="video-001",
            source_url="https://www.youtube.com/watch?v=video-001",
            title="Demo Video",
            channel_id="channel-001",
            channel_title="Demo Channel",
            description="This video explains how to bridge standby to the YouTube bounded context.",
        )

    def inspect_source(self, url: str) -> YouTubeSourceDescriptor:
        if url != "https://www.youtube.com/watch?v=video-001":
            raise YouTubeAgentError(
                YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED,
                f"unsupported source: {url}",
                failed_stage=YouTubeFailedStage.DISCOVERY,
            )
        return self._descriptor

    def discover_videos(self, source_url: str, target_kind: YouTubeTargetKind, *, limit: int = 5) -> list[YouTubeVideoSnapshot]:
        assert target_kind == YouTubeTargetKind.VIDEO
        return [self._snapshot]

    def fetch_video_metadata(self, source_url: str) -> YouTubeVideoSnapshot:
        return self._snapshot

    def fetch_transcript(
        self,
        source_url: str,
        *,
        preferred_languages: list[str],
        include_auto_generated: bool,
    ) -> YouTubeTranscriptPayload:
        raise YouTubeAgentError(
            YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE,
            "no subtitles or auto captions are available for this video",
            failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
        )


def _build_bridge(tmp_path: Path) -> tuple[StandbyYouTubeBridgeService, YouTubeAgentService]:
    service = YouTubeAgentService(
        repository=InMemoryYouTubeRepository(),
        repo_root=tmp_path,
        fetcher=FakeBridgeFetcher(),
        digest_service=YouTubeDigestService(),
    )
    return StandbyYouTubeBridgeService(youtube_service=service), service


def test_bridge_subscribe_is_idempotent(tmp_path: Path) -> None:
    bridge, _ = _build_bridge(tmp_path)

    first = bridge.execute_payload(
        {
            "action": "subscribe",
            "target_url": "https://www.youtube.com/watch?v=video-001",
        }
    )
    second = bridge.execute_payload(
        {
            "action": "subscribe",
            "target_url": "https://www.youtube.com/watch?v=video-001",
        }
    )

    assert first.success is True
    assert second.success is True
    assert first.subscription_id == second.subscription_id
    assert first.status == JobStatus.COMPLETED
    assert second.result_kind == YouTubeResultKind.SUCCESS


def test_bridge_rejects_invalid_action(tmp_path: Path) -> None:
    bridge, _ = _build_bridge(tmp_path)

    result = bridge.execute_payload({"action": "not_real"})

    assert result.success is False
    assert result.status == JobStatus.FAILED
    assert result.error_kind == "invalid_action"
    assert result.failed_stage == "request_validation"


def test_bridge_rejects_missing_subscription_as_invalid_target(tmp_path: Path) -> None:
    bridge, _ = _build_bridge(tmp_path)

    result = bridge.execute_payload(
        {
            "action": "check",
            "subscription_id": "missing-subscription",
        }
    )

    assert result.success is False
    assert result.status == JobStatus.FAILED
    assert result.error_kind == "invalid_target"
    assert result.reason == "subscription not found: missing-subscription"


def test_bridge_propagates_youtube_failure_with_run_context(tmp_path: Path) -> None:
    bridge, service = _build_bridge(tmp_path)
    subscription = service.subscribe(
        YouTubeSubscriptionCreateRequest(
            source_url="https://www.youtube.com/watch?v=video-001",
        )
    )
    service.check_subscription(
        subscription.subscription_id,
        YouTubeSubscriptionCheckRequest(limit=1),
    )

    result = bridge.execute_payload(
        {
            "action": "fetch_transcript",
            "video_id": "video-001",
        }
    )

    assert result.success is False
    assert result.status == JobStatus.FAILED
    assert result.result_kind == YouTubeResultKind.FAILED
    assert result.error_kind == "transcript_unavailable"
    assert result.failed_stage == "transcript_fetch"
    assert result.video_id == "video-001"
    assert result.transcript_id is not None
    assert result.run_id is not None
