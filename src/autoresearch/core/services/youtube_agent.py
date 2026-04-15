from __future__ import annotations

from pathlib import Path

from autoresearch.core.repositories.youtube import YouTubeRepository
from autoresearch.core.services.youtube_digest import YouTubeDigestService
from autoresearch.core.services.youtube_errors import YouTubeAgentError
from autoresearch.core.services.youtube_fetcher import (
    YouTubeFetcher,
    YouTubeTranscriptPayload,
    YouTubeVideoSnapshot,
)
from autoresearch.shared.models import (
    JobStatus,
    YouTubeCheckResultRead,
    YouTubeDigestCreateRequest,
    YouTubeDigestRead,
    YouTubeFailedStage,
    YouTubeFailureKind,
    YouTubeQuestionAnswerRead,
    YouTubeQuestionRequest,
    YouTubeResultKind,
    YouTubeRunKind,
    YouTubeRunRead,
    YouTubeSubscriptionCheckRequest,
    YouTubeSubscriptionCreateRequest,
    YouTubeSubscriptionExportRead,
    YouTubeSubscriptionImportItem,
    YouTubeSubscriptionImportItemResultRead,
    YouTubeSubscriptionImportRequest,
    YouTubeSubscriptionImportResultRead,
    YouTubeSubscriptionRead,
    YouTubeSubscriptionStatus,
    YouTubeSubscriptionUpdateRequest,
    YouTubeTranscriptCreateRequest,
    YouTubeTranscriptRead,
    YouTubeTranscriptSource,
    YouTubeVideoRead,
    utc_now,
)
from autoresearch.shared.store import create_resource_id


class YouTubeAgentService:
    """YouTube bounded context: subscription, discovery, transcript, digest, Q&A."""

    def __init__(
        self,
        *,
        repository: YouTubeRepository,
        repo_root: Path,
        fetcher: YouTubeFetcher | None = None,
        digest_service: YouTubeDigestService | None = None,
    ) -> None:
        self._repository = repository
        self._repo_root = repo_root.resolve()
        self._fetcher = fetcher or YouTubeFetcher()
        self._digest_service = digest_service or YouTubeDigestService()

    def subscribe(self, request: YouTubeSubscriptionCreateRequest) -> YouTubeSubscriptionRead:
        descriptor = self._fetcher.inspect_source(request.source_url)
        existing = self._repository.get_subscription_by_normalized_url(descriptor.normalized_url)
        if existing is not None:
            if existing.status == YouTubeSubscriptionStatus.DELETED:
                restored = existing.model_copy(
                    update=self._subscription_defaults_from_descriptor(
                        descriptor=descriptor,
                        title=request.title,
                        auto_fetch_transcript=request.auto_fetch_transcript,
                        auto_digest=request.auto_digest,
                        poll_interval_minutes=request.poll_interval_minutes,
                        metadata=request.metadata,
                        status=YouTubeSubscriptionStatus.ACTIVE,
                        updated_at=utc_now(),
                    )
                )
                return self._repository.save_subscription(restored)
            return existing

        now = utc_now()
        subscription = YouTubeSubscriptionRead(
            subscription_id=create_resource_id("ytsub"),
            created_at=now,
            **self._subscription_defaults_from_descriptor(
                descriptor=descriptor,
                title=request.title,
                auto_fetch_transcript=request.auto_fetch_transcript,
                auto_digest=request.auto_digest,
                poll_interval_minutes=request.poll_interval_minutes,
                metadata=request.metadata,
                status=YouTubeSubscriptionStatus.ACTIVE,
                updated_at=now,
            ),
        )
        return self._repository.save_subscription(subscription)

    def list_subscriptions(
        self,
        *,
        status: YouTubeSubscriptionStatus | None = None,
        include_deleted: bool = False,
    ) -> list[YouTubeSubscriptionRead]:
        return self._repository.list_subscriptions(status=status, include_deleted=include_deleted)

    def get_subscription(
        self,
        subscription_id: str,
        *,
        include_deleted: bool = False,
    ) -> YouTubeSubscriptionRead | None:
        subscription = self._repository.get_subscription(subscription_id)
        if subscription is None:
            return None
        if not include_deleted and subscription.status == YouTubeSubscriptionStatus.DELETED:
            return None
        return subscription

    def update_subscription(
        self,
        subscription_id: str,
        request: YouTubeSubscriptionUpdateRequest,
    ) -> YouTubeSubscriptionRead:
        subscription = self.get_subscription(subscription_id, include_deleted=True)
        if subscription is None:
            raise KeyError(subscription_id)

        updated_fields: dict[str, object] = {"updated_at": utc_now()}
        if "title" in request.model_fields_set:
            updated_fields["title"] = request.title
        if "status" in request.model_fields_set and request.status is not None:
            updated_fields["status"] = request.status
        if "auto_fetch_transcript" in request.model_fields_set and request.auto_fetch_transcript is not None:
            updated_fields["auto_fetch_transcript"] = request.auto_fetch_transcript
        if "auto_digest" in request.model_fields_set and request.auto_digest is not None:
            updated_fields["auto_digest"] = request.auto_digest
        if "poll_interval_minutes" in request.model_fields_set and request.poll_interval_minutes is not None:
            updated_fields["poll_interval_minutes"] = request.poll_interval_minutes
        if "metadata" in request.model_fields_set:
            updated_fields["metadata"] = {
                **subscription.metadata,
                **request.metadata,
            }
        updated = subscription.model_copy(update=updated_fields)
        return self._repository.save_subscription(updated)

    def delete_subscription(self, subscription_id: str) -> YouTubeSubscriptionRead:
        subscription = self.get_subscription(subscription_id, include_deleted=True)
        if subscription is None:
            raise KeyError(subscription_id)
        if subscription.status == YouTubeSubscriptionStatus.DELETED:
            return subscription
        deleted = subscription.model_copy(
            update={
                "status": YouTubeSubscriptionStatus.DELETED,
                "updated_at": utc_now(),
            }
        )
        return self._repository.save_subscription(deleted)

    def export_subscriptions(self, *, include_deleted: bool = False) -> YouTubeSubscriptionExportRead:
        subscriptions = self.list_subscriptions(include_deleted=include_deleted)
        return YouTubeSubscriptionExportRead(
            exported_at=utc_now(),
            subscriptions=[
                YouTubeSubscriptionImportItem(
                    source_url=subscription.source_url,
                    title=subscription.title,
                    status=subscription.status,
                    auto_fetch_transcript=subscription.auto_fetch_transcript,
                    auto_digest=subscription.auto_digest,
                    poll_interval_minutes=subscription.poll_interval_minutes,
                    metadata=subscription.metadata,
                )
                for subscription in subscriptions
            ],
        )

    def import_subscriptions(
        self,
        request: YouTubeSubscriptionImportRequest,
    ) -> YouTubeSubscriptionImportResultRead:
        items: list[YouTubeSubscriptionImportItemResultRead] = []
        counts = {
            "created_count": 0,
            "updated_count": 0,
            "restored_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
        }

        for item in request.subscriptions:
            try:
                descriptor = self._fetcher.inspect_source(item.source_url)
            except YouTubeAgentError as exc:
                counts["failed_count"] += 1
                items.append(
                    YouTubeSubscriptionImportItemResultRead(
                        source_url=item.source_url,
                        action="failed",
                        error_kind=exc.failure_kind,
                        reason=exc.reason,
                    )
                )
                continue

            existing = self._repository.get_subscription_by_normalized_url(descriptor.normalized_url)
            if existing is None:
                now = utc_now()
                saved = self._repository.save_subscription(
                    YouTubeSubscriptionRead(
                        subscription_id=create_resource_id("ytsub"),
                        created_at=now,
                        **self._subscription_defaults_from_descriptor(
                            descriptor=descriptor,
                            title=item.title,
                            auto_fetch_transcript=item.auto_fetch_transcript,
                            auto_digest=item.auto_digest,
                            poll_interval_minutes=item.poll_interval_minutes,
                            metadata=item.metadata,
                            status=item.status,
                            updated_at=now,
                        ),
                    )
                )
                counts["created_count"] += 1
                items.append(
                    YouTubeSubscriptionImportItemResultRead(
                        source_url=item.source_url,
                        normalized_url=descriptor.normalized_url,
                        action="created",
                        subscription=saved,
                    )
                )
                continue

            action = self._determine_import_action(
                existing=existing,
                descriptor=descriptor,
                item=item,
            )
            if action == "skipped":
                counts["skipped_count"] += 1
                items.append(
                    YouTubeSubscriptionImportItemResultRead(
                        source_url=item.source_url,
                        normalized_url=descriptor.normalized_url,
                        action="skipped",
                        subscription=existing,
                    )
                )
                continue

            saved = self._repository.save_subscription(
                existing.model_copy(
                    update=self._subscription_defaults_from_descriptor(
                        descriptor=descriptor,
                        title=item.title,
                        auto_fetch_transcript=item.auto_fetch_transcript,
                        auto_digest=item.auto_digest,
                        poll_interval_minutes=item.poll_interval_minutes,
                        metadata=item.metadata,
                        status=item.status,
                        updated_at=utc_now(),
                    )
                )
            )
            counts[f"{action}_count"] += 1
            items.append(
                YouTubeSubscriptionImportItemResultRead(
                    source_url=item.source_url,
                    normalized_url=descriptor.normalized_url,
                    action=action,
                    subscription=saved,
                )
            )

        return YouTubeSubscriptionImportResultRead(
            imported_count=len(request.subscriptions),
            items=items,
            **counts,
        )

    def get_video(self, video_id: str) -> YouTubeVideoRead | None:
        return self._repository.get_video(video_id)

    def get_transcript(self, video_id: str) -> YouTubeTranscriptRead | None:
        return self._repository.get_transcript_by_video_id(video_id)

    def get_digest(self, video_id: str) -> YouTubeDigestRead | None:
        return self._repository.get_digest_by_video_id(video_id)

    def list_runs(
        self,
        *,
        subscription_id: str | None = None,
        video_id: str | None = None,
        kind: YouTubeRunKind | None = None,
    ) -> list[YouTubeRunRead]:
        return self._repository.list_runs(subscription_id=subscription_id, video_id=video_id, kind=kind)

    def check_subscription(
        self,
        subscription_id: str,
        request: YouTubeSubscriptionCheckRequest,
    ) -> YouTubeCheckResultRead:
        subscription = self.get_subscription(subscription_id)
        if subscription is None:
            raise KeyError(subscription_id)

        run = self._create_run(
            kind=YouTubeRunKind.SUBSCRIPTION_CHECK,
            subscription_id=subscription_id,
        )
        updated_subscription = subscription

        try:
            snapshots = self._fetcher.discover_videos(
                subscription.normalized_url,
                subscription.target_kind,
                limit=request.limit,
            )
            discovered_video_ids: list[str] = []
            new_video_ids: list[str] = []
            auto_pipeline_results: list[dict[str, object]] = []

            for snapshot in snapshots:
                discovered_video_ids.append(snapshot.video_id)
                existing_video = self._repository.get_video(snapshot.video_id)
                saved_video = self._upsert_video_from_snapshot(
                    snapshot=snapshot,
                    subscription=subscription,
                    existing=existing_video,
                )
                if existing_video is None:
                    new_video_ids.append(saved_video.video_id)
                    if subscription.auto_fetch_transcript:
                        try:
                            transcript = self.fetch_transcript(
                                saved_video.video_id,
                                YouTubeTranscriptCreateRequest(),
                            )
                            auto_pipeline_results.append(
                                {
                                    "video_id": saved_video.video_id,
                                    "step": "transcript",
                                    "status": transcript.status.value,
                                    "result_kind": transcript.result_kind.value,
                                    "failure_kind": transcript.failure_kind.value if transcript.failure_kind else None,
                                }
                            )
                        except YouTubeAgentError as exc:
                            auto_pipeline_results.append(
                                {
                                    "video_id": saved_video.video_id,
                                    "step": "transcript",
                                    "status": JobStatus.FAILED.value,
                                    "result_kind": YouTubeResultKind.FAILED.value,
                                    "failure_kind": exc.failure_kind.value,
                                    "failed_stage": exc.failed_stage.value if exc.failed_stage else None,
                                    "reason": exc.reason,
                                }
                            )
                    if subscription.auto_digest:
                        digest = self.generate_digest(
                            saved_video.video_id,
                            YouTubeDigestCreateRequest(),
                        )
                        auto_pipeline_results.append(
                            {
                                "video_id": saved_video.video_id,
                                "step": "digest",
                                "status": digest.status.value,
                                "result_kind": digest.result_kind.value,
                                "failure_kind": digest.failure_kind.value if digest.failure_kind else None,
                                "failed_stage": digest.failed_stage.value if digest.failed_stage else None,
                            }
                        )

            now = utc_now()
            updated_subscription = subscription.model_copy(
                update={
                    "latest_video_id": discovered_video_ids[0] if discovered_video_ids else subscription.latest_video_id,
                    "last_checked_at": now,
                    "updated_at": now,
                    "metadata": {
                        **subscription.metadata,
                        **request.metadata,
                    },
                }
            )
            self._repository.save_subscription(updated_subscription)

            if not discovered_video_ids:
                run = self._complete_run(
                    run,
                    status=JobStatus.COMPLETED,
                    result_kind=YouTubeResultKind.NOOP,
                    failure_kind=YouTubeFailureKind.NO_NEW_VIDEOS_FOUND,
                    reason="source returned no videos",
                    summary="no videos discovered",
                    metadata={"limit": request.limit},
                )
            elif not new_video_ids:
                run = self._complete_run(
                    run,
                    status=JobStatus.COMPLETED,
                    result_kind=YouTubeResultKind.NOOP,
                    failure_kind=YouTubeFailureKind.DUPLICATE_IDEMPOTENT_NOOP,
                    reason="all discovered videos were already stored",
                    summary=f"no new videos across {len(discovered_video_ids)} discovered item(s)",
                    metadata={
                        "discovered_video_ids": discovered_video_ids,
                        "auto_pipeline_results": auto_pipeline_results,
                    },
                )
            else:
                run = self._complete_run(
                    run,
                    status=JobStatus.COMPLETED,
                    result_kind=YouTubeResultKind.SUCCESS,
                    failure_kind=None,
                    reason=None,
                    summary=f"discovered {len(new_video_ids)} new video(s)",
                    metadata={
                        "discovered_video_ids": discovered_video_ids,
                        "new_video_ids": new_video_ids,
                        "auto_pipeline_results": auto_pipeline_results,
                    },
                )

            return YouTubeCheckResultRead(
                run=run,
                subscription=updated_subscription,
                discovered_count=len(discovered_video_ids),
                discovered_video_ids=discovered_video_ids,
                new_video_ids=new_video_ids,
            )
        except YouTubeAgentError as exc:
            self._complete_run(
                run,
                status=JobStatus.FAILED,
                result_kind=YouTubeResultKind.FAILED,
                failure_kind=exc.failure_kind,
                failed_stage=exc.failed_stage or YouTubeFailedStage.DISCOVERY,
                reason=exc.reason,
                summary="subscription check failed",
                metadata=exc.details,
                error=exc.reason,
            )
            raise

    def refresh_video_metadata(self, video_id: str) -> YouTubeVideoRead:
        video = self.get_video(video_id)
        if video is None:
            raise KeyError(video_id)

        run = self._create_run(
            kind=YouTubeRunKind.VIDEO_METADATA_REFRESH,
            subscription_id=video.subscription_id,
            video_id=video_id,
        )
        try:
            snapshot = self._fetcher.fetch_video_metadata(video.source_url)
            refreshed = self._upsert_video_from_snapshot(
                snapshot=snapshot,
                subscription=self._require_subscription(video.subscription_id),
                existing=video,
            )
            changed = self._video_changed(video, refreshed)
            self._complete_run(
                run,
                status=JobStatus.COMPLETED,
                result_kind=YouTubeResultKind.SUCCESS if changed else YouTubeResultKind.NOOP,
                failure_kind=None if changed else YouTubeFailureKind.DUPLICATE_IDEMPOTENT_NOOP,
                reason=None if changed else "video metadata was already up to date",
                summary="video metadata refreshed" if changed else "video metadata unchanged",
                metadata={"video_id": video_id},
            )
            return refreshed
        except YouTubeAgentError as exc:
            self._complete_run(
                run,
                status=JobStatus.FAILED,
                result_kind=YouTubeResultKind.FAILED,
                failure_kind=exc.failure_kind,
                failed_stage=exc.failed_stage or YouTubeFailedStage.METADATA_FETCH,
                reason=exc.reason,
                summary="video metadata refresh failed",
                metadata=exc.details,
                error=exc.reason,
            )
            raise

    def fetch_transcript(
        self,
        video_id: str,
        request: YouTubeTranscriptCreateRequest,
    ) -> YouTubeTranscriptRead:
        video = self.get_video(video_id)
        if video is None:
            raise KeyError(video_id)

        existing = self._repository.get_transcript_by_video_id(video_id)
        if existing is not None and existing.content.strip() and not request.overwrite_existing:
            self._create_noop_run(
                kind=YouTubeRunKind.TRANSCRIPT_FETCH,
                subscription_id=video.subscription_id,
                video_id=video_id,
                summary="transcript already exists",
            )
            return existing

        run = self._create_run(
            kind=YouTubeRunKind.TRANSCRIPT_FETCH,
            subscription_id=video.subscription_id,
            video_id=video_id,
        )
        try:
            payload = self._fetcher.fetch_transcript(
                video.source_url,
                preferred_languages=request.preferred_languages,
                include_auto_generated=request.include_auto_generated,
            )
            transcript = self._save_transcript_success(
                video_id=video_id,
                payload=payload,
                existing=existing,
                metadata=request.metadata,
            )
            updated_video = video.model_copy(
                update={
                    "transcript_id": transcript.transcript_id,
                    "updated_at": utc_now(),
                }
            )
            self._repository.save_video(updated_video)
            self._complete_run(
                run,
                status=transcript.status,
                result_kind=transcript.result_kind,
                failure_kind=transcript.failure_kind,
                failed_stage=transcript.failed_stage,
                reason=transcript.reason,
                summary="transcript ready" if transcript.result_kind == YouTubeResultKind.SUCCESS else "transcript ready with warning",
                metadata={"transcript_id": transcript.transcript_id},
                error=None,
            )
            return transcript
        except YouTubeAgentError as exc:
            transcript = self._save_transcript_failure(
                video_id=video_id,
                existing=existing,
                failure_kind=exc.failure_kind,
                failed_stage=exc.failed_stage or YouTubeFailedStage.TRANSCRIPT_FETCH,
                reason=exc.reason,
                metadata={**request.metadata, **exc.details},
            )
            self._complete_run(
                run,
                status=JobStatus.FAILED,
                result_kind=YouTubeResultKind.FAILED,
                failure_kind=exc.failure_kind,
                failed_stage=exc.failed_stage or YouTubeFailedStage.TRANSCRIPT_FETCH,
                reason=exc.reason,
                summary="transcript fetch failed",
                metadata={"transcript_id": transcript.transcript_id, **exc.details},
                error=exc.reason,
            )
            raise

    def generate_digest(
        self,
        video_id: str,
        request: YouTubeDigestCreateRequest,
    ) -> YouTubeDigestRead:
        video = self.get_video(video_id)
        if video is None:
            raise KeyError(video_id)

        existing = self._repository.get_digest_by_video_id(video_id)
        transcript = self._repository.get_transcript_by_video_id(video_id)
        digest_is_current = (
            existing is not None
            and existing.content.strip()
            and self._digest_is_current(
                digest=existing,
                video=video,
                transcript=transcript,
            )
        )
        if digest_is_current and not request.overwrite_existing:
            self._create_noop_run(
                kind=YouTubeRunKind.DIGEST_GENERATE,
                subscription_id=video.subscription_id,
                video_id=video_id,
                summary="digest already exists",
            )
            return existing

        run = self._create_run(
            kind=YouTubeRunKind.DIGEST_GENERATE,
            subscription_id=video.subscription_id,
            video_id=video_id,
        )

        if transcript is None or not transcript.content.strip():
            failure_kind = transcript.failure_kind if transcript and transcript.failure_kind else YouTubeFailureKind.TRANSCRIPT_UNAVAILABLE
            reason = transcript.reason if transcript and transcript.reason else "digest generation requires transcript content"
            digest = self._save_digest_failure(
                video_id=video_id,
                existing=existing,
                failure_kind=failure_kind,
                failed_stage=YouTubeFailedStage.DIGEST_BUILD,
                reason=reason,
                metadata=request.metadata,
                output_format=request.format,
            )
            self._complete_run(
                run,
                status=JobStatus.FAILED,
                result_kind=YouTubeResultKind.FAILED,
                failure_kind=failure_kind,
                failed_stage=YouTubeFailedStage.DIGEST_BUILD,
                reason=reason,
                summary="digest generation skipped",
                metadata={"digest_id": digest.digest_id},
                error=reason,
            )
            return digest

        content = self._digest_service.generate_digest(
            video=video,
            transcript=transcript,
            output_format=request.format,
        )
        now = utc_now()
        digest = (existing or YouTubeDigestRead(
            digest_id=create_resource_id("ytdigest"),
            video_id=video_id,
            created_at=now,
            updated_at=now,
        )).model_copy(
            update={
                "status": JobStatus.COMPLETED,
                "result_kind": transcript.result_kind,
                "failure_kind": transcript.failure_kind,
                "failed_stage": transcript.failed_stage,
                "reason": transcript.reason,
                "format": request.format,
                "content": content,
                "updated_at": now,
                "metadata": {
                    **(existing.metadata if existing else {}),
                    **request.metadata,
                },
            }
        )
        saved = self._repository.save_digest(digest)
        updated_video = video.model_copy(
            update={
                "digest_id": saved.digest_id,
                "updated_at": now,
            }
        )
        self._repository.save_video(updated_video)
        self._complete_run(
            run,
            status=JobStatus.COMPLETED,
            result_kind=saved.result_kind,
            failure_kind=saved.failure_kind,
            failed_stage=saved.failed_stage,
            reason=saved.reason,
            summary="digest generated",
            metadata={"digest_id": saved.digest_id},
        )
        return saved

    def ask_video(
        self,
        video_id: str,
        request: YouTubeQuestionRequest,
    ) -> YouTubeQuestionAnswerRead:
        video = self.get_video(video_id)
        if video is None:
            raise KeyError(video_id)

        transcript = self._repository.get_transcript_by_video_id(video_id)
        digest = self._repository.get_digest_by_video_id(video_id)
        run = self._create_run(
            kind=YouTubeRunKind.QUESTION_ANSWER,
            subscription_id=video.subscription_id,
            video_id=video_id,
        )

        if transcript is None or not transcript.content.strip():
            failure_kind = transcript.failure_kind if transcript and transcript.failure_kind else YouTubeFailureKind.ASK_CONTEXT_MISSING
            reason = transcript.reason if transcript and transcript.reason else "ask requires transcript content for this video"
            self._complete_run(
                run,
                status=JobStatus.FAILED,
                result_kind=YouTubeResultKind.FAILED,
                failure_kind=failure_kind,
                failed_stage=YouTubeFailedStage.ASK,
                reason=reason,
                summary="question answering blocked",
                metadata={"question": request.question},
                error=reason,
            )
            raise YouTubeAgentError(failure_kind, reason, failed_stage=YouTubeFailedStage.ASK)

        answer = self._digest_service.answer_question(
            video=video,
            question=request.question,
            transcript=transcript,
            digest=digest,
        )
        self._complete_run(
            run,
            status=JobStatus.COMPLETED,
            result_kind=transcript.result_kind,
            failure_kind=transcript.failure_kind,
            failed_stage=transcript.failed_stage,
            reason=transcript.reason,
            summary="question answered",
            metadata={"question": request.question},
        )
        return answer.model_copy(
            update={
                "metadata": {
                    **answer.metadata,
                    **request.metadata,
                }
            }
        )

    def _subscription_defaults_from_descriptor(
        self,
        *,
        descriptor,
        title: str | None,
        auto_fetch_transcript: bool,
        auto_digest: bool,
        poll_interval_minutes: int,
        metadata: dict[str, object],
        status: YouTubeSubscriptionStatus,
        updated_at,
    ) -> dict[str, object]:
        return {
            "source_url": descriptor.normalized_url,
            "normalized_url": descriptor.normalized_url,
            "target_kind": descriptor.target_kind,
            "external_id": descriptor.external_id,
            "title": title or descriptor.title,
            "status": status,
            "auto_fetch_transcript": auto_fetch_transcript,
            "auto_digest": auto_digest,
            "poll_interval_minutes": poll_interval_minutes,
            "updated_at": updated_at,
            "metadata": {
                **descriptor.metadata,
                **metadata,
            },
        }

    def _determine_import_action(
        self,
        *,
        existing: YouTubeSubscriptionRead,
        descriptor,
        item: YouTubeSubscriptionImportItem,
    ) -> str:
        desired_status = item.status
        desired_title = item.title or descriptor.title
        desired_metadata = {
            **descriptor.metadata,
            **item.metadata,
        }
        changed = any(
            (
                existing.title != desired_title,
                existing.status != desired_status,
                existing.auto_fetch_transcript != item.auto_fetch_transcript,
                existing.auto_digest != item.auto_digest,
                existing.poll_interval_minutes != item.poll_interval_minutes,
                existing.metadata != desired_metadata,
            )
        )
        if not changed:
            return "skipped"
        if existing.status == YouTubeSubscriptionStatus.DELETED and desired_status != YouTubeSubscriptionStatus.DELETED:
            return "restored"
        return "updated"

    def _upsert_video_from_snapshot(
        self,
        *,
        snapshot: YouTubeVideoSnapshot,
        subscription: YouTubeSubscriptionRead,
        existing: YouTubeVideoRead | None,
    ) -> YouTubeVideoRead:
        now = utc_now()
        base = existing or YouTubeVideoRead(
            video_id=snapshot.video_id,
            source_url=snapshot.source_url,
            subscription_id=subscription.subscription_id,
            created_at=now,
            updated_at=now,
        )
        updated = base.model_copy(
            update={
                "source_url": snapshot.source_url,
                "subscription_id": subscription.subscription_id,
                "channel_id": snapshot.channel_id or base.channel_id,
                "channel_title": snapshot.channel_title or base.channel_title,
                "title": snapshot.title or base.title,
                "description": snapshot.description or base.description,
                "published_at": snapshot.published_at or base.published_at,
                "duration_seconds": snapshot.duration_seconds or base.duration_seconds,
                "status": JobStatus.COMPLETED,
                "updated_at": now,
                "metadata": {
                    **base.metadata,
                    **snapshot.metadata,
                    "subscription_id": subscription.subscription_id,
                },
            }
        )
        return self._repository.save_video(updated)

    def _save_transcript_success(
        self,
        *,
        video_id: str,
        payload: YouTubeTranscriptPayload,
        existing: YouTubeTranscriptRead | None,
        metadata: dict[str, object],
    ) -> YouTubeTranscriptRead:
        now = utc_now()
        base = existing or YouTubeTranscriptRead(
            transcript_id=create_resource_id("yttranscript"),
            video_id=video_id,
            language=payload.language,
            source=YouTubeTranscriptSource.MISSING,
            created_at=now,
            updated_at=now,
        )
        transcript = base.model_copy(
            update={
                "language": payload.language,
                "source": payload.source,
                "status": JobStatus.COMPLETED,
                "result_kind": payload.result_kind,
                "failure_kind": payload.failure_kind,
                "failed_stage": YouTubeFailedStage.TRANSCRIPT_FETCH if payload.failure_kind else None,
                "reason": payload.reason,
                "content": payload.content,
                "updated_at": now,
                "metadata": {
                    **base.metadata,
                    **payload.metadata,
                    **metadata,
                },
            }
        )
        return self._repository.save_transcript(transcript)

    def _save_transcript_failure(
        self,
        *,
        video_id: str,
        existing: YouTubeTranscriptRead | None,
        failure_kind: YouTubeFailureKind,
        failed_stage: YouTubeFailedStage,
        reason: str,
        metadata: dict[str, object],
    ) -> YouTubeTranscriptRead:
        now = utc_now()
        base = existing or YouTubeTranscriptRead(
            transcript_id=create_resource_id("yttranscript"),
            video_id=video_id,
            language=metadata.get("preferred_languages", ["unknown"])[0] if isinstance(metadata.get("preferred_languages"), list) and metadata.get("preferred_languages") else "unknown",
            source=YouTubeTranscriptSource.MISSING,
            created_at=now,
            updated_at=now,
        )
        transcript = base.model_copy(
            update={
                "source": YouTubeTranscriptSource.MISSING,
                "status": JobStatus.FAILED,
                "result_kind": YouTubeResultKind.FAILED,
                "failure_kind": failure_kind,
                "failed_stage": failed_stage,
                "reason": reason,
                "content": "",
                "updated_at": now,
                "metadata": {
                    **base.metadata,
                    **metadata,
                },
            }
        )
        return self._repository.save_transcript(transcript)

    def _save_digest_failure(
        self,
        *,
        video_id: str,
        existing: YouTubeDigestRead | None,
        failure_kind: YouTubeFailureKind,
        failed_stage: YouTubeFailedStage,
        reason: str,
        metadata: dict[str, object],
        output_format: str,
    ) -> YouTubeDigestRead:
        now = utc_now()
        base = existing or YouTubeDigestRead(
            digest_id=create_resource_id("ytdigest"),
            video_id=video_id,
            created_at=now,
            updated_at=now,
        )
        digest = base.model_copy(
            update={
                "status": JobStatus.FAILED,
                "result_kind": YouTubeResultKind.FAILED,
                "failure_kind": failure_kind,
                "failed_stage": failed_stage,
                "reason": reason,
                "format": output_format,
                "content": "",
                "updated_at": now,
                "metadata": {
                    **base.metadata,
                    **metadata,
                },
            }
        )
        return self._repository.save_digest(digest)

    def _create_run(
        self,
        *,
        kind: YouTubeRunKind,
        subscription_id: str | None = None,
        video_id: str | None = None,
    ) -> YouTubeRunRead:
        now = utc_now()
        run = YouTubeRunRead(
            run_id=create_resource_id("ytrun"),
            kind=kind,
            status=JobStatus.RUNNING,
            subscription_id=subscription_id,
            video_id=video_id,
            created_at=now,
            updated_at=now,
        )
        return self._repository.save_run(run)

    def _create_noop_run(
        self,
        *,
        kind: YouTubeRunKind,
        subscription_id: str | None,
        video_id: str | None,
        summary: str,
    ) -> YouTubeRunRead:
        run = self._create_run(kind=kind, subscription_id=subscription_id, video_id=video_id)
        return self._complete_run(
            run,
            status=JobStatus.COMPLETED,
            result_kind=YouTubeResultKind.NOOP,
            failure_kind=YouTubeFailureKind.DUPLICATE_IDEMPOTENT_NOOP,
            reason=summary,
            summary=summary,
        )

    def _complete_run(
        self,
        run: YouTubeRunRead,
        *,
        status: JobStatus,
        result_kind: YouTubeResultKind,
        failure_kind: YouTubeFailureKind | None,
        failed_stage: YouTubeFailedStage | None = None,
        reason: str | None,
        summary: str,
        metadata: dict[str, object] | None = None,
        error: str | None = None,
    ) -> YouTubeRunRead:
        finished_at = utc_now()
        duration_seconds = max(0.0, (finished_at - run.created_at).total_seconds())
        updated = run.model_copy(
            update={
                "status": status,
                "result_kind": result_kind,
                "failure_kind": failure_kind,
                "failed_stage": failed_stage,
                "reason": reason,
                "summary": summary,
                "duration_seconds": duration_seconds,
                "updated_at": finished_at,
                "metadata": {
                    **run.metadata,
                    **(metadata or {}),
                },
                "error": error,
            }
        )
        return self._repository.save_run(updated)

    def _require_subscription(self, subscription_id: str | None) -> YouTubeSubscriptionRead:
        if subscription_id is None:
            raise KeyError("missing subscription_id")
        subscription = self._repository.get_subscription(subscription_id)
        if subscription is None:
            raise KeyError(subscription_id)
        return subscription

    def _video_changed(self, previous: YouTubeVideoRead, current: YouTubeVideoRead) -> bool:
        comparable_fields = (
            "title",
            "description",
            "channel_title",
            "channel_id",
            "published_at",
            "duration_seconds",
            "metadata",
        )
        return any(getattr(previous, field) != getattr(current, field) for field in comparable_fields)

    def _digest_is_current(
        self,
        *,
        digest: YouTubeDigestRead,
        video: YouTubeVideoRead,
        transcript: YouTubeTranscriptRead | None,
    ) -> bool:
        if digest.updated_at < video.updated_at:
            return False
        if transcript is not None and digest.updated_at < transcript.updated_at:
            return False
        return True
