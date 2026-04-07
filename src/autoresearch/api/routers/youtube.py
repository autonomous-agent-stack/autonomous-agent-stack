from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from autoresearch.api.dependencies import get_youtube_agent_service
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.youtube_errors import YouTubeAgentError
from autoresearch.shared.models import (
    YouTubeCheckResultRead,
    YouTubeDigestCreateRequest,
    YouTubeDigestRead,
    YouTubeQuestionAnswerRead,
    YouTubeQuestionRequest,
    YouTubeSubscriptionCheckRequest,
    YouTubeSubscriptionCreateRequest,
    YouTubeSubscriptionExportRead,
    YouTubeSubscriptionImportRequest,
    YouTubeSubscriptionImportResultRead,
    YouTubeSubscriptionRead,
    YouTubeSubscriptionStatus,
    YouTubeSubscriptionUpdateRequest,
    YouTubeTranscriptCreateRequest,
    YouTubeTranscriptRead,
    YouTubeVideoRead,
)


router = APIRouter(prefix="/api/v1/youtube", tags=["youtube"])


def _youtube_http_exception(exc: YouTubeAgentError) -> HTTPException:
    status_code = status.HTTP_409_CONFLICT
    if exc.failure_kind.value == "unsupported_source_or_parse_failed":
        status_code = status.HTTP_400_BAD_REQUEST
    elif exc.failure_kind.value == "rate_limited":
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    elif exc.failure_kind.value == "network_failure":
        status_code = status.HTTP_502_BAD_GATEWAY
    elif exc.failure_kind.value == "timeout_failure":
        status_code = status.HTTP_504_GATEWAY_TIMEOUT
    elif exc.failure_kind.value == "yt_dlp_extractor_failure":
        status_code = status.HTTP_502_BAD_GATEWAY
    return HTTPException(status_code=status_code, detail=exc.to_api_detail())


@router.post(
    "/subscriptions",
    response_model=YouTubeSubscriptionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_subscription(
    payload: YouTubeSubscriptionCreateRequest,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeSubscriptionRead:
    try:
        return service.subscribe(payload)
    except YouTubeAgentError as exc:
        raise _youtube_http_exception(exc) from exc


@router.get("/subscriptions", response_model=list[YouTubeSubscriptionRead])
def list_subscriptions(
    status_filter: YouTubeSubscriptionStatus | None = Query(default=None, alias="status"),
    include_deleted: bool = False,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> list[YouTubeSubscriptionRead]:
    return service.list_subscriptions(status=status_filter, include_deleted=include_deleted)


@router.get("/subscriptions/export", response_model=YouTubeSubscriptionExportRead)
def export_subscriptions(
    include_deleted: bool = False,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeSubscriptionExportRead:
    return service.export_subscriptions(include_deleted=include_deleted)


@router.post("/subscriptions/import", response_model=YouTubeSubscriptionImportResultRead)
def import_subscriptions(
    payload: YouTubeSubscriptionImportRequest,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeSubscriptionImportResultRead:
    return service.import_subscriptions(payload)


@router.get("/subscriptions/{subscription_id}", response_model=YouTubeSubscriptionRead)
def get_subscription(
    subscription_id: str,
    include_deleted: bool = False,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeSubscriptionRead:
    subscription = service.get_subscription(subscription_id, include_deleted=include_deleted)
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube subscription not found")
    return subscription


@router.patch("/subscriptions/{subscription_id}", response_model=YouTubeSubscriptionRead)
def update_subscription(
    subscription_id: str,
    payload: YouTubeSubscriptionUpdateRequest,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeSubscriptionRead:
    try:
        return service.update_subscription(subscription_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube subscription not found") from exc


@router.delete("/subscriptions/{subscription_id}", response_model=YouTubeSubscriptionRead)
def delete_subscription(
    subscription_id: str,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeSubscriptionRead:
    try:
        return service.delete_subscription(subscription_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube subscription not found") from exc


@router.post("/subscriptions/{subscription_id}/check", response_model=YouTubeCheckResultRead)
def check_subscription(
    subscription_id: str,
    payload: YouTubeSubscriptionCheckRequest,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeCheckResultRead:
    try:
        return service.check_subscription(subscription_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube subscription not found") from exc
    except YouTubeAgentError as exc:
        raise _youtube_http_exception(exc) from exc


@router.get("/videos/{video_id}", response_model=YouTubeVideoRead)
def get_video(
    video_id: str,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeVideoRead:
    video = service.get_video(video_id)
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube video not found")
    return video


@router.post("/videos/{video_id}/metadata", response_model=YouTubeVideoRead)
def refresh_video_metadata(
    video_id: str,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeVideoRead:
    try:
        return service.refresh_video_metadata(video_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube video not found") from exc
    except YouTubeAgentError as exc:
        raise _youtube_http_exception(exc) from exc


@router.post("/videos/{video_id}/transcript", response_model=YouTubeTranscriptRead)
def create_transcript(
    video_id: str,
    payload: YouTubeTranscriptCreateRequest,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeTranscriptRead:
    try:
        return service.fetch_transcript(video_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube video not found") from exc
    except YouTubeAgentError as exc:
        raise _youtube_http_exception(exc) from exc


@router.post("/videos/{video_id}/digest", response_model=YouTubeDigestRead)
def create_digest(
    video_id: str,
    payload: YouTubeDigestCreateRequest,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeDigestRead:
    try:
        return service.generate_digest(video_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube video not found") from exc


@router.post("/videos/{video_id}/ask", response_model=YouTubeQuestionAnswerRead)
def ask_video(
    video_id: str,
    payload: YouTubeQuestionRequest,
    service: YouTubeAgentService = Depends(get_youtube_agent_service),
) -> YouTubeQuestionAnswerRead:
    try:
        return service.ask_video(video_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="YouTube video not found") from exc
    except YouTubeAgentError as exc:
        raise _youtube_http_exception(exc) from exc
