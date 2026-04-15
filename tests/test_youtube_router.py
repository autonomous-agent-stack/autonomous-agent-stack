from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_youtube_agent_service
from autoresearch.api.main import app
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
    YouTubeFailedStage,
    YouTubeFailureKind,
    YouTubeResultKind,
    YouTubeSubscriptionStatus,
    YouTubeTargetKind,
    YouTubeTranscriptSource,
)


class RouterFakeYouTubeFetcher:
    def inspect_source(self, url: str) -> YouTubeSourceDescriptor:
        if url == "bad-url":
            raise YouTubeAgentError(
                YouTubeFailureKind.UNSUPPORTED_SOURCE_OR_PARSE_FAILED,
                "unsupported source: bad-url",
                failed_stage=YouTubeFailedStage.DISCOVERY,
            )
        return YouTubeSourceDescriptor(
            normalized_url=url.rstrip("/"),
            target_kind=YouTubeTargetKind.CHANNEL,
            external_id="router-channel",
            title="Router Demo",
        )

    def discover_videos(self, source_url: str, target_kind: YouTubeTargetKind, *, limit: int = 5) -> list[YouTubeVideoSnapshot]:
        return [
            YouTubeVideoSnapshot(
                video_id="router-video-001",
                source_url="https://www.youtube.com/watch?v=router-video-001",
                title="Router Test Video",
                channel_id="router-channel",
                channel_title="Router Demo",
                description="The router test video explains how the YouTube API skeleton works.",
            )
        ]

    def fetch_video_metadata(self, source_url: str) -> YouTubeVideoSnapshot:
        return YouTubeVideoSnapshot(
            video_id="router-video-001",
            source_url="https://www.youtube.com/watch?v=router-video-001",
            title="Router Test Video",
            channel_id="router-channel",
            channel_title="Router Demo",
            description="The router test video explains how the YouTube API skeleton works.",
        )

    def fetch_transcript(
        self,
        source_url: str,
        *,
        preferred_languages: list[str],
        include_auto_generated: bool,
    ) -> YouTubeTranscriptPayload:
        if source_url.endswith("router-video-001") and preferred_languages == ["fr"]:
            raise YouTubeAgentError(
                YouTubeFailureKind.SUBTITLE_LANGUAGE_MISMATCH,
                "requested subtitle languages are not available",
                failed_stage=YouTubeFailedStage.TRANSCRIPT_FETCH,
            )
        return YouTubeTranscriptPayload(
            language=preferred_languages[0],
            source=YouTubeTranscriptSource.AUTOMATIC,
            content=(
                "The API skeleton keeps subscription state in SQLite.\n"
                "The check endpoint discovers videos and persists metadata.\n"
                "Digest and ask endpoints can build on top of the stored transcript."
            ),
            result_kind=YouTubeResultKind.WARNING,
            failure_kind=YouTubeFailureKind.AUTO_CAPTIONS_ONLY,
            reason="manual subtitles unavailable; using auto captions",
        )


@pytest.fixture
def youtube_client(tmp_path: Path) -> TestClient:
    service = YouTubeAgentService(
        repository=InMemoryYouTubeRepository(),
        repo_root=tmp_path,
        fetcher=RouterFakeYouTubeFetcher(),
        digest_service=YouTubeDigestService(),
    )
    app.dependency_overrides[get_youtube_agent_service] = lambda: service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_youtube_router_end_to_end(youtube_client: TestClient) -> None:
    created = youtube_client.post(
        "/api/v1/youtube/subscriptions",
        json={"source_url": "https://www.youtube.com/@router-demo"},
    )
    assert created.status_code == 201
    subscription_id = created.json()["subscription_id"]

    checked = youtube_client.post(
        f"/api/v1/youtube/subscriptions/{subscription_id}/check",
        json={"limit": 3},
    )
    assert checked.status_code == 200
    assert checked.json()["new_video_ids"] == ["router-video-001"]

    metadata = youtube_client.post("/api/v1/youtube/videos/router-video-001/metadata")
    assert metadata.status_code == 200
    assert metadata.json()["title"] == "Router Test Video"

    transcript = youtube_client.post(
        "/api/v1/youtube/videos/router-video-001/transcript",
        json={"preferred_languages": ["en"]},
    )
    assert transcript.status_code == 200
    assert transcript.json()["result_kind"] == "warning"
    assert transcript.json()["failure_kind"] == "auto_captions_only"

    digest = youtube_client.post(
        "/api/v1/youtube/videos/router-video-001/digest",
        json={"format": "markdown"},
    )
    assert digest.status_code == 200
    assert "## Summary" in digest.json()["content"]

    answer = youtube_client.post(
        "/api/v1/youtube/videos/router-video-001/ask",
        json={"question": "What does the skeleton persist?"},
    )
    assert answer.status_code == 200
    assert "SQLite" in answer.json()["answer"]


def test_youtube_router_returns_structured_error_detail(youtube_client: TestClient) -> None:
    response = youtube_client.post(
        "/api/v1/youtube/subscriptions",
        json={"source_url": "bad-url"},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_kind"] == "unsupported_source_or_parse_failed"

    created = youtube_client.post(
        "/api/v1/youtube/subscriptions",
        json={
            "source_url": "https://www.youtube.com/@router-demo",
            "auto_fetch_transcript": False,
            "auto_digest": False,
        },
    )
    subscription_id = created.json()["subscription_id"]
    youtube_client.post(
        f"/api/v1/youtube/subscriptions/{subscription_id}/check",
        json={"limit": 3},
    )
    mismatch = youtube_client.post(
        "/api/v1/youtube/videos/router-video-001/transcript",
        json={"preferred_languages": ["fr"]},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["error_kind"] == "subtitle_language_mismatch"
    assert mismatch.json()["detail"]["failed_stage"] == "transcript_fetch"


def test_youtube_router_subscription_management_routes(youtube_client: TestClient) -> None:
    created = youtube_client.post(
        "/api/v1/youtube/subscriptions",
        json={"source_url": "https://www.youtube.com/@router-demo"},
    )
    assert created.status_code == 201
    subscription_id = created.json()["subscription_id"]

    updated = youtube_client.patch(
        f"/api/v1/youtube/subscriptions/{subscription_id}",
        json={
            "title": "Managed Router Demo",
            "status": "paused",
            "poll_interval_minutes": 180,
            "metadata": {"owner": "ops"},
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Managed Router Demo"
    assert updated.json()["status"] == YouTubeSubscriptionStatus.PAUSED

    exported = youtube_client.get("/api/v1/youtube/subscriptions/export")
    assert exported.status_code == 200
    assert exported.json()["version"] == "youtube_subscriptions.v1"
    assert len(exported.json()["subscriptions"]) == 1

    deleted = youtube_client.delete(f"/api/v1/youtube/subscriptions/{subscription_id}")
    assert deleted.status_code == 200
    assert deleted.json()["status"] == YouTubeSubscriptionStatus.DELETED

    hidden = youtube_client.get(f"/api/v1/youtube/subscriptions/{subscription_id}")
    assert hidden.status_code == 404

    visible = youtube_client.get(f"/api/v1/youtube/subscriptions/{subscription_id}?include_deleted=true")
    assert visible.status_code == 200
    assert visible.json()["status"] == YouTubeSubscriptionStatus.DELETED

    listed = youtube_client.get("/api/v1/youtube/subscriptions")
    assert listed.status_code == 200
    assert listed.json() == []

    imported = youtube_client.post(
        "/api/v1/youtube/subscriptions/import",
        json={
            "subscriptions": [
                {
                    "source_url": "https://www.youtube.com/@router-demo/",
                    "title": "Restored via Import",
                    "status": "active",
                    "auto_fetch_transcript": False,
                    "auto_digest": False,
                    "poll_interval_minutes": 240,
                },
                {
                    "source_url": "bad-url",
                },
            ]
        },
    )
    assert imported.status_code == 200
    body = imported.json()
    assert body["restored_count"] == 1
    assert body["failed_count"] == 1
    assert body["items"][0]["action"] == "restored"
    assert body["items"][0]["subscription"]["subscription_id"] == subscription_id
    assert body["items"][1]["action"] == "failed"
    assert body["items"][1]["error_kind"] == "unsupported_source_or_parse_failed"
