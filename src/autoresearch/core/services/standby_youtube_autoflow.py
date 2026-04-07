from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from pydantic import ValidationError

from autoresearch.api.settings import get_runtime_settings
from autoresearch.core.repositories.youtube import SQLiteYouTubeRepository
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.youtube_errors import YouTubeAgentError
from autoresearch.github_assistant.models import GitHubAssistantYouTubePublishRequest
from autoresearch.github_assistant.service import GitHubAssistantService
from autoresearch.shared.models import (
    JobStatus,
    StandbyYouTubeAutoflowRequest,
    StandbyYouTubeAutoflowResult,
    YouTubeDigestCreateRequest,
    YouTubeSubscriptionCheckRequest,
    YouTubeSubscriptionCreateRequest,
    YouTubeTranscriptCreateRequest,
)


_REQUEST_VALIDATION_STAGE = "request_validation"
_DISCOVERY_STAGE = "source_discovery"
_GITHUB_PUBLISH_STAGE = "github_publish"
_URL_RE = re.compile(r"https?://[^\s<>()]+")


def extract_urls_from_text(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    urls: list[str] = []
    seen: set[str] = set()
    for candidate in _URL_RE.findall(text):
        cleaned = candidate.rstrip(".,)")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        urls.append(cleaned)
    return urls


def extract_youtube_urls_from_text(text: str) -> list[str]:
    return [url for url in extract_urls_from_text(text) if "youtu" in url.lower()]


class StandbyYouTubeAutoflowService:
    def __init__(
        self,
        *,
        youtube_service: YouTubeAgentService,
        github_service: GitHubAssistantService,
    ) -> None:
        self._youtube_service = youtube_service
        self._github_service = github_service

    def execute_payload(
        self,
        payload: dict[str, Any],
        *,
        queue_requested_by: str | None = None,
        queue_metadata: dict[str, Any] | None = None,
    ) -> StandbyYouTubeAutoflowResult:
        try:
            request = StandbyYouTubeAutoflowRequest.model_validate(payload)
        except ValidationError as exc:
            return StandbyYouTubeAutoflowResult(
                success=False,
                status=JobStatus.FAILED,
                error_kind="invalid_request",
                failed_stage=_REQUEST_VALIDATION_STAGE,
                reason="; ".join(item["msg"] for item in exc.errors()),
                metadata={"validation_errors": exc.errors()},
            )
        return self.execute(
            request,
            queue_requested_by=queue_requested_by,
            queue_metadata=queue_metadata,
        )

    def execute(
        self,
        request: StandbyYouTubeAutoflowRequest,
        *,
        queue_requested_by: str | None = None,
        queue_metadata: dict[str, Any] | None = None,
    ) -> StandbyYouTubeAutoflowResult:
        metadata = self._build_metadata(
            request=request,
            queue_requested_by=queue_requested_by,
            queue_metadata=queue_metadata,
        )
        try:
            source_url = self._resolve_source_url(request)
        except ValueError as exc:
            return StandbyYouTubeAutoflowResult(
                success=False,
                status=JobStatus.FAILED,
                error_kind="invalid_source",
                failed_stage=_DISCOVERY_STAGE,
                reason=str(exc),
                metadata=metadata,
            )

        try:
            subscription = self._youtube_service.subscribe(
                YouTubeSubscriptionCreateRequest(
                    source_url=source_url,
                    auto_fetch_transcript=False,
                    auto_digest=False,
                    metadata=metadata,
                )
            )
            check = self._youtube_service.check_subscription(
                subscription.subscription_id,
                YouTubeSubscriptionCheckRequest(
                    limit=1,
                    metadata=metadata,
                ),
            )
            video_id = self._resolve_video_id(subscription_id=subscription.subscription_id, fallback_video_id=subscription.external_id, check=check)
            transcript = self._youtube_service.fetch_transcript(
                video_id,
                YouTubeTranscriptCreateRequest(
                    preferred_languages=list(request.preferred_languages),
                    include_auto_generated=request.include_auto_generated,
                    overwrite_existing=request.overwrite_existing,
                    metadata=metadata,
                ),
            )
            digest = self._youtube_service.generate_digest(
                video_id,
                YouTubeDigestCreateRequest(
                    format="markdown",
                    overwrite_existing=request.overwrite_existing,
                    metadata=metadata,
                ),
            )
            video = self._youtube_service.get_video(video_id)
            if video is None:
                raise KeyError(video_id)

            run_dir, publish = self._github_service.publish_youtube(
                GitHubAssistantYouTubePublishRequest(
                    video_id=video.video_id,
                    source_url=video.source_url,
                    title=video.title,
                    channel_id=video.channel_id,
                    channel_title=video.channel_title,
                    description=video.description,
                    published_at=video.published_at,
                    digest_id=digest.digest_id,
                    digest_content=digest.content,
                    transcript_id=transcript.transcript_id,
                    transcript_language=transcript.language,
                    repo_hint=request.repo_hint,
                    requested_by=request.requested_by or queue_requested_by,
                    metadata=metadata,
                )
            )
            summary = self._github_service.read_summary(run_dir)
            success_statuses = {"draft_pr_opened", "promotion_complete", "no_changes"}
            return StandbyYouTubeAutoflowResult(
                success=summary.status in success_statuses,
                status=JobStatus.COMPLETED if summary.status in success_statuses else JobStatus.FAILED,
                source_url=source_url,
                normalized_url=subscription.normalized_url,
                subscription_id=subscription.subscription_id,
                video_id=video.video_id,
                transcript_id=transcript.transcript_id,
                digest_id=digest.digest_id,
                repo=publish.repo,
                output_path=publish.output_path,
                route_reason=publish.route_reason,
                github_run_dir=str(run_dir),
                github_run_status=summary.status,
                pr_url=publish.pr_url,
                artifacts=self._github_service.list_artifacts(run_dir),
                reason=summary.warnings[-1] if summary.warnings else publish.route_reason,
                metadata={
                    **metadata,
                    "branch_name": publish.branch_name,
                    "github_summary": summary.model_dump(mode="json"),
                },
            )
        except KeyError as exc:
            missing = str(exc).strip("'")
            return StandbyYouTubeAutoflowResult(
                success=False,
                status=JobStatus.FAILED,
                source_url=source_url,
                error_kind="invalid_target",
                failed_stage=_DISCOVERY_STAGE,
                reason=f"video not found: {missing}",
                metadata=metadata,
            )
        except YouTubeAgentError as exc:
            return StandbyYouTubeAutoflowResult(
                success=False,
                status=JobStatus.FAILED,
                source_url=source_url,
                subscription_id=locals().get("subscription").subscription_id if "subscription" in locals() else None,
                video_id=locals().get("video_id"),
                transcript_id=locals().get("transcript").transcript_id if "transcript" in locals() else None,
                digest_id=locals().get("digest").digest_id if "digest" in locals() else None,
                error_kind=exc.failure_kind.value,
                failed_stage=exc.failed_stage.value if exc.failed_stage else None,
                reason=exc.reason,
                metadata={
                    **metadata,
                    **exc.details,
                },
            )
        except Exception as exc:
            return StandbyYouTubeAutoflowResult(
                success=False,
                status=JobStatus.FAILED,
                source_url=source_url,
                subscription_id=locals().get("subscription").subscription_id if "subscription" in locals() else None,
                video_id=locals().get("video_id"),
                transcript_id=locals().get("transcript").transcript_id if "transcript" in locals() else None,
                digest_id=locals().get("digest").digest_id if "digest" in locals() else None,
                error_kind="github_publish_failed",
                failed_stage=_GITHUB_PUBLISH_STAGE,
                reason=str(exc).strip() or exc.__class__.__name__,
                metadata=metadata,
            )

    def _resolve_source_url(self, request: StandbyYouTubeAutoflowRequest) -> str:
        if request.source_url and request.source_url.strip():
            return request.source_url.strip()
        if request.input_text:
            youtube_urls = extract_youtube_urls_from_text(request.input_text)
            if youtube_urls:
                return youtube_urls[0]
        raise ValueError("no YouTube URL found in request")

    def _resolve_video_id(
        self,
        *,
        subscription_id: str,
        fallback_video_id: str | None,
        check,
    ) -> str:
        if check.new_video_ids:
            return check.new_video_ids[0]
        if check.discovered_video_ids:
            return check.discovered_video_ids[0]
        subscription = self._youtube_service.get_subscription(subscription_id)
        if subscription and subscription.latest_video_id:
            return subscription.latest_video_id
        if fallback_video_id:
            return fallback_video_id
        raise KeyError(subscription_id)

    def _build_metadata(
        self,
        *,
        request: StandbyYouTubeAutoflowRequest,
        queue_requested_by: str | None,
        queue_metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        metadata = dict(queue_metadata or {})
        metadata.update(request.metadata)
        metadata.setdefault("source", request.source)
        if request.requested_by:
            metadata["requested_by"] = request.requested_by
        elif queue_requested_by:
            metadata["requested_by"] = queue_requested_by
        if request.input_text and request.input_text.strip():
            metadata.setdefault("input_text", request.input_text.strip())
        return metadata


def build_default_standby_youtube_autoflow_service() -> StandbyYouTubeAutoflowService:
    repo_root = Path(__file__).resolve().parents[4]
    return StandbyYouTubeAutoflowService(
        youtube_service=YouTubeAgentService(
            repository=SQLiteYouTubeRepository(db_path=get_runtime_settings().api_db_path),
            repo_root=repo_root,
        ),
        github_service=GitHubAssistantService(repo_root=repo_root),
    )
