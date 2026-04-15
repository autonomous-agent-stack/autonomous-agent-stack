from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from autoresearch.core.repositories.youtube import InMemoryYouTubeRepository
from autoresearch.core.services.standby_youtube_autoflow import StandbyYouTubeAutoflowService
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.youtube_digest import YouTubeDigestService
from autoresearch.core.services.youtube_fetcher import (
    YouTubeSourceDescriptor,
    YouTubeTranscriptPayload,
    YouTubeVideoSnapshot,
)
from autoresearch.github_assistant.models import (
    GitHubAssistantYouTubePublishRequest,
    GitHubAssistantYouTubePublishResult,
    RunSummary,
)
from autoresearch.shared.models import JobStatus, YouTubeTargetKind


class _AutoflowFetcher:
    def inspect_source(self, url: str) -> YouTubeSourceDescriptor:
        return YouTubeSourceDescriptor(
            normalized_url="https://www.youtube.com/watch?v=video-001",
            target_kind=YouTubeTargetKind.VIDEO,
            external_id="video-001",
            title="Autoflow Demo Video",
        )

    def discover_videos(self, source_url: str, target_kind: YouTubeTargetKind, *, limit: int = 5) -> list[YouTubeVideoSnapshot]:
        return [
            YouTubeVideoSnapshot(
                video_id="video-001",
                source_url="https://www.youtube.com/watch?v=video-001",
                title="Autoflow Demo Video",
                channel_id="channel-001",
                channel_title="Demo Channel",
                description="Autoflow demo description.",
                published_at=datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc),
            )
        ]

    def fetch_video_metadata(self, source_url: str) -> YouTubeVideoSnapshot:
        return self.discover_videos(source_url, YouTubeTargetKind.VIDEO)[0]

    def fetch_transcript(
        self,
        source_url: str,
        *,
        preferred_languages: list[str],
        include_auto_generated: bool,
    ) -> YouTubeTranscriptPayload:
        return YouTubeTranscriptPayload(
            language="en",
            source="manual",
            content="This transcript explains how the autoflow links YouTube and GitHub.",
        )


class _FakeGitHubPublishService:
    def __init__(self, tmp_path: Path) -> None:
        self.run_dir = tmp_path / "github-runs" / "run-youtube-001"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.payloads: list[GitHubAssistantYouTubePublishRequest] = []

    def publish_youtube(
        self,
        payload: GitHubAssistantYouTubePublishRequest,
    ) -> tuple[Path, GitHubAssistantYouTubePublishResult]:
        self.payloads.append(payload)
        return self.run_dir, GitHubAssistantYouTubePublishResult(
            repo="acme/demo",
            output_path="docs/youtube-ingest/2026-04-06-video-001-autoflow-demo-video.md",
            route_reason="default_enabled_route",
            pr_url="https://github.com/acme/demo/pull/7",
            branch_name="assistant/youtube/video-001-autoflow-demo-video",
        )

    def read_summary(self, run_dir: Path) -> RunSummary:
        assert run_dir == self.run_dir
        return RunSummary(
            run_id="gha-run-001",
            repo="acme/demo",
            status="draft_pr_opened",
            started_at=datetime(2026, 4, 7, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 7, 0, 1, tzinfo=timezone.utc),
        )

    def list_artifacts(self, run_dir: Path) -> list[str]:
        assert run_dir == self.run_dir
        return ["patch.diff", "promotion_result.json"]


def _build_service(tmp_path: Path) -> tuple[StandbyYouTubeAutoflowService, _FakeGitHubPublishService]:
    github = _FakeGitHubPublishService(tmp_path)
    youtube = YouTubeAgentService(
        repository=InMemoryYouTubeRepository(),
        repo_root=tmp_path,
        fetcher=_AutoflowFetcher(),
        digest_service=YouTubeDigestService(),
    )
    return StandbyYouTubeAutoflowService(youtube_service=youtube, github_service=github), github


def test_autoflow_executes_end_to_end_from_input_text(tmp_path: Path) -> None:
    service, github = _build_service(tmp_path)

    result = service.execute_payload(
        {
            "input_text": "请处理这个视频 https://www.youtube.com/watch?v=video-001 并推到 GitHub",
            "repo_hint": "acme/demo",
            "requested_by": "operator",
        },
        queue_requested_by="queue-operator",
        queue_metadata={"source": "autoflow_test"},
    )

    assert result.success is True
    assert result.status == JobStatus.COMPLETED
    assert result.video_id == "video-001"
    assert result.digest_id is not None
    assert result.repo == "acme/demo"
    assert result.pr_url == "https://github.com/acme/demo/pull/7"
    assert result.github_run_status == "draft_pr_opened"
    assert "patch.diff" in result.artifacts
    assert github.payloads[0].repo_hint == "acme/demo"
    assert github.payloads[0].source_url == "https://www.youtube.com/watch?v=video-001"


def test_autoflow_rejects_missing_youtube_url(tmp_path: Path) -> None:
    service, _ = _build_service(tmp_path)

    result = service.execute_payload({"input_text": "这里没有链接"})

    assert result.success is False
    assert result.status == JobStatus.FAILED
    assert result.error_kind == "invalid_source"
    assert result.failed_stage == "source_discovery"
