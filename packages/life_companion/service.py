from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import re
import shutil
from typing import Any, Callable

from autoresearch.personal_packages import (
    PERSONAL_ENTERTAINMENT_CURATOR_PACKAGE_ID,
    PERSONAL_LIFE_COMPANION_PACKAGE_ID,
    PERSONAL_STUDY_WORKSPACE_PACKAGE_ID,
)
from autoresearch.shared.models import (
    StudyDashboardItemRead,
    StudyDashboardItemStatus,
    StudyDashboardReadingDepth,
    StudyDashboardSourceKind,
    utc_now,
)
from autoresearch.shared.store import Repository, create_resource_id

from .schema import (
    LifeCompanionDependencyRead,
    LifeCompanionStateRead,
    PersonalActivityEventRead,
    PersonalActivityEventRequest,
    PersonalContentIngestRead,
    PersonalContentIngestRequest,
    PersonalContentItemRead,
    PersonalDailyPlanBlockRead,
    PersonalDailyPlanRead,
    PersonalDailyPlanRequest,
    PersonalEntertainmentSessionRequest,
    PersonalEntertainmentSessionRead,
    PersonalExportJobRead,
    PersonalExportRequest,
    PersonalExportStatus,
    PersonalExportTarget,
    PersonalFeedbackRead,
    PersonalFeedbackRequest,
    PersonalFeedbackSignal,
    PersonalFlashcardRead,
    PersonalRecommendationKind,
    PersonalRecommendationRead,
    PersonalRecommendationRequest,
    PersonalRecommendationResponse,
    PersonalRecommendationRowRead,
    PersonalReviewRating,
    PersonalReviewRead,
    PersonalReviewRequest,
    PersonalPromoteRead,
    PersonalPromoteRequest,
    PersonalPreferenceProfileRead,
    PersonalSearchRead,
    PersonalSourceAccountRead,
    PersonalContentKind,
)


PackageEnabled = Callable[[str], bool]


@dataclass(frozen=True, slots=True)
class LifeCompanionRepositories:
    contents: Repository[PersonalContentItemRead]
    highlights: Repository[Any]
    notes: Repository[Any]
    flashcards: Repository[PersonalFlashcardRead]
    reviews: Repository[PersonalReviewRead]
    recommendations: Repository[PersonalRecommendationRead]
    feedback: Repository[PersonalFeedbackRead]
    plans: Repository[PersonalDailyPlanRead]
    exports: Repository[PersonalExportJobRead]
    source_accounts: Repository[PersonalSourceAccountRead]
    preference_profiles: Repository[PersonalPreferenceProfileRead]
    events: Repository[PersonalActivityEventRead]
    study_items: Repository[StudyDashboardItemRead]


class LifeCompanionService:
    """Personal learning and entertainment operating layer."""

    def __init__(
        self,
        *,
        repositories: LifeCompanionRepositories,
        artifact_root: Path,
        study_workbench_settings: Any,
        package_enabled: PackageEnabled,
    ) -> None:
        self._repos = repositories
        self._artifact_root = artifact_root.expanduser().resolve()
        self._artifact_root.mkdir(parents=True, exist_ok=True)
        self._study_settings = study_workbench_settings
        self._package_enabled = package_enabled

    def dependency_state(self) -> list[LifeCompanionDependencyRead]:
        return [
            LifeCompanionDependencyRead(
                package_id=PERSONAL_STUDY_WORKSPACE_PACKAGE_ID,
                enabled=self._package_enabled(PERSONAL_STUDY_WORKSPACE_PACKAGE_ID),
            ),
            LifeCompanionDependencyRead(
                package_id=PERSONAL_ENTERTAINMENT_CURATOR_PACKAGE_ID,
                enabled=self._package_enabled(PERSONAL_ENTERTAINMENT_CURATOR_PACKAGE_ID),
            ),
        ]

    def is_enabled(self) -> bool:
        return self._package_enabled(PERSONAL_LIFE_COMPANION_PACKAGE_ID)

    def is_ready(self) -> bool:
        return self.is_enabled() and all(item.enabled for item in self.dependency_state())

    def state(self) -> LifeCompanionStateRead:
        rows = self.recommendations(PersonalRecommendationRequest(limit=18)).rows if self.is_ready() else []
        plans = sorted(self._repos.plans.list(), key=lambda item: item.updated_at, reverse=True)
        due_cards = self._due_cards(limit=12)
        exports = sorted(self._repos.exports.list(), key=lambda item: item.updated_at, reverse=True)[:12]
        events = sorted(self._repos.events.list(), key=lambda item: item.created_at, reverse=True)[:20]
        enabled = self.is_enabled()
        deps = self.dependency_state()
        status = "ok" if enabled and all(item.enabled for item in deps) else (
            "missing_dependency" if enabled else "disabled"
        )
        preference_profile = self._preference_profile() if status == "ok" else None
        if status == "ok" and not rows:
            status = "degraded"
        return LifeCompanionStateRead(
            status=status,
            enabled=enabled,
            dependencies=deps,
            rows=rows,
            active_plan=plans[0] if plans else None,
            due_cards=due_cards,
            exports=exports,
            source_accounts=sorted(self._repos.source_accounts.list(), key=lambda item: item.provider),
            preference_profile=preference_profile,
            recent_activity=events,
            metadata={
                "content_count": len(self._repos.contents.list()),
                "study_item_count": len(self._visible_study_items()),
                "card_count": len(self._repos.flashcards.list()),
                "export_count": len(exports),
            },
        )

    def ingest(self, request: PersonalContentIngestRequest) -> PersonalContentIngestRead:
        if not self.is_ready():
            return PersonalContentIngestRead(
                status="disabled",
                metadata=self._disabled_metadata(),
            )
        now = utc_now()
        items: list[PersonalContentItemRead] = []
        scanned = 0
        skipped = 0
        if request.title or request.text or request.source_url:
            item = PersonalContentItemRead(
                content_id=create_resource_id("content"),
                kind=request.kind,
                title=(request.title or _title_from_text(request.text) or request.source_url or "Untitled").strip()[:180],
                summary=_summarize_text(request.text),
                source_url=request.source_url,
                source_app=request.source_app,
                tags=_dedupe([*request.tags, *_extract_topics(request.text or request.title)]),
                topics=_extract_topics(f"{request.title}\n{request.text}"),
                score=_score_text(request.title, request.text),
                created_at=now,
                updated_at=now,
                metadata=request.metadata,
            )
            self._repos.contents.save(item.content_id, item)
            self._record_event("content.ingested", item.content_id, source="api", metadata=item.metadata)
            items.append(item)

        if request.scan_exports:
            for path in self._export_scan_candidates(limit=request.limit):
                scanned += 1
                if any(str(path) == item.metadata.get("source_path") for item in self._repos.contents.list()):
                    skipped += 1
                    continue
                parsed = self._content_from_export_path(path)
                if parsed is None:
                    skipped += 1
                    continue
                self._repos.contents.save(parsed.content_id, parsed)
                self._record_event(
                    "content.backfilled",
                    parsed.content_id,
                    source=parsed.source_app or "export_scan",
                    metadata={"source_path": str(path)},
                )
                items.append(parsed)

        return PersonalContentIngestRead(
            status="completed" if items else ("skipped" if skipped else "degraded"),
            items=items,
            scanned_count=scanned + (1 if request.title or request.text or request.source_url else 0),
            imported_count=len(items),
            skipped_count=skipped,
            metadata={"scan_exports": request.scan_exports},
        )

    def recommendations(self, request: PersonalRecommendationRequest) -> PersonalRecommendationResponse:
        if not self.is_ready():
            return PersonalRecommendationResponse(status="disabled", metadata=self._disabled_metadata())

        blocked = self._blocked_targets()
        rows: list[PersonalRecommendationRowRead] = []
        saved: list[PersonalRecommendationRead] = []
        study_items = self._visible_study_items()
        due_cards = self._due_cards(limit=10)
        preference_profile = self._preference_profile()

        if request.include_study:
            continue_items = [
                self._recommendation_from_study_item(item, row="continue")
                for item in study_items
                if item.status in {StudyDashboardItemStatus.NEW, StudyDashboardItemStatus.UNREAD}
            ][:8]
            deep_items = [
                self._recommendation_from_study_item(item, row="deep")
                for item in study_items
                if item.reading_depth == StudyDashboardReadingDepth.DEEP
            ][:6]
            rows.extend(
                [
                    PersonalRecommendationRowRead(
                        row_id="continue_learning",
                        title="Continue learning",
                        reason="Prioritizes new and unread items with recent learning value.",
                        items=self._without_blocked(continue_items, blocked),
                    ),
                    PersonalRecommendationRowRead(
                        row_id="deep_study",
                        title="Deep study",
                        reason="High-value items suited for MarginNote4 reading and map building.",
                        items=self._without_blocked(deep_items, blocked),
                    ),
                ]
            )

        if request.include_review:
            review_items = [
                PersonalRecommendationRead(
                    recommendation_id=create_resource_id("rec"),
                    kind=PersonalRecommendationKind.REVIEW,
                    title=card.front,
                    summary=card.back[:240],
                    reason="Due for active recall and spaced repetition.",
                    score=max(55.0, 92.0 - card.review_count * 5),
                    estimated_minutes=3,
                    actions=["review", "mark_done", "export_cards"],
                    related_item_ids=[card.card_id],
                    metadata={"card_id": card.card_id},
                )
                for card in due_cards
            ]
            rows.append(
                PersonalRecommendationRowRead(
                    row_id="review_queue",
                    title="Review queue",
                    reason="Cards due now get a small, concrete practice row.",
                    items=self._without_blocked(review_items, blocked),
                )
            )

        if request.include_entertainment:
            entertainment = self.entertainment_session(
                PersonalEntertainmentSessionRequest(
                    request_text=request.request_text,
                    mood=request.mood,
                    focus=request.focus,
                    company=request.company,
                    available_minutes=min(request.available_minutes, 120),
                    metadata=request.metadata,
                )
            )
            rows.append(
                PersonalRecommendationRowRead(
                    row_id="entertainment_dj",
                    title="Entertainment DJ",
                    reason="Balances mood, focus, time, and legal source boundaries.",
                    items=self._without_blocked(entertainment.recommendations, blocked),
                )
            )

        rows.append(
            PersonalRecommendationRowRead(
                row_id="export_next",
                title="Export next",
                reason="Keeps GoodNotes and MarginNote4 as first-class study surfaces.",
                items=self._without_blocked(self._export_recommendations(), blocked),
            )
        )

        clipped_rows: list[PersonalRecommendationRowRead] = []
        remaining = request.limit
        for row in rows:
            if remaining <= 0:
                break
            items = row.items[:remaining]
            remaining -= len(items)
            clipped = row.model_copy(update={"items": items})
            clipped_rows.append(clipped)
            saved.extend(items)
        for item in saved:
            self._repos.recommendations.save(item.recommendation_id, item)
        return PersonalRecommendationResponse(
            status="completed" if saved else "degraded",
            rows=clipped_rows,
            metadata={
                "mood": request.mood,
                "focus": request.focus,
                "company": request.company,
                "available_minutes": request.available_minutes,
                "preference_profile_id": preference_profile.profile_id,
            },
        )

    def daily_plan(self, request: PersonalDailyPlanRequest) -> PersonalDailyPlanRead:
        if not self.is_ready():
            return PersonalDailyPlanRead(
                plan_id=create_resource_id("plan"),
                plan_date=request.plan_date or utc_now().date().isoformat(),
                title="Personal package disabled",
                status="disabled",
                metadata=self._disabled_metadata(),
            )
        plan_date = request.plan_date or utc_now().date().isoformat()
        recs = self.recommendations(
            PersonalRecommendationRequest(
                mood=request.mood,
                focus=request.focus,
                available_minutes=request.available_minutes,
                request_text="daily study and entertainment plan",
                limit=24,
            )
        )
        first_study = _first_items(recs.rows, kind=PersonalRecommendationKind.STUDY, limit=3)
        first_review = _first_items(recs.rows, kind=PersonalRecommendationKind.REVIEW, limit=3)
        first_fun = _first_items(recs.rows, kind=PersonalRecommendationKind.ENTERTAINMENT, limit=2)
        blocks = [
            PersonalDailyPlanBlockRead(
                block_id=create_resource_id("block"),
                kind="study",
                title="Deep study block",
                minutes=min(45, max(20, request.available_minutes // 3)),
                recommendation_ids=[item.recommendation_id for item in first_study],
            ),
            PersonalDailyPlanBlockRead(
                block_id=create_resource_id("block"),
                kind="review",
                title="Active recall review",
                minutes=15,
                recommendation_ids=[item.recommendation_id for item in first_review],
            ),
            PersonalDailyPlanBlockRead(
                block_id=create_resource_id("block"),
                kind="reward",
                title="Legal entertainment reward",
                minutes=min(30, max(10, request.available_minutes // 4)),
                recommendation_ids=[item.recommendation_id for item in first_fun],
            ),
            PersonalDailyPlanBlockRead(
                block_id=create_resource_id("block"),
                kind="export",
                title="GoodNotes and MarginNote4 export",
                minutes=5,
                recommendation_ids=[],
            ),
        ]
        plan = PersonalDailyPlanRead(
            plan_id=create_resource_id("plan"),
            plan_date=plan_date,
            title=f"Personal plan {plan_date}",
            blocks=blocks,
            recommendation_rows=recs.rows,
            metadata={
                "mood": request.mood,
                "focus": request.focus,
                "available_minutes": request.available_minutes,
                "requested_by": request.requested_by,
            },
        )
        export_ids: list[str] = []
        if request.auto_export:
            export = self.export(
                PersonalExportRequest(
                    target=PersonalExportTarget.BOTH,
                    plan_id=plan.plan_id,
                    title=plan.title,
                    requested_by=request.requested_by,
                ),
                plan=plan,
            )
            export_ids.append(export.export_id)
        plan = plan.model_copy(update={"export_job_ids": export_ids, "updated_at": utc_now()})
        self._repos.plans.save(plan.plan_id, plan)
        self._record_event("plan.created", plan.plan_id, source="api", metadata=plan.metadata)
        return plan

    def create_cards(self, request: PersonalReviewRequest | None = None) -> list[PersonalFlashcardRead]:
        if not self.is_ready():
            return []
        request = request or PersonalReviewRequest()
        if request.card_id:
            card = self._repos.flashcards.get(request.card_id)
            return [card] if card else []
        cards: list[PersonalFlashcardRead] = []
        existing_keys = {
            str(card.metadata.get("source_key") or card.study_item_id or card.front)
            for card in self._repos.flashcards.list()
        }
        for item in self._visible_study_items()[: min(request.limit, 20)]:
            source_key = f"study:{item.item_id}"
            if source_key in existing_keys:
                continue
            fronts = [
                f"What is the main point of {item.title}?",
                f"Why does {item.title} matter?",
            ]
            backs = [
                item.summary or item.why_it_matters or item.suggested_action,
                item.why_it_matters or item.suggested_action or item.summary,
            ]
            for front, back in zip(fronts, backs):
                card = PersonalFlashcardRead(
                    card_id=create_resource_id("card"),
                    study_item_id=item.item_id,
                    front=front[:280],
                    back=(back or item.title)[:1200],
                    tags=_dedupe([*item.technologies[:5], item.source_kind.value]),
                    external_refs={"study_item_id": item.item_id, "source_url": item.source_url},
                    metadata={"source_key": source_key, "source_kind": item.source_kind.value},
                )
                self._repos.flashcards.save(card.card_id, card)
                cards.append(card)
            self._record_event("cards.generated", item.item_id, source="study_coach", metadata={"count": len(fronts)})
        return cards

    def review(self, request: PersonalReviewRequest) -> PersonalReviewRead | list[PersonalFlashcardRead]:
        if not self.is_ready():
            return []
        if not request.card_id or request.rating is None:
            return self._due_cards(limit=request.limit)
        card = self._repos.flashcards.get(request.card_id)
        if card is None:
            return PersonalReviewRead(
                review_id=create_resource_id("review"),
                card_id=request.card_id,
                rating=request.rating,
                metadata={"status": "missing_card"},
            )
        interval = _next_interval(card.interval_days, request.rating)
        next_due = utc_now() + timedelta(days=interval)
        updated = card.model_copy(
            update={
                "due_at": next_due,
                "interval_days": interval,
                "ease": _next_ease(card.ease, request.rating),
                "review_count": card.review_count + 1,
                "updated_at": utc_now(),
            }
        )
        self._repos.flashcards.save(updated.card_id, updated)
        review = PersonalReviewRead(
            review_id=create_resource_id("review"),
            card_id=card.card_id,
            rating=request.rating,
            next_due_at=next_due,
            metadata=request.metadata,
        )
        self._repos.reviews.save(review.review_id, review)
        self._record_event(
            "review.completed",
            card.card_id,
            source="study_coach",
            metadata={"rating": request.rating.value, "next_due_at": next_due.isoformat()},
        )
        return review

    def entertainment_session(
        self,
        request: PersonalEntertainmentSessionRequest,
    ) -> PersonalEntertainmentSessionRead:
        if not self.is_ready():
            return PersonalEntertainmentSessionRead(status="disabled", metadata=self._disabled_metadata())
        try:
            from packages.entertainment_curator.service import EntertainmentCuratorTelegramService
        except Exception as exc:
            return PersonalEntertainmentSessionRead(
                status="degraded",
                answer=f"Entertainment curator unavailable: {exc}",
                metadata={"error": str(exc)},
            )

        raw_text = request.request_text.strip() or (
            f"/entertain mood={request.mood} focus={request.focus} "
            f"company={request.company} time={request.available_minutes}m"
        )
        payload = EntertainmentCuratorTelegramService().handle_telegram_message(
            raw_text,
            requested_by=request.requested_by,
            metadata={**request.metadata, "source": "life_companion"},
        )
        recs: list[PersonalRecommendationRead] = []
        for item in payload.get("recommendations", []):
            if not isinstance(item, dict):
                continue
            rec = PersonalRecommendationRead(
                recommendation_id=create_resource_id("rec"),
                kind=PersonalRecommendationKind.ENTERTAINMENT,
                title=str(item.get("title") or "Entertainment recommendation")[:180],
                summary=str(item.get("reason") or item.get("alternative") or ""),
                reason=str(item.get("reason") or "Fits the requested mood and context."),
                source_app=str(item.get("platform") or "entertainment_curator"),
                score=70.0,
                estimated_minutes=_minutes_from_text(str(item.get("estimated_time") or "")),
                actions=["play_official", "save_for_later", "promote_to_study", "feedback"],
                metadata={
                    "search_query": item.get("search_query"),
                    "alternative": item.get("alternative"),
                    "platform": item.get("platform"),
                    "type": item.get("type"),
                },
            )
            self._repos.recommendations.save(rec.recommendation_id, rec)
            recs.append(rec)
        self._record_event("entertainment.session", "", source="entertainment_dj", metadata=payload.get("metadata") or {})
        return PersonalEntertainmentSessionRead(
            status="completed",
            recommendations=recs,
            answer=str(payload.get("answer") or ""),
            selected_profile=str((payload.get("metadata") or {}).get("selected_youtube_profile") or ""),
            metadata=payload.get("metadata") or {},
        )

    def export(self, request: PersonalExportRequest, *, plan: PersonalDailyPlanRead | None = None) -> PersonalExportJobRead:
        if not self.is_ready():
            return PersonalExportJobRead(
                export_id=create_resource_id("export"),
                target=request.target,
                status=PersonalExportStatus.FAILED,
                title=request.title or "Personal export disabled",
                metadata=self._disabled_metadata(),
            )
        plan = plan or (self._repos.plans.get(request.plan_id) if request.plan_id else None)
        title = request.title or (plan.title if plan else "Personal study pack")
        export_id = create_resource_id("export")
        root = self._artifact_root / "exports" / export_id
        root.mkdir(parents=True, exist_ok=True)
        markdown = self._render_export_markdown(title=title, plan=plan)
        markdown_path = root / f"{_slugify(title)}.md"
        pdf_path = root / f"{_slugify(title)}.pdf"
        csv_path = root / f"{_slugify(title)}-cards.csv"
        sidecar_path = root / f"{_slugify(title)}-marginnote-sidecar.md"
        markdown_path.write_text(markdown, encoding="utf-8")
        pdf_path.write_bytes(_minimal_pdf(markdown.splitlines()[:100]))
        artifact_paths = [str(markdown_path), str(pdf_path)]
        if request.include_cards:
            csv_path.write_text(self._render_cards_csv(), encoding="utf-8")
            artifact_paths.append(str(csv_path))
        if request.include_marginnote_sidecar:
            sidecar_path.write_text(self._render_marginnote_sidecar(plan=plan, pdf_path=pdf_path), encoding="utf-8")
            artifact_paths.append(str(sidecar_path))

        copied_paths = self._copy_export_artifacts(
            target=request.target,
            pdf_path=pdf_path,
            csv_path=csv_path if csv_path.exists() else None,
            sidecar_path=sidecar_path if sidecar_path.exists() else None,
        )
        status = PersonalExportStatus.COPIED if copied_paths else PersonalExportStatus.AWAITING_IMPORT
        job = PersonalExportJobRead(
            export_id=export_id,
            target=request.target,
            status=status,
            title=title,
            artifact_paths=artifact_paths,
            copied_paths=copied_paths,
            metadata={
                "plan_id": request.plan_id or (plan.plan_id if plan else ""),
                "requested_by": request.requested_by,
                "targets": _targets(request.target),
            },
        )
        self._repos.exports.save(job.export_id, job)
        self._record_event("export.created", job.export_id, source="artifact_exporter", metadata=job.metadata)
        return job

    def feedback(self, request: PersonalFeedbackRequest) -> PersonalFeedbackRead:
        feedback = PersonalFeedbackRead(
            feedback_id=create_resource_id("feedback"),
            target_id=request.target_id,
            signal=request.signal,
            note=request.note,
            source=request.source,
            metadata=request.metadata,
        )
        self._repos.feedback.save(feedback.feedback_id, feedback)
        self._record_event(
            "feedback.recorded",
            request.target_id,
            source=request.source,
            metadata={"signal": request.signal.value, **request.metadata},
        )
        return feedback

    def promote(self, request: PersonalPromoteRequest) -> PersonalPromoteRead:
        if not self.is_ready():
            return PersonalPromoteRead(status="disabled", metadata=self._disabled_metadata())
        recommendation = self._repos.recommendations.get(request.recommendation_id) if request.recommendation_id else None
        title = request.title or (recommendation.title if recommendation else "")
        summary = request.summary or (recommendation.summary if recommendation else "")
        source_url = request.source_url or (recommendation.source_url if recommendation else "")
        if not title:
            return PersonalPromoteRead(status="degraded", metadata={"reason": "title is required"})
        now = utc_now()
        content = PersonalContentItemRead(
            content_id=create_resource_id("content"),
            kind=PersonalContentKind.STUDY_ITEM,
            title=title[:180],
            summary=summary,
            source_url=source_url,
            source_app="life_companion",
            tags=_extract_topics(f"{title}\n{summary}"),
            topics=_extract_topics(f"{title}\n{summary}"),
            external_refs={"recommendation_id": request.recommendation_id} if request.recommendation_id else {},
            score=72.0,
            created_at=now,
            updated_at=now,
            metadata={**request.metadata, "promoted": True},
        )
        self._repos.contents.save(content.content_id, content)
        study_item = StudyDashboardItemRead(
            item_id=create_resource_id("study_item"),
            source_kind=StudyDashboardSourceKind.LOCAL,
            source_key=f"life_companion:{content.content_id}",
            title=content.title,
            summary=content.summary,
            why_it_matters="Promoted from the personal learning and entertainment recommendation loop.",
            technologies=content.topics,
            source_url=content.source_url,
            reading_depth=StudyDashboardReadingDepth.READ,
            suggested_action="Read, annotate, and turn into cards.",
            status=StudyDashboardItemStatus.NEW,
            score=content.score,
            created_at=now,
            updated_at=now,
            metadata={
                "source": "life_companion",
                "content_id": content.content_id,
                "recommendation_id": request.recommendation_id,
                **request.metadata,
            },
        )
        self._repos.study_items.save(study_item.item_id, study_item)
        self._record_event("content.promoted", content.content_id, source="promote", metadata=study_item.metadata)
        return PersonalPromoteRead(content=content, study_item=study_item)

    def search(self, query: str) -> PersonalSearchRead:
        normalized = query.strip().lower()
        if not normalized:
            return PersonalSearchRead(query=query)
        contents = [
            item
            for item in self._repos.contents.list()
            if normalized in f"{item.title}\n{item.summary}\n{' '.join(item.tags)}".lower()
        ][:20]
        recommendations = [
            item
            for item in self._repos.recommendations.list()
            if normalized in f"{item.title}\n{item.summary}\n{item.reason}".lower()
        ][:20]
        cards = [
            item
            for item in self._repos.flashcards.list()
            if normalized in f"{item.front}\n{item.back}\n{' '.join(item.tags)}".lower()
        ][:20]
        return PersonalSearchRead(query=query, items=contents, recommendations=recommendations, cards=cards)

    def record_event(self, request: PersonalActivityEventRequest) -> PersonalActivityEventRead:
        event = PersonalActivityEventRead(
            event_id=create_resource_id("event"),
            event_type=request.event_type,
            target_id=request.target_id,
            source=request.source,
            metadata=request.metadata,
        )
        self._repos.events.save(event.event_id, event)
        return event

    def _visible_study_items(self) -> list[StudyDashboardItemRead]:
        return sorted(
            [item for item in self._repos.study_items.list() if item.status != StudyDashboardItemStatus.ARCHIVED],
            key=lambda item: (item.score, item.updated_at),
            reverse=True,
        )

    def _preference_profile(self) -> PersonalPreferenceProfileRead:
        profiles = sorted(self._repos.preference_profiles.list(), key=lambda item: item.updated_at, reverse=True)
        if profiles:
            return profiles[0]
        profile = PersonalPreferenceProfileRead(
            profile_id="default",
            display_name="Default personal profile",
            mood_weights={"mixed": 1.0, "focus": 0.8, "relax": 0.7},
            source_weights={"study_dashboard": 1.0, "entertainment_curator": 0.8},
            metadata={"created_by": "life_companion"},
        )
        self._repos.preference_profiles.save(profile.profile_id, profile)
        return profile

    def _due_cards(self, *, limit: int) -> list[PersonalFlashcardRead]:
        now = utc_now()
        return sorted(
            [card for card in self._repos.flashcards.list() if card.due_at <= now],
            key=lambda card: card.due_at,
        )[:limit]

    def _recommendation_from_study_item(self, item: StudyDashboardItemRead, *, row: str) -> PersonalRecommendationRead:
        return PersonalRecommendationRead(
            recommendation_id=create_resource_id("rec"),
            kind=PersonalRecommendationKind.STUDY,
            title=item.title,
            summary=item.summary,
            reason=item.why_it_matters or item.suggested_action,
            source_url=item.source_url,
            source_app=item.source_kind.value,
            score=min(100.0, item.score + (8 if row == "deep" else 0)),
            estimated_minutes=35 if item.reading_depth == StudyDashboardReadingDepth.DEEP else 18,
            actions=["open_source", "deep_dive", "generate_cards", "export"],
            related_item_ids=[item.item_id],
            metadata={"study_item_id": item.item_id, "status": item.status.value, "reading_depth": item.reading_depth.value},
        )

    def _export_recommendations(self) -> list[PersonalRecommendationRead]:
        latest_plan = sorted(self._repos.plans.list(), key=lambda item: item.updated_at, reverse=True)
        return [
            PersonalRecommendationRead(
                recommendation_id=create_resource_id("rec"),
                kind=PersonalRecommendationKind.EXPORT,
                title="Prepare GoodNotes and MarginNote4 study pack",
                summary="Generate PDF, card CSV, and MarginNote sidecar with stable IDs for backfill.",
                reason="Handwriting and deep-reading surfaces should stay synchronized with AAS.",
                score=78.0,
                estimated_minutes=5,
                actions=["export_goodnotes", "export_marginnote", "scan_backfill"],
                related_item_ids=[latest_plan[0].plan_id] if latest_plan else [],
                metadata={"target": "both"},
            )
        ]

    def _blocked_targets(self) -> set[str]:
        blocked_signals = {PersonalFeedbackSignal.NOT_INTERESTED, PersonalFeedbackSignal.HIDE_SOURCE}
        return {item.target_id for item in self._repos.feedback.list() if item.signal in blocked_signals}

    def _without_blocked(
        self,
        items: list[PersonalRecommendationRead],
        blocked: set[str],
    ) -> list[PersonalRecommendationRead]:
        return [
            item
            for item in items
            if item.recommendation_id not in blocked
            and not any(related in blocked for related in item.related_item_ids)
            and item.source_app not in blocked
        ]

    def _export_scan_candidates(self, *, limit: int) -> list[Path]:
        roots: list[Path] = []
        roots.extend(getattr(self._study_settings, "goodnotes_backup_dirs", []) or [])
        roots.extend(getattr(self._study_settings, "marginnote_export_dirs", []) or [])
        candidates: list[Path] = []
        for raw_root in roots:
            root = Path(raw_root).expanduser()
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".md", ".txt", ".csv", ".tsv", ".apkg", ".marginpkg"}:
                    candidates.append(path)
                    if len(candidates) >= limit:
                        return candidates
        return candidates

    def _content_from_export_path(self, path: Path) -> PersonalContentItemRead | None:
        now = utc_now()
        suffix = path.suffix.lower()
        source_app = "marginnote4" if "margin" in path.as_posix().lower() or suffix in {".apkg", ".marginpkg"} else "goodnotes"
        if suffix in {".md", ".txt", ".csv", ".tsv"}:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                return None
            title = _title_from_text(text) or path.stem
            return PersonalContentItemRead(
                content_id=create_resource_id("content"),
                kind=PersonalContentKind.NOTE,
                title=title[:180],
                summary=_summarize_text(text),
                source_app=source_app,
                tags=_extract_topics(text),
                topics=_extract_topics(text),
                score=_score_text(title, text),
                created_at=now,
                updated_at=now,
                metadata={"source_path": str(path), "backfill": True},
            )
        if suffix in {".apkg", ".marginpkg"}:
            return PersonalContentItemRead(
                content_id=create_resource_id("content"),
                kind=PersonalContentKind.FLASHCARD_DECK,
                title=path.stem[:180],
                summary=f"Backfilled {source_app} package for traceability.",
                source_app=source_app,
                tags=[source_app, suffix.lstrip(".")],
                topics=[source_app],
                score=60.0,
                created_at=now,
                updated_at=now,
                metadata={"source_path": str(path), "backfill": True, "parser": "archive_reference"},
            )
        return None

    def _render_export_markdown(self, *, title: str, plan: PersonalDailyPlanRead | None) -> str:
        lines = [
            "---",
            f"title: {title}",
            f"generated_at: {utc_now().isoformat()}",
            "targets:",
            "  - goodnotes",
            "  - marginnote4",
            "---",
            "",
            f"# {title}",
            "",
            "## Daily plan",
        ]
        if plan is not None:
            lines.append(f"- plan_id: `{plan.plan_id}`")
            for block in plan.blocks:
                lines.append(f"- [ ] `{block.block_id}` {block.kind}: {block.title} ({block.minutes} min)")
        else:
            lines.append("- [ ] Deep study")
            lines.append("- [ ] Active recall")
            lines.append("- [ ] Legal entertainment reward")
        lines.extend(["", "## Study queue"])
        for item in self._visible_study_items()[:8]:
            source = f" source={item.source_url}" if item.source_url else ""
            lines.extend(
                [
                    "",
                    f"### {item.title}",
                    f"- item_id: `{item.item_id}`{source}",
                    f"- depth: `{item.reading_depth.value}` score={item.score:.0f}",
                    f"- action: {item.suggested_action}",
                    "",
                    item.summary or item.why_it_matters,
                    "",
                    "Notes:",
                    "- ",
                    "- ",
                ]
            )
        lines.extend(["", "## Review cards"])
        for card in self._repos.flashcards.list()[:20]:
            lines.append(f"- `{card.card_id}` {card.front}")
        return "\n".join(lines).strip() + "\n"

    def _render_cards_csv(self) -> str:
        lines = ["front,back,tags,card_id"]
        for card in self._repos.flashcards.list()[:200]:
            lines.append(
                ",".join(
                    [
                        _csv_cell(card.front),
                        _csv_cell(card.back),
                        _csv_cell(" ".join(card.tags)),
                        _csv_cell(card.card_id),
                    ]
                )
            )
        if len(lines) == 1:
            lines.append('"Create one recall question","Generate cards from /cards first","life_companion",""')
        return "\n".join(lines) + "\n"

    def _render_marginnote_sidecar(self, *, plan: PersonalDailyPlanRead | None, pdf_path: Path) -> str:
        lines = [
            "# MarginNote4 Sidecar",
            "",
            f"- pdf: `{pdf_path}`",
            f"- generated_at: `{utc_now().isoformat()}`",
            "",
            "## Backlinks",
        ]
        if plan is not None:
            lines.append(f"- plan_id: `{plan.plan_id}`")
        for item in self._visible_study_items()[:20]:
            lines.append(f"- `{item.item_id}` -> {item.source_url or item.source_key}")
        lines.extend(
            [
                "",
                "## Backfill Contract",
                "",
                "Keep item_id, plan_id, and card_id strings in exported notes so AAS can align MarginNote4 study results later.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _copy_export_artifacts(
        self,
        *,
        target: PersonalExportTarget,
        pdf_path: Path,
        csv_path: Path | None,
        sidecar_path: Path | None,
    ) -> list[str]:
        copied: list[str] = []
        target_values = _targets(target)
        if "goodnotes" in target_values:
            inbox = getattr(self._study_settings, "goodnotes_inbox_dir", None)
            if inbox:
                copied.extend(_copy_many(Path(inbox), [pdf_path, *([csv_path] if csv_path else [])]))
        if "marginnote" in target_values:
            inbox = getattr(self._study_settings, "marginnote_inbox_dir", None)
            if inbox:
                copied.extend(_copy_many(Path(inbox), [pdf_path, *([sidecar_path] if sidecar_path else [])]))
        return copied

    def _record_event(self, event_type: str, target_id: str, *, source: str, metadata: dict[str, Any] | None = None) -> None:
        event = PersonalActivityEventRead(
            event_id=create_resource_id("event"),
            event_type=event_type,
            target_id=target_id,
            source=source,
            metadata=metadata or {},
        )
        self._repos.events.save(event.event_id, event)

    def _disabled_metadata(self) -> dict[str, Any]:
        return {
            "package_id": PERSONAL_LIFE_COMPANION_PACKAGE_ID,
            "package_enabled": self.is_enabled(),
            "dependencies": [item.model_dump(mode="json") for item in self.dependency_state()],
        }


def _targets(target: PersonalExportTarget) -> list[str]:
    if target == PersonalExportTarget.GOODNOTES:
        return ["goodnotes"]
    if target == PersonalExportTarget.MARGINNOTE:
        return ["marginnote"]
    return ["goodnotes", "marginnote"]


def _first_items(
    rows: list[PersonalRecommendationRowRead],
    *,
    kind: PersonalRecommendationKind,
    limit: int,
) -> list[PersonalRecommendationRead]:
    out: list[PersonalRecommendationRead] = []
    for row in rows:
        for item in row.items:
            if item.kind == kind:
                out.append(item)
                if len(out) >= limit:
                    return out
    return out


def _copy_many(destination: Path, paths: list[Path | None]) -> list[str]:
    copied: list[str] = []
    destination = destination.expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for path in paths:
        if path is None or not path.exists():
            continue
        target = destination / path.name
        shutil.copyfile(path, target)
        copied.append(str(target))
    return copied


def _next_interval(previous: int, rating: PersonalReviewRating) -> int:
    if rating == PersonalReviewRating.AGAIN:
        return 0
    if rating == PersonalReviewRating.HARD:
        return max(1, previous)
    if rating == PersonalReviewRating.GOOD:
        return max(1, previous * 2)
    return max(2, previous * 3)


def _next_ease(previous: float, rating: PersonalReviewRating) -> float:
    delta = {
        PersonalReviewRating.AGAIN: -0.2,
        PersonalReviewRating.HARD: -0.05,
        PersonalReviewRating.GOOD: 0.05,
        PersonalReviewRating.EASY: 0.15,
    }[rating]
    return max(1.3, min(3.5, previous + delta))


def _title_from_text(text: str) -> str:
    for line in text.splitlines():
        cleaned = line.strip().strip("#").strip()
        if cleaned:
            return cleaned[:180]
    return ""


def _summarize_text(text: str) -> str:
    return " ".join(text.split())[:600]


def _score_text(title: str, text: str) -> float:
    haystack = f"{title}\n{text}".lower()
    score = 50.0
    for keyword in ("ai", "agent", "architecture", "python", "fastapi", "study", "learning", "research"):
        if keyword in haystack:
            score += 5
    return min(100.0, score)


def _extract_topics(text: str) -> list[str]:
    topics = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_+.-]{2,}", text):
        if token.lower() in {"the", "and", "for", "with", "from", "this", "that"}:
            continue
        topics.append(token[:40])
    return _dedupe(topics)[:12]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        key = normalized.lower()
        if not normalized or key in seen:
            continue
        seen.add(key)
        out.append(normalized)
    return out


def _minutes_from_text(text: str) -> int:
    match = re.search(r"(\d{1,3})", text)
    if match:
        return max(1, min(int(match.group(1)), 240))
    return 30


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    return normalized[:80] or "personal-study-pack"


def _csv_cell(value: str) -> str:
    return '"' + value.replace('"', '""').replace("\n", " ").strip() + '"'


def _minimal_pdf(lines: list[str]) -> bytes:
    safe_lines = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")[:110] for line in lines]
    text_ops = ["BT", "/F1 10 Tf", "50 780 Td"]
    for index, line in enumerate(safe_lines[:90]):
        if index:
            text_ops.append("0 -14 Td")
        text_ops.append(f"({line}) Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", "ignore")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{idx} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)
