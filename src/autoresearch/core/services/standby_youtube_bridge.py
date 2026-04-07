from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from autoresearch.api.settings import get_runtime_settings
from autoresearch.core.repositories.youtube import SQLiteYouTubeRepository
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.youtube_errors import YouTubeAgentError
from autoresearch.shared.models import (
    JobStatus,
    StandbyYouTubeAction,
    StandbyYouTubeActionRequest,
    StandbyYouTubeActionResult,
    YouTubeCheckResultRead,
    YouTubeDigestCreateRequest,
    YouTubeDigestRead,
    YouTubeQuestionAnswerRead,
    YouTubeQuestionRequest,
    YouTubeResultKind,
    YouTubeRunKind,
    YouTubeRunRead,
    YouTubeSubscriptionCheckRequest,
    YouTubeSubscriptionCreateRequest,
    YouTubeSubscriptionRead,
    YouTubeTranscriptCreateRequest,
    YouTubeTranscriptRead,
)


_REQUEST_VALIDATION_STAGE = "request_validation"


class StandbyYouTubeBridgeService:
    """Typed, fail-closed bridge from standby worker tasks to the YouTube bounded context."""

    def __init__(self, *, youtube_service: YouTubeAgentService) -> None:
        self._youtube_service = youtube_service

    def execute_payload(
        self,
        payload: dict[str, Any],
        *,
        queue_requested_by: str | None = None,
        queue_metadata: dict[str, Any] | None = None,
    ) -> StandbyYouTubeActionResult:
        try:
            request = StandbyYouTubeActionRequest.model_validate(payload)
        except ValidationError as exc:
            return self._validation_failure(payload=payload, exc=exc)
        return self.execute(
            request,
            queue_requested_by=queue_requested_by,
            queue_metadata=queue_metadata,
        )

    def execute(
        self,
        request: StandbyYouTubeActionRequest,
        *,
        queue_requested_by: str | None = None,
        queue_metadata: dict[str, Any] | None = None,
    ) -> StandbyYouTubeActionResult:
        metadata = self._build_metadata(
            request=request,
            queue_requested_by=queue_requested_by,
            queue_metadata=queue_metadata,
        )

        try:
            if request.action == StandbyYouTubeAction.SUBSCRIBE:
                subscription = self._youtube_service.subscribe(
                    YouTubeSubscriptionCreateRequest(
                        source_url=request.target_url or "",
                        metadata=metadata,
                    )
                )
                return StandbyYouTubeActionResult(
                    success=True,
                    action=request.action.value,
                    status=JobStatus.COMPLETED,
                    result_kind=YouTubeResultKind.SUCCESS,
                    subscription_id=subscription.subscription_id,
                    reason="subscription ready",
                    metadata={
                        "normalized_url": subscription.normalized_url,
                        "target_kind": subscription.target_kind.value,
                    },
                )

            if request.action == StandbyYouTubeAction.CHECK:
                result = self._youtube_service.check_subscription(
                    request.subscription_id or "",
                    YouTubeSubscriptionCheckRequest(
                        limit=request.check_limit,
                        metadata=metadata,
                    ),
                )
                return self._check_result_to_bridge_result(result)

            if request.action == StandbyYouTubeAction.FETCH_TRANSCRIPT:
                transcript = self._youtube_service.fetch_transcript(
                    request.video_id or "",
                    YouTubeTranscriptCreateRequest(
                        preferred_languages=list(request.preferred_languages),
                        include_auto_generated=request.include_auto_generated,
                        overwrite_existing=request.overwrite_existing,
                        metadata=metadata,
                    ),
                )
                return self._transcript_result_to_bridge_result(video_id=request.video_id or "", transcript=transcript)

            if request.action == StandbyYouTubeAction.BUILD_DIGEST:
                digest = self._youtube_service.generate_digest(
                    request.video_id or "",
                    YouTubeDigestCreateRequest(
                        format=request.digest_format,
                        overwrite_existing=request.overwrite_existing,
                        metadata=metadata,
                    ),
                )
                return self._digest_result_to_bridge_result(video_id=request.video_id or "", digest=digest)

            answer = self._youtube_service.ask_video(
                request.video_id or "",
                YouTubeQuestionRequest(
                    question=request.question or "",
                    metadata=metadata,
                ),
            )
            return self._answer_result_to_bridge_result(video_id=request.video_id or "", answer=answer)
        except KeyError:
            return StandbyYouTubeActionResult(
                success=False,
                action=request.action.value,
                status=JobStatus.FAILED,
                result_kind=YouTubeResultKind.FAILED,
                error_kind="invalid_target",
                failed_stage=_REQUEST_VALIDATION_STAGE,
                reason=self._missing_resource_reason(request),
                subscription_id=request.subscription_id,
                video_id=request.video_id,
                metadata=metadata,
            )
        except YouTubeAgentError as exc:
            run = self._latest_run_for_action(request)
            return StandbyYouTubeActionResult(
                success=False,
                action=request.action.value,
                status=JobStatus.FAILED,
                result_kind=YouTubeResultKind.FAILED,
                error_kind=exc.failure_kind.value,
                failed_stage=exc.failed_stage.value if exc.failed_stage else None,
                reason=exc.reason,
                subscription_id=request.subscription_id,
                video_id=request.video_id,
                transcript_id=self._transcript_id_from_run_context(request),
                digest_id=self._digest_id_from_run_context(request),
                run_id=run.run_id if run else None,
                metadata={
                    **metadata,
                    **exc.details,
                },
            )

    def _validation_failure(
        self,
        *,
        payload: dict[str, Any],
        exc: ValidationError,
    ) -> StandbyYouTubeActionResult:
        error_kind = "invalid_request"
        for item in exc.errors():
            if tuple(item.get("loc") or ()) == ("action",):
                error_kind = "invalid_action"
                break
        action = payload.get("action")
        return StandbyYouTubeActionResult(
            success=False,
            action=str(action or "unknown"),
            status=JobStatus.FAILED,
            result_kind=YouTubeResultKind.FAILED,
            error_kind=error_kind,
            failed_stage=_REQUEST_VALIDATION_STAGE,
            reason="; ".join(item["msg"] for item in exc.errors()),
            metadata={"validation_errors": exc.errors()},
        )

    def _build_metadata(
        self,
        *,
        request: StandbyYouTubeActionRequest,
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
        return metadata

    def _check_result_to_bridge_result(self, result: YouTubeCheckResultRead) -> StandbyYouTubeActionResult:
        run = result.run
        return StandbyYouTubeActionResult(
            success=run.status != JobStatus.FAILED,
            action=StandbyYouTubeAction.CHECK.value,
            status=run.status,
            result_kind=run.result_kind,
            error_kind=run.failure_kind.value if run.failure_kind else None,
            failed_stage=run.failed_stage.value if run.failed_stage else None,
            reason=run.reason,
            subscription_id=result.subscription.subscription_id,
            video_id=result.new_video_ids[0] if result.new_video_ids else None,
            run_id=run.run_id,
            discovered_video_ids=list(result.discovered_video_ids),
            new_video_ids=list(result.new_video_ids),
            metadata={"summary": run.summary},
        )

    def _transcript_result_to_bridge_result(
        self,
        *,
        video_id: str,
        transcript: YouTubeTranscriptRead,
    ) -> StandbyYouTubeActionResult:
        run = self._latest_run(video_id=video_id, kind=YouTubeRunKind.TRANSCRIPT_FETCH)
        return StandbyYouTubeActionResult(
            success=transcript.status != JobStatus.FAILED,
            action=StandbyYouTubeAction.FETCH_TRANSCRIPT.value,
            status=transcript.status,
            result_kind=transcript.result_kind,
            error_kind=transcript.failure_kind.value if transcript.failure_kind else None,
            failed_stage=transcript.failed_stage.value if transcript.failed_stage else None,
            reason=transcript.reason,
            video_id=video_id,
            transcript_id=transcript.transcript_id,
            run_id=run.run_id if run else None,
            metadata={
                "language": transcript.language,
                "source": transcript.source.value,
            },
        )

    def _digest_result_to_bridge_result(
        self,
        *,
        video_id: str,
        digest: YouTubeDigestRead,
    ) -> StandbyYouTubeActionResult:
        run = self._latest_run(video_id=video_id, kind=YouTubeRunKind.DIGEST_GENERATE)
        return StandbyYouTubeActionResult(
            success=digest.status != JobStatus.FAILED,
            action=StandbyYouTubeAction.BUILD_DIGEST.value,
            status=digest.status,
            result_kind=digest.result_kind,
            error_kind=digest.failure_kind.value if digest.failure_kind else None,
            failed_stage=digest.failed_stage.value if digest.failed_stage else None,
            reason=digest.reason,
            video_id=video_id,
            digest_id=digest.digest_id,
            run_id=run.run_id if run else None,
            metadata={"format": digest.format},
        )

    def _answer_result_to_bridge_result(
        self,
        *,
        video_id: str,
        answer: YouTubeQuestionAnswerRead,
    ) -> StandbyYouTubeActionResult:
        run = self._latest_run(video_id=video_id, kind=YouTubeRunKind.QUESTION_ANSWER)
        return StandbyYouTubeActionResult(
            success=True,
            action=StandbyYouTubeAction.ASK.value,
            status=JobStatus.COMPLETED,
            result_kind=YouTubeResultKind.SUCCESS,
            video_id=video_id,
            run_id=run.run_id if run else None,
            answer=answer.answer,
            citations=list(answer.citations),
            metadata=answer.metadata,
        )

    def _latest_run_for_action(self, request: StandbyYouTubeActionRequest) -> YouTubeRunRead | None:
        if request.action == StandbyYouTubeAction.CHECK:
            return self._latest_run(subscription_id=request.subscription_id, kind=YouTubeRunKind.SUBSCRIPTION_CHECK)
        if request.action == StandbyYouTubeAction.FETCH_TRANSCRIPT:
            return self._latest_run(video_id=request.video_id, kind=YouTubeRunKind.TRANSCRIPT_FETCH)
        if request.action == StandbyYouTubeAction.BUILD_DIGEST:
            return self._latest_run(video_id=request.video_id, kind=YouTubeRunKind.DIGEST_GENERATE)
        if request.action == StandbyYouTubeAction.ASK:
            return self._latest_run(video_id=request.video_id, kind=YouTubeRunKind.QUESTION_ANSWER)
        return None

    def _latest_run(
        self,
        *,
        subscription_id: str | None = None,
        video_id: str | None = None,
        kind: YouTubeRunKind,
    ) -> YouTubeRunRead | None:
        runs = self._youtube_service.list_runs(subscription_id=subscription_id, video_id=video_id, kind=kind)
        return runs[0] if runs else None

    def _transcript_id_from_run_context(self, request: StandbyYouTubeActionRequest) -> str | None:
        if not request.video_id:
            return None
        transcript = self._youtube_service.get_transcript(request.video_id)
        return transcript.transcript_id if transcript else None

    def _digest_id_from_run_context(self, request: StandbyYouTubeActionRequest) -> str | None:
        if not request.video_id:
            return None
        digest = self._youtube_service.get_digest(request.video_id)
        return digest.digest_id if digest else None

    @staticmethod
    def _missing_resource_reason(request: StandbyYouTubeActionRequest) -> str:
        if request.subscription_id:
            return f"subscription not found: {request.subscription_id}"
        if request.video_id:
            return f"video not found: {request.video_id}"
        return "target resource was not found"


def build_default_standby_youtube_bridge_service() -> StandbyYouTubeBridgeService:
    repo_root = Path(__file__).resolve().parents[4]
    return StandbyYouTubeBridgeService(
        youtube_service=YouTubeAgentService(
            repository=SQLiteYouTubeRepository(db_path=get_runtime_settings().api_db_path),
            repo_root=repo_root,
        )
    )
