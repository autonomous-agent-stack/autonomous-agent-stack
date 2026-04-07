from __future__ import annotations

from pathlib import Path

import pytest

from autoresearch.core.repositories.youtube import InMemoryYouTubeRepository
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.youtube_digest import YouTubeDigestService
from autoresearch.core.services.youtube_errors import YouTubeAgentError
from autoresearch.core.services.youtube_fetcher import (
    YouTubeSourceDescriptor,
    YouTubeTranscriptPayload,
    YouTubeVideoSnapshot,
)
from autoresearch.shared.models import (
    YouTubeDigestCreateRequest,
    YouTubeFailedStage,
    YouTubeFailureKind,
    YouTubeQuestionRequest,
    YouTubeResultKind,
    YouTubeRunKind,
    YouTubeSubscriptionCheckRequest,
    YouTubeSubscriptionCreateRequest,
    YouTubeSubscriptionImportItem,
    YouTubeSubscriptionImportRequest,
    YouTubeSubscriptionStatus,
    YouTubeSubscriptionUpdateRequest,
    YouTubeTargetKind,
    YouTubeTranscriptCreateRequest,
    YouTubeTranscriptSource,
)


class FakeYouTubeFetcher:
    def __init__(self) -> None:
        self._descriptors = {
            "https://www.youtube.com/@demo": YouTubeSourceDescriptor(
                normalized_url="https://www.youtube.com/@demo",
                target_kind=YouTubeTargetKind.CHANNEL,
                external_id="demo",
                title="Demo Channel",
            ),
            "https://www.youtube.com/@demo/": YouTubeSourceDescriptor(
                normalized_url="https://www.youtube.com/@demo",
                target_kind=YouTubeTargetKind.CHANNEL,
                external_id="demo",
                title="Demo Channel",
            ),
            "https://www.youtube.com/playlist?list=PL_DEMO": YouTubeSourceDescriptor(
                normalized_url="https://www.youtube.com/playlist?list=PL_DEMO",
                target_kind=YouTubeTargetKind.PLAYLIST,
                external_id="PL_DEMO",
                title="Demo Playlist",
            ),
            "https://www.youtube.com/watch?v=video-001": YouTubeSourceDescriptor(
                normalized_url="https://www.youtube.com/watch?v=video-001",
                target_kind=YouTubeTargetKind.VIDEO,
                external_id="video-001",
                title="Video 001",
            ),
            "https://www.youtube.com/watch?v=video-no-transcript": YouTubeSourceDescriptor(
                normalized_url="https://www.youtube.com/watch?v=video-no-transcript",
                target_kind=YouTubeTargetKind.VIDEO,
                external_id="video-no-transcript",
                title="Video No Transcript",
            ),
        }
        self._discoveries = {
            "https://www.youtube.com/@demo": [
                YouTubeVideoSnapshot(
                    video_id="video-001",
                    source_url="https://www.youtube.com/watch?v=video-001",
                    title="Agent Systems 101",
                    channel_id="channel-001",
                    channel_title="Demo Channel",
                    description="This is a walkthrough about building agent systems.",
                )
            ],
            "https://www.youtube.com/playlist?list=PL_DEMO": [
                YouTubeVideoSnapshot(
                    video_id="playlist-video-001",
                    source_url="https://www.youtube.com/watch?v=playlist-video-001",
                    title="Playlist Entry 001",
                    channel_id="channel-001",
                    channel_title="Demo Channel",
                    description="This playlist entry explains deterministic pipelines.",
                )
            ],
            "https://www.youtube.com/watch?v=video-001": [
                YouTubeVideoSnapshot(
                    video_id="video-001",
                    source_url="https://www.youtube.com/watch?v=video-001",
                    title="Agent Systems 101",
                    channel_id="channel-001",
                    channel_title=None,
                    description="This is a walkthrough about building agent systems.",
                )
            ],
            "https://www.youtube.com/watch?v=video-no-transcript": [
                YouTubeVideoSnapshot(
                    video_id="video-no-transcript",
                    source_url="https://www.youtube.com/watch?v=video-no-transcript",
                    title="Transcript Missing",
                    channel_id="channel-001",
                    channel_title="Demo Channel",
                    description="This item intentionally has no transcript.",
                )
            ],
        }
        self._metadata = {
            "https://www.youtube.com/watch?v=video-001": YouTubeVideoSnapshot(
                video_id="video-001",
                source_url="https://www.youtube.com/watch?v=video-001",
                title="Agent Systems 101",
                channel_id="channel-001",
                channel_title="Demo Channel",
                description=(
                    "Build a deterministic YouTube agent with clear state, transcript handling, "
                    "and explainable reruns."
                ),
            ),
            "https://www.youtube.com/watch?v=playlist-video-001": self._discoveries["https://www.youtube.com/playlist?list=PL_DEMO"][0],
            "https://www.youtube.com/watch?v=video-no-transcript": self._discoveries["https://www.youtube.com/watch?v=video-no-transcript"][0],
        }
        self._transcripts = {
            "https://www.youtube.com/watch?v=video-001": YouTubeTranscriptPayload(
                language="en",
                source=YouTubeTranscriptSource.AUTOMATIC,
                content=(
                    "Agent systems need clear state boundaries.\n"
                    "A YouTube agent should separate fetching, summarizing, and notification.\n"
                    "Idempotency matters when monitoring channels repeatedly."
                ),
                result_kind=YouTubeResultKind.WARNING,
                failure_kind=YouTubeFailureKind.AUTO_CAPTIONS_ONLY,
                reason="manual subtitles unavailable; using auto captions",
            ),
            "https://www.youtube.com/watch?v=playlist-video-001": YouTubeTranscriptPayload(
                language="en",
                source=YouTubeTranscriptSource.MANUAL,
                content=(
                    "Playlist pipelines should stay deterministic.\n"
                    "Stored state makes reruns explainable."
                ),
            ),
        }

    def inspect_source(self, url: str) -> YouTubeSourceDescriptor:
        descriptor = self._descriptors.get(url)
        if descriptor is None:
            raise YouTubeAgentError(
                YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED,
                f"unsupported source: {url}",
            )
        return descriptor

    def discover_videos(self, source_url: str, target_kind: YouTubeTargetKind, *, limit: int = 5) -> list[YouTubeVideoSnapshot]:
        return list(self._discoveries.get(source_url, []))[:limit]

    def fetch_video_metadata(self, source_url: str) -> YouTubeVideoSnapshot:
        return self._metadata[source_url]

    def fetch_transcript(
        self,
        source_url: str,
        *,
        preferred_languages: list[str],
        include_auto_generated: bool,
    ) -> YouTubeTranscriptPayload:
        payload = self._transcripts.get(source_url)
        if payload is None:
            raise YouTubeAgentError(
                YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE,
                "no subtitles or auto captions are available for this video",
            )
        if payload.source == YouTubeTranscriptSource.AUTOMATIC and not include_auto_generated:
            raise YouTubeAgentError(
                YouTubeFailureKind.AUTO_CAPTIONS_ONLY,
                "only auto captions are available for the requested languages",
            )
        if preferred_languages and payload.language not in preferred_languages:
            raise YouTubeAgentError(
                YouTubeFailureKind.SUBTITLE_LANGUAGE_MISMATCH,
                "requested subtitle languages are not available",
            )
        return payload


def _build_service(tmp_path: Path) -> tuple[YouTubeAgentService, InMemoryYouTubeRepository]:
    repository = InMemoryYouTubeRepository()
    service = YouTubeAgentService(
        repository=repository,
        repo_root=tmp_path,
        fetcher=FakeYouTubeFetcher(),
        digest_service=YouTubeDigestService(),
    )
    return service, repository


def test_channel_check_discovers_new_video_and_marks_auto_caption_warning(tmp_path: Path) -> None:
    service, repository = _build_service(tmp_path)
    subscription = service.subscribe(YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/@demo"))

    result = service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest(limit=3))

    assert result.new_video_ids == ["video-001"]
    transcript = service.get_transcript("video-001")
    assert transcript is not None
    assert transcript.result_kind == YouTubeResultKind.WARNING
    assert transcript.failure_kind == YouTubeFailureKind.AUTO_CAPTIONS_ONLY
    digest = service.get_digest("video-001")
    assert digest is not None
    assert digest.result_kind == YouTubeResultKind.WARNING
    assert digest.failure_kind == YouTubeFailureKind.AUTO_CAPTIONS_ONLY
    assert len(repository.list_runs(video_id="video-001", kind=YouTubeRunKind.TRANSCRIPT_FETCH)) == 1


def test_playlist_check_discovers_playlist_video(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    subscription = service.subscribe(
        YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/playlist?list=PL_DEMO")
    )

    result = service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest(limit=3))

    assert result.new_video_ids == ["playlist-video-001"]
    video = service.get_video("playlist-video-001")
    assert video is not None
    assert video.title == "Playlist Entry 001"


def test_transcript_success_and_digest_idempotent(tmp_path: Path) -> None:
    service, repository = _build_service(tmp_path)
    subscription = service.subscribe(YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/watch?v=video-001"))
    result = service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest())
    assert result.new_video_ids == ["video-001"]

    first_digest = service.generate_digest("video-001", YouTubeDigestCreateRequest(overwrite_existing=True))
    second_digest = service.generate_digest("video-001", YouTubeDigestCreateRequest())

    assert first_digest.digest_id == second_digest.digest_id
    digest_runs = repository.list_runs(video_id="video-001", kind=YouTubeRunKind.DIGEST_GENERATE)
    assert any(run.result_kind == YouTubeResultKind.NOOP for run in digest_runs)


def test_digest_regenerates_after_metadata_refresh(tmp_path: Path) -> None:
    service, repository = _build_service(tmp_path)
    subscription = service.subscribe(YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/watch?v=video-001"))
    service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest())

    stale_digest = service.get_digest("video-001")
    assert stale_digest is not None
    assert "Channel: unknown" in stale_digest.content

    service.refresh_video_metadata("video-001")
    refreshed_digest = service.generate_digest("video-001", YouTubeDigestCreateRequest())

    assert "Channel: Demo Channel" in refreshed_digest.content
    digest_runs = repository.list_runs(video_id="video-001", kind=YouTubeRunKind.DIGEST_GENERATE)
    assert digest_runs[0].result_kind != YouTubeResultKind.NOOP


def test_transcript_unavailable_is_persisted_with_failure_kind(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    subscription = service.subscribe(
        YouTubeSubscriptionCreateRequest(
            source_url="https://www.youtube.com/watch?v=video-no-transcript",
            auto_fetch_transcript=False,
            auto_digest=False,
        )
    )
    service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest())

    with pytest.raises(YouTubeAgentError) as excinfo:
        service.fetch_transcript("video-no-transcript", YouTubeTranscriptCreateRequest())

    assert excinfo.value.failure_kind == YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE
    transcript = service.get_transcript("video-no-transcript")
    assert transcript is not None
    assert transcript.status == "failed" or transcript.status.value == "failed"
    assert transcript.failure_kind == YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE
    assert transcript.failed_stage == YouTubeFailedStage.TRANSCRIPT_FETCH


def test_ask_requires_transcript_content(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    subscription = service.subscribe(
        YouTubeSubscriptionCreateRequest(
            source_url="https://www.youtube.com/watch?v=video-no-transcript",
            auto_fetch_transcript=False,
            auto_digest=False,
        )
    )
    service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest())

    with pytest.raises(YouTubeAgentError) as excinfo:
        service.ask_video("video-no-transcript", YouTubeQuestionRequest(question="What is this about?"))

    assert excinfo.value.failure_kind in {
        YouTubeFailureKind.ASK_CONTEXT_MISSING,
        YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE,
    }


def test_failed_stage_persists_for_discovery_digest_and_ask(tmp_path: Path) -> None:
    class DiscoveryFailureFetcher(FakeYouTubeFetcher):
        def discover_videos(self, source_url: str, target_kind: YouTubeTargetKind, *, limit: int = 5) -> list[YouTubeVideoSnapshot]:
            raise YouTubeAgentError(
                YouTubeFailureKind.VIDEO_UNAVAILABLE,
                "this video is unavailable",
                failed_stage=YouTubeFailedStage.DISCOVERY,
            )

    repository = InMemoryYouTubeRepository()
    discovery_service = YouTubeAgentService(
        repository=repository,
        repo_root=tmp_path,
        fetcher=DiscoveryFailureFetcher(),
        digest_service=YouTubeDigestService(),
    )
    subscription = discovery_service.subscribe(
        YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/watch?v=video-001")
    )

    with pytest.raises(YouTubeAgentError):
        discovery_service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest())

    discovery_run = repository.list_runs(
        subscription_id=subscription.subscription_id,
        kind=YouTubeRunKind.SUBSCRIPTION_CHECK,
    )[0]
    assert discovery_run.failure_kind == YouTubeFailureKind.VIDEO_UNAVAILABLE
    assert discovery_run.failed_stage == YouTubeFailedStage.DISCOVERY

    service, repository = _build_service(tmp_path)
    no_context_subscription = service.subscribe(
        YouTubeSubscriptionCreateRequest(
            source_url="https://www.youtube.com/watch?v=video-no-transcript",
            auto_fetch_transcript=False,
            auto_digest=False,
        )
    )
    service.check_subscription(no_context_subscription.subscription_id, YouTubeSubscriptionCheckRequest())

    digest = service.generate_digest("video-no-transcript", YouTubeDigestCreateRequest())
    assert digest.failure_kind == YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE
    assert digest.failed_stage == YouTubeFailedStage.DIGEST_BUILD

    with pytest.raises(YouTubeAgentError) as ask_excinfo:
        service.ask_video("video-no-transcript", YouTubeQuestionRequest(question="what happened?"))

    assert ask_excinfo.value.failed_stage == YouTubeFailedStage.ASK
    ask_run = repository.list_runs(video_id="video-no-transcript", kind=YouTubeRunKind.QUESTION_ANSWER)[0]
    assert ask_run.failed_stage == YouTubeFailedStage.ASK


def test_ask_summary_question_uses_video_title_and_context(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    subscription = service.subscribe(YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/watch?v=video-001"))
    service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest())
    service.refresh_video_metadata("video-001")
    service.generate_digest("video-001", YouTubeDigestCreateRequest())

    answer = service.ask_video("video-001", YouTubeQuestionRequest(question="What is this video mainly about?"))

    assert "Agent Systems 101" in answer.answer
    assert answer.citations
    assert answer.citations[0] in answer.answer


def test_repeated_check_does_not_duplicate_video_or_auto_runs(tmp_path: Path) -> None:
    service, repository = _build_service(tmp_path)
    subscription = service.subscribe(YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/@demo"))

    first = service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest())
    second = service.check_subscription(subscription.subscription_id, YouTubeSubscriptionCheckRequest())

    assert first.new_video_ids == ["video-001"]
    assert second.new_video_ids == []
    assert len(repository.list_videos(subscription.subscription_id)) == 1
    assert len(repository.list_digests()) == 1
    assert len(repository.list_runs(video_id="video-001", kind=YouTubeRunKind.TRANSCRIPT_FETCH)) == 1
    assert len(repository.list_runs(video_id="video-001", kind=YouTubeRunKind.DIGEST_GENERATE)) == 1
    check_runs = repository.list_runs(subscription_id=subscription.subscription_id, kind=YouTubeRunKind.SUBSCRIPTION_CHECK)
    assert len(check_runs) == 2
    assert check_runs[0].result_kind == YouTubeResultKind.NOOP


def test_url_normalization_and_subscription_dedup(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)

    first = service.subscribe(YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/@demo"))
    second = service.subscribe(YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/@demo/"))

    assert first.subscription_id == second.subscription_id


def test_subscription_update_soft_delete_and_restore_on_recreate(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    created = service.subscribe(YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/@demo"))

    updated = service.update_subscription(
        created.subscription_id,
        YouTubeSubscriptionUpdateRequest(
            title="Renamed Demo",
            status=YouTubeSubscriptionStatus.PAUSED,
            poll_interval_minutes=120,
            metadata={"owner": "ops"},
        ),
    )
    deleted = service.delete_subscription(created.subscription_id)

    assert service.list_subscriptions() == []
    assert service.list_subscriptions(include_deleted=True)[0].status == YouTubeSubscriptionStatus.DELETED

    restored = service.subscribe(
        YouTubeSubscriptionCreateRequest(
            source_url="https://www.youtube.com/@demo/",
            title="Restored Demo",
            auto_fetch_transcript=False,
            auto_digest=False,
            poll_interval_minutes=180,
            metadata={"owner": "growth"},
        )
    )

    assert updated.title == "Renamed Demo"
    assert updated.status == YouTubeSubscriptionStatus.PAUSED
    assert updated.poll_interval_minutes == 120
    assert updated.metadata["owner"] == "ops"
    assert deleted.status == YouTubeSubscriptionStatus.DELETED
    assert restored.subscription_id == created.subscription_id
    assert restored.status == YouTubeSubscriptionStatus.ACTIVE
    assert restored.title == "Restored Demo"
    assert restored.auto_fetch_transcript is False
    assert restored.auto_digest is False
    assert restored.poll_interval_minutes == 180
    assert restored.metadata["owner"] == "growth"


def test_import_export_round_trip_and_invalid_rows_are_structured(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)
    created = service.subscribe(YouTubeSubscriptionCreateRequest(source_url="https://www.youtube.com/@demo"))
    service.update_subscription(
        created.subscription_id,
        YouTubeSubscriptionUpdateRequest(status=YouTubeSubscriptionStatus.PAUSED),
    )

    exported = service.export_subscriptions()
    imported = service.import_subscriptions(
        YouTubeSubscriptionImportRequest(
            subscriptions=[
                *exported.subscriptions,
                YouTubeSubscriptionImportItem(
                    source_url="https://www.youtube.com/playlist?list=PL_DEMO",
                    title="Imported Playlist",
                    auto_fetch_transcript=False,
                    auto_digest=False,
                    metadata={"batch": "v1"},
                ),
                YouTubeSubscriptionImportItem(source_url="bad-url"),
            ]
        )
    )

    assert exported.version == "youtube_subscriptions.v1"
    assert len(exported.subscriptions) == 1
    assert imported.imported_count == 3
    assert imported.created_count == 1
    assert imported.skipped_count == 1
    assert imported.failed_count == 1
    assert imported.items[0].action == "skipped"
    assert imported.items[1].action == "created"
    assert imported.items[1].subscription is not None
    assert imported.items[1].subscription.title == "Imported Playlist"
    assert imported.items[2].action == "failed"
    assert imported.items[2].error_kind == YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED
