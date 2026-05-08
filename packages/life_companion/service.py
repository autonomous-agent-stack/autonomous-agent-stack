from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
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
    PersonalBlockRead,
    PersonalCanvasRead,
    PersonalCanvasUpsertRequest,
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
    PersonalGraphRead,
    PersonalHighlightRead,
    PersonalInterfaceLayoutRead,
    PersonalInterfaceLayoutRequest,
    PersonalInterfacePanelRead,
    PersonalLinkCreateRequest,
    PersonalLinkRead,
    PersonalLinkRelation,
    PersonalMentionPromoteRequest,
    PersonalMentionRead,
    PersonalNodeKind,
    PersonalNodeRead,
    PersonalNoteRead,
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
    highlights: Repository[PersonalHighlightRead]
    notes: Repository[PersonalNoteRead]
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
    nodes: Repository[PersonalNodeRead]
    blocks: Repository[PersonalBlockRead]
    links: Repository[PersonalLinkRead]
    mentions: Repository[PersonalMentionRead]
    canvases: Repository[PersonalCanvasRead]


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
        if self.is_ready():
            self.sync_graph()
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
        graph = self.graph(depth=1, limit=40) if enabled and all(item.enabled for item in deps) else None
        canvas = self.canvas() if graph and graph.nodes else None
        layout = self.interface_layout(PersonalInterfaceLayoutRequest()) if status in {"ok", "degraded"} else None
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
            graph=graph,
            canvas=canvas,
            layout=layout,
            recent_activity=events,
            metadata={
                "content_count": len(self._repos.contents.list()),
                "study_item_count": len(self._visible_study_items()),
                "card_count": len(self._repos.flashcards.list()),
                "export_count": len(exports),
                "node_count": len(self._repos.nodes.list()),
                "link_count": len(self._repos.links.list()),
                "mention_count": len(self._repos.mentions.list()),
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

        self.sync_graph()
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
                metadata={
                    "card_id": card.card_id,
                    "source_context": self._source_context(card.card_id),
                    "attention": "interrupt" if card.review_count == 0 else "normal",
                },
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
            items = [self._attention_adjusted_recommendation(item) for item in row.items[:remaining]]
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
                    "source_context": {
                        "source_app": str(item.get("platform") or "entertainment_curator"),
                        "backlinks": 0,
                        "nodes": [],
                    },
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
        graph = self.sync_graph()
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
                "graph_seed": {
                    "node_count": len(graph.nodes),
                    "link_count": len(graph.links),
                    "mention_count": len(graph.mentions),
                    "root_node_id": plan.plan_id if plan else "",
                },
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
        if self.is_ready():
            self.sync_graph()
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
        nodes = [
            item
            for item in self._repos.nodes.list()
            if normalized in f"{item.title}\n{item.body}\n{' '.join(item.tags)}".lower()
        ][:30]
        return PersonalSearchRead(query=query, items=contents, recommendations=recommendations, cards=cards, nodes=nodes)

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

    def sync_graph(self) -> PersonalGraphRead:
        if not self.is_ready():
            return PersonalGraphRead(status="disabled", metadata=self._disabled_metadata())

        for item in self._visible_study_items():
            self._upsert_node(
                node_id=item.item_id,
                kind=PersonalNodeKind.CONTENT,
                title=item.title,
                body="\n".join(
                    part
                    for part in [item.summary, item.why_it_matters, item.suggested_action]
                    if part
                ),
                source_id=item.item_id,
                source_table="study_dashboard_items",
                source_url=item.source_url,
                tags=_dedupe([item.source_kind.value, item.reading_depth.value, *item.technologies]),
                properties={
                    "score": item.score,
                    "status": item.status.value,
                    "reading_depth": item.reading_depth.value,
                },
                metadata=item.metadata,
            )

        for content in self._repos.contents.list():
            self._upsert_node(
                node_id=content.content_id,
                kind=PersonalNodeKind.CONTENT,
                title=content.title,
                body=content.summary,
                source_id=content.content_id,
                source_table="personal_content_items",
                source_url=content.source_url,
                tags=_dedupe([content.kind.value, content.source_app, *content.tags, *content.topics]),
                properties={"score": content.score, "kind": content.kind.value},
                metadata=content.metadata,
            )
            for ref in content.external_refs.values():
                if ref and self._repos.nodes.get(ref):
                    self._upsert_link(content.content_id, ref, PersonalLinkRelation.DERIVED_FROM, anchor_text=ref)

        for highlight in self._repos.highlights.list():
            title = _title_from_text(highlight.text) or f"Highlight {highlight.highlight_id}"
            self._upsert_node(
                node_id=highlight.highlight_id,
                kind=PersonalNodeKind.CONTENT,
                title=title[:160],
                body="\n".join(part for part in [highlight.text, highlight.note, highlight.location] if part),
                source_id=highlight.highlight_id,
                source_table="personal_highlights",
                tags=_dedupe(["highlight", *_extract_topics(f"{highlight.text}\n{highlight.note}")]),
                properties={"content_id": highlight.content_id, "location": highlight.location},
                metadata=highlight.metadata,
            )
            if highlight.content_id and self._repos.nodes.get(highlight.content_id):
                self._upsert_link(
                    highlight.highlight_id,
                    highlight.content_id,
                    PersonalLinkRelation.DERIVED_FROM,
                    highlight.content_id,
                )

        for note in self._repos.notes.list():
            title = _title_from_text(note.text) or f"Note {note.note_id}"
            self._upsert_node(
                node_id=note.note_id,
                kind=PersonalNodeKind.CONTENT,
                title=title[:160],
                body=note.text,
                source_id=note.note_id,
                source_table="personal_notes",
                tags=_dedupe(["note", note.source_app, *_extract_topics(note.text)]),
                properties={"content_id": note.content_id, "source_app": note.source_app},
                metadata=note.metadata,
            )
            if note.content_id and self._repos.nodes.get(note.content_id):
                self._upsert_link(
                    note.note_id,
                    note.content_id,
                    PersonalLinkRelation.DERIVED_FROM,
                    note.content_id,
                )

        for card in self._repos.flashcards.list():
            body = f"{card.front}\n\n{card.back}"
            self._upsert_node(
                node_id=card.card_id,
                kind=PersonalNodeKind.CARD,
                title=card.front[:140],
                body=body,
                source_id=card.card_id,
                source_table="personal_flashcards",
                tags=_dedupe(["card", *card.tags]),
                properties={
                    "due_at": card.due_at.isoformat(),
                    "review_count": card.review_count,
                    "interval_days": card.interval_days,
                },
                metadata=card.metadata,
            )
            if card.study_item_id:
                self._upsert_link(
                    card.card_id,
                    card.study_item_id,
                    PersonalLinkRelation.DERIVED_FROM,
                    anchor_text=card.study_item_id,
                )
            if card.content_id:
                self._upsert_link(
                    card.card_id,
                    card.content_id,
                    PersonalLinkRelation.DERIVED_FROM,
                    anchor_text=card.content_id,
                )

        for review in self._repos.reviews.list():
            title = f"Review {review.card_id}"
            self._upsert_node(
                node_id=review.review_id,
                kind=PersonalNodeKind.CARD,
                title=title,
                body=f"rating: {review.rating.value if review.rating else 'pending'}",
                source_id=review.review_id,
                source_table="personal_reviews",
                tags=_dedupe(["review", review.rating.value if review.rating else "pending"]),
                properties={
                    "card_id": review.card_id,
                    "rating": review.rating.value if review.rating else "",
                    "next_due_at": review.next_due_at.isoformat() if review.next_due_at else "",
                },
                metadata=review.metadata,
            )
            if review.card_id and self._repos.nodes.get(review.card_id):
                self._upsert_link(
                    review.review_id,
                    review.card_id,
                    PersonalLinkRelation.DERIVED_FROM,
                    review.card_id,
                )

        for plan in self._repos.plans.list():
            body = "\n".join(f"{block.kind}: {block.title}" for block in plan.blocks)
            self._upsert_node(
                node_id=plan.plan_id,
                kind=PersonalNodeKind.PLAN,
                title=plan.title,
                body=body,
                source_id=plan.plan_id,
                source_table="personal_daily_plans",
                tags=["plan", plan.status],
                properties={"plan_date": plan.plan_date, "status": plan.status},
                metadata=plan.metadata,
            )
            for row in plan.recommendation_rows:
                for rec in row.items:
                    self._upsert_link(plan.plan_id, rec.recommendation_id, PersonalLinkRelation.PART_OF, row.title)

        for rec in self._repos.recommendations.list():
            self._upsert_node(
                node_id=rec.recommendation_id,
                kind=PersonalNodeKind.ENTERTAINMENT
                if rec.kind == PersonalRecommendationKind.ENTERTAINMENT
                else PersonalNodeKind.RECOMMENDATION,
                title=rec.title,
                body="\n".join(part for part in [rec.summary, rec.reason] if part),
                source_id=rec.recommendation_id,
                source_table="personal_recommendations",
                source_url=rec.source_url,
                tags=_dedupe([rec.kind.value, rec.source_app, *rec.actions]),
                properties={"score": rec.score, "estimated_minutes": rec.estimated_minutes},
                metadata=rec.metadata,
            )
            for related in rec.related_item_ids:
                if self._repos.nodes.get(related):
                    self._upsert_link(rec.recommendation_id, related, PersonalLinkRelation.REFERENCES, related)

        for export in self._repos.exports.list():
            self._upsert_node(
                node_id=export.export_id,
                kind=PersonalNodeKind.EXPORT,
                title=export.title,
                body="\n".join([*export.artifact_paths, *export.copied_paths]),
                source_id=export.export_id,
                source_table="personal_export_jobs",
                tags=["export", export.target.value, export.status.value],
                properties={"status": export.status.value, "target": export.target.value},
                metadata=export.metadata,
            )
            plan_id = str(export.metadata.get("plan_id") or "").strip()
            if plan_id and self._repos.nodes.get(plan_id):
                self._upsert_link(export.export_id, plan_id, PersonalLinkRelation.SOURCE_OF, plan_id)

        for account in self._repos.source_accounts.list():
            self._upsert_node(
                node_id=account.account_id,
                kind=PersonalNodeKind.SOURCE,
                title=account.display_name or account.provider,
                body=f"{account.provider} {account.auth_status}",
                source_id=account.account_id,
                source_table="personal_source_accounts",
                tags=_dedupe(["source", account.provider, account.auth_status]),
                properties={"enabled": account.enabled, "provider": account.provider},
                metadata=account.metadata,
            )

        for node in list(self._repos.nodes.list()):
            self._index_node_text(node)
        self._refresh_node_counts()
        return self.graph(depth=1, limit=80)

    def list_nodes(self, *, query: str = "", kind: str = "", limit: int = 100) -> list[PersonalNodeRead]:
        self.sync_graph()
        normalized = query.strip().lower()
        kind_value = kind.strip().lower()
        nodes = sorted(self._repos.nodes.list(), key=lambda item: (item.backlink_count, item.updated_at), reverse=True)
        out: list[PersonalNodeRead] = []
        for node in nodes:
            if kind_value and node.kind.value != kind_value:
                continue
            if normalized and normalized not in f"{node.title}\n{node.body}\n{' '.join(node.tags)}".lower():
                continue
            out.append(node)
            if len(out) >= limit:
                break
        return out

    def get_node(self, node_id: str) -> PersonalNodeRead | None:
        self.sync_graph()
        return self._repos.nodes.get(node_id)

    def list_links(self, *, node_id: str = "", relation: str = "", limit: int = 200) -> list[PersonalLinkRead]:
        self.sync_graph()
        relation_value = relation.strip().lower()
        links = sorted(self._repos.links.list(), key=lambda item: item.created_at, reverse=True)
        out: list[PersonalLinkRead] = []
        for link in links:
            if node_id and node_id not in {link.source_node_id, link.target_node_id}:
                continue
            if relation_value and link.relation.value != relation_value:
                continue
            out.append(link)
            if len(out) >= limit:
                break
        return out

    def create_link(self, request: PersonalLinkCreateRequest) -> PersonalLinkRead:
        self.sync_graph()
        source = self._repos.nodes.get(request.source_node_id)
        target = self._repos.nodes.get(request.target_node_id)
        if source is None or target is None:
            raise ValueError("source and target nodes must exist")
        link = self._upsert_link(
            request.source_node_id,
            request.target_node_id,
            request.relation,
            anchor_text=request.anchor_text,
            source_block_id=request.source_block_id,
            metadata=request.metadata,
        )
        self._refresh_node_counts()
        return link

    def delete_link(self, link_id: str) -> bool:
        existing = self._repos.links.get(link_id)
        if existing is None:
            return False
        self._repos.links.delete(link_id)
        self._refresh_node_counts()
        return True

    def backlinks(self, node_id: str, *, limit: int = 100) -> list[PersonalLinkRead]:
        self.sync_graph()
        return [
            link for link in self._repos.links.list()
            if link.target_node_id == node_id
        ][:limit]

    def mentions(self, *, status: str = "pending", limit: int = 100) -> list[PersonalMentionRead]:
        return [
            mention for mention in sorted(self._repos.mentions.list(), key=lambda item: item.updated_at, reverse=True)
            if not status or mention.status == status
        ][:limit]

    def promote_mention(self, request: PersonalMentionPromoteRequest) -> PersonalMentionRead:
        self.sync_graph()
        mention = self._repos.mentions.get(request.mention_id)
        if mention is None:
            raise ValueError("mention not found")
        target_node_id = request.target_node_id or mention.suggested_node_id
        if not target_node_id:
            target_node_id = self._ensure_concept_node(mention.target_text).node_id
        if self._repos.nodes.get(target_node_id) is None:
            raise ValueError("target node not found")
        self._upsert_link(
            mention.source_node_id,
            target_node_id,
            request.relation,
            anchor_text=mention.target_text,
            source_block_id=mention.source_block_id,
            confidence=0.95,
            metadata={"promoted_mention_id": mention.mention_id, **request.metadata},
        )
        updated = mention.model_copy(
            update={
                "status": "promoted",
                "suggested_node_id": target_node_id,
                "updated_at": utc_now(),
                "metadata": {**mention.metadata, **request.metadata},
            }
        )
        self._repos.mentions.save(updated.mention_id, updated)
        self._refresh_node_counts()
        return updated

    def graph(self, *, root_node_id: str = "", depth: int = 1, limit: int = 80) -> PersonalGraphRead:
        if not self.is_ready():
            return PersonalGraphRead(status="disabled", metadata=self._disabled_metadata())
        depth = max(0, min(depth, 4))
        limit = max(1, min(limit, 300))
        all_nodes = {node.node_id: node for node in self._repos.nodes.list()}
        all_links = self._repos.links.list()
        if not all_nodes:
            return PersonalGraphRead(metadata={"node_count": 0, "link_count": 0})
        if root_node_id and root_node_id in all_nodes:
            selected = {root_node_id}
            frontier = {root_node_id}
            selected_links: list[PersonalLinkRead] = []
            for _ in range(depth):
                next_frontier: set[str] = set()
                for link in all_links:
                    touches = link.source_node_id in frontier or link.target_node_id in frontier
                    if not touches:
                        continue
                    selected_links.append(link)
                    next_frontier.add(link.source_node_id)
                    next_frontier.add(link.target_node_id)
                selected.update(next_frontier)
                frontier = next_frontier - selected
                if len(selected) >= limit:
                    break
            nodes = [all_nodes[node_id] for node_id in selected if node_id in all_nodes][:limit]
            node_ids = {node.node_id for node in nodes}
            links = [
                link for link in selected_links
                if link.source_node_id in node_ids and link.target_node_id in node_ids
            ][: limit * 2]
        else:
            nodes = sorted(all_nodes.values(), key=lambda item: (item.backlink_count, item.outgoing_count, item.updated_at), reverse=True)[:limit]
            node_ids = {node.node_id for node in nodes}
            links = [
                link for link in all_links
                if link.source_node_id in node_ids and link.target_node_id in node_ids
            ][: limit * 2]
        return PersonalGraphRead(
            root_node_id=root_node_id,
            nodes=nodes,
            links=links,
            mentions=self.mentions(limit=30),
            depth=depth,
            metadata={
                "node_count": len(all_nodes),
                "link_count": len(all_links),
                "selected_node_count": len(nodes),
                "selected_link_count": len(links),
            },
        )

    def canvas(self, *, canvas_id: str = "default") -> PersonalCanvasRead:
        existing = self._repos.canvases.get(canvas_id)
        if existing is not None:
            return existing
        graph = self.graph(depth=1, limit=36)
        nodes: list[dict[str, Any]] = []
        columns = 4
        for index, node in enumerate(graph.nodes[:36]):
            nodes.append(
                {
                    "id": node.node_id,
                    "type": "default",
                    "position": {"x": (index % columns) * 280, "y": (index // columns) * 180},
                    "data": {
                        "label": node.title,
                        "kind": node.kind.value,
                        "backlinks": node.backlink_count,
                    },
                }
            )
        edges = [
            {
                "id": link.link_id,
                "source": link.source_node_id,
                "target": link.target_node_id,
                "label": link.relation.value,
            }
            for link in graph.links
        ]
        canvas = PersonalCanvasRead(
            canvas_id=canvas_id,
            title="Life Companion Map",
            nodes=nodes,
            edges=edges,
            viewport={"x": 0, "y": 0, "zoom": 0.85},
            metadata={"generated_from": "graph"},
        )
        self._repos.canvases.save(canvas.canvas_id, canvas)
        return canvas

    def upsert_canvas(self, request: PersonalCanvasUpsertRequest) -> PersonalCanvasRead:
        now = utc_now()
        existing = self._repos.canvases.get(request.canvas_id)
        canvas = PersonalCanvasRead(
            canvas_id=request.canvas_id,
            title=request.title,
            nodes=request.nodes,
            edges=request.edges,
            viewport=request.viewport,
            created_at=existing.created_at if existing else now,
            updated_at=now,
            metadata=request.metadata,
        )
        self._repos.canvases.save(canvas.canvas_id, canvas)
        return canvas

    def interface_layout(self, request: PersonalInterfaceLayoutRequest) -> PersonalInterfaceLayoutRead:
        if not self.is_enabled():
            return PersonalInterfaceLayoutRead(status="disabled", metadata=self._disabled_metadata())
        missing = [item.package_id for item in self.dependency_state() if not item.enabled]
        if missing:
            return PersonalInterfaceLayoutRead(
                status="missing_dependency",
                overlooked=missing,
                metadata=self._disabled_metadata(),
            )
        graph = self.sync_graph()
        due_cards = self._due_cards(limit=20)
        latest_plan = sorted(self._repos.plans.list(), key=lambda item: item.updated_at, reverse=True)
        exports = sorted(self._repos.exports.list(), key=lambda item: item.updated_at, reverse=True)
        recommendations = sorted(
            self._repos.recommendations.list(),
            key=lambda item: (item.score, item.created_at),
            reverse=True,
        )
        mentions = self.mentions(limit=20)
        stale_exports = [item for item in exports if item.status in {PersonalExportStatus.AWAITING_IMPORT, PersonalExportStatus.FAILED}]
        orphan_nodes = [
            node for node in graph.nodes
            if node.backlink_count == 0 and node.outgoing_count == 0 and node.kind != PersonalNodeKind.TAG
        ][:12]
        blind_spots = self._knowledge_blind_spots(limit=10)
        hot_clusters = self._hot_clusters(limit=12)
        tracking_topics = self._tracking_topics()
        tracked_hot_clusters = [
            item for item in hot_clusters
            if tracking_topics & {str(topic).strip().lower() for topic in item.get("topics", [])}
        ]
        boredom_items = [
            item for item in recommendations
            if str(item.metadata.get("attention") or "") == "boredom_feed"
        ][:12]
        priorities = request.priorities or {}

        mode = _layout_mode(
            intent=request.intent,
            due_cards=len(due_cards),
            mentions=len(mentions),
            stale_exports=len(stale_exports),
            focus=request.focus,
        )
        panels = [
            PersonalInterfacePanelRead(
                panel_id="today_home",
                title="Today command center",
                view_kind="today_home",
                priority=_priority(88, priorities, "today"),
                reason="Start with the next concrete action across study, review, reward, and export.",
                source_pattern="NotebookLM Studio + Readwise Home",
                recommendation_ids=[item.recommendation_id for item in recommendations[:4]],
                action_ids=["plan", "review", "export", "reward"],
                metadata={"plan_id": latest_plan[0].plan_id if latest_plan else ""},
            ),
            PersonalInterfacePanelRead(
                panel_id="for_you_filtered_view",
                title="For You filtered view",
                view_kind="filtered_view",
                priority=_priority(76, priorities, "for_you"),
                reason="A query-like row view keeps inbox, learning value, and entertainment fit scannable.",
                source_pattern="Readwise Reader filtered views + Netflix rows",
                query=_filtered_view_query(request),
                recommendation_ids=[item.recommendation_id for item in recommendations[:12]],
                action_ids=["feedback", "save", "hide_source", "promote_to_study"],
            ),
            PersonalInterfacePanelRead(
                panel_id="object_dashboard",
                title="Objects that need structure",
                view_kind="object_dashboard",
                priority=_priority(70 + len(orphan_nodes), priorities, "objects"),
                reason="Object dashboards surface concepts, cards, sources, and projects that lack enough context.",
                source_pattern="Capacities object types + Tana supertags",
                node_ids=[node.node_id for node in orphan_nodes],
                action_ids=["add_type", "link", "tag", "make_view"],
                metadata={"orphan_count": len(orphan_nodes)},
            ),
            PersonalInterfacePanelRead(
                panel_id="graph_mentions",
                title="Backlinks and unlinked mentions",
                view_kind="graph",
                priority=_priority(64 + min(len(mentions) * 3, 24), priorities, "graph"),
                reason="Confirmed links and unlinked mentions reveal overlooked relationships before they decay.",
                source_pattern="Obsidian backlinks/graph + RemNote text references",
                node_ids=[mention.source_node_id for mention in mentions[:10]],
                action_ids=["promote_mention", "dismiss_mention", "open_backlinks"],
                metadata={"mention_count": len(mentions), "link_count": len(graph.links)},
            ),
            PersonalInterfacePanelRead(
                panel_id="knowledge_blind_spots",
                title="Knowledge blind spots",
                view_kind="blind_spots",
                priority=_priority(62 + min(len(blind_spots) * 3, 24), priorities, "blind_spots"),
                reason="Avoids a filter bubble by showing topics with weak backlinks, few cards, or no review evidence.",
                source_pattern="NotebookLM gap finding + Anki weak-area review + Capacities object dashboards",
                query="gap_score = low backlinks + missing cards + missing reviews",
                node_ids=[node_id for gap in blind_spots for node_id in gap.get("node_ids", [])[:2]][:12],
                action_ids=["generate_cards", "find_sources", "open_graph", "schedule_deep_study"],
                metadata={"gaps": blind_spots},
            ),
            PersonalInterfacePanelRead(
                panel_id="deduped_hot_feed",
                title="Deduped hot feed",
                view_kind="hot_feed",
                priority=_priority(54 + min(len(hot_clusters) * 2, 24), priorities, "hot"),
                reason="Merges repeated news, projects, and source echoes before they spend your attention.",
                source_pattern="Readwise feed triage + Reddit/Hacker News style hot ranking + YouTube seen feedback",
                query="cluster by title/url/topics; downrank seen unless followed",
                node_ids=[node_id for item in hot_clusters for node_id in item.get("item_ids", [])[:1]][:12],
                action_ids=["mark_seen", "save_tracking", "hide_source", "promote_to_study"],
                metadata={"clusters": hot_clusters},
            ),
            PersonalInterfacePanelRead(
                panel_id="tracking_watchlist",
                title="Tracked topics with signal",
                view_kind="tracking",
                priority=_priority(68 + min(len(tracked_hot_clusters) * 8, 28), priorities, "tracking"),
                reason="Only followed topics get a higher-priority surface, and only when a cluster adds new signal.",
                source_pattern="GitHub watch/subscription inbox + YouTube channel feedback + Netflix continue rows",
                query="saved/more_like_this topics with new deduped clusters",
                node_ids=[node_id for item in tracked_hot_clusters for node_id in item.get("item_ids", [])[:1]][:12],
                action_ids=["open_latest", "summarize_delta", "keep_tracking", "mute_tracking"],
                metadata={"topics": sorted(tracking_topics), "clusters": tracked_hot_clusters},
            ),
            PersonalInterfacePanelRead(
                panel_id="whiteboard_canvas",
                title="Whiteboard synthesis",
                view_kind="canvas",
                priority=_priority(58 + min(len(graph.links), 18), priorities, "canvas"),
                reason="A spatial canvas is better than a list when the current problem is synthesis and structure.",
                source_pattern="Heptabase whiteboard + Obsidian Canvas",
                node_ids=[node.node_id for node in graph.nodes[:18]],
                action_ids=["save_canvas", "open_node", "export_graph_seed"],
            ),
            PersonalInterfacePanelRead(
                panel_id="review_queue",
                title="Active recall queue",
                view_kind="review_queue",
                priority=_priority(50 + min(len(due_cards) * 4, 36), priorities, "review"),
                reason="Due cards should interrupt passive browsing when memory is the bottleneck.",
                source_pattern="Anki FSRS-style spaced repetition + RemNote flashcards",
                node_ids=[card.card_id for card in due_cards[:16]],
                action_ids=["again", "hard", "good", "easy", "generate_cards"],
            ),
            PersonalInterfacePanelRead(
                panel_id="export_backfill",
                title="GoodNotes / MarginNote return loop",
                view_kind="export_status",
                priority=_priority(46 + min(len(stale_exports) * 8, 32), priorities, "export"),
                reason="Exports only become knowledge when annotated files and sidecars come back into the graph.",
                source_pattern="GoodNotes import/auto backup + MarginNote sidecar workflow",
                node_ids=[item.export_id for item in stale_exports[:8]],
                action_ids=["export", "scan_backfill", "retry_failed"],
                metadata={"stale_export_count": len(stale_exports)},
            ),
            PersonalInterfacePanelRead(
                panel_id="boredom_scroll",
                title="Boredom scroll",
                view_kind="boredom_feed",
                priority=_priority(28 if request.focus == "high" else 48, priorities, "boredom"),
                reason="Low-urgency, already-seen, or lightweight items stay available for idle browsing without stealing focus.",
                source_pattern="Readwise daily digest + low-pressure social feed controls",
                recommendation_ids=[item.recommendation_id for item in boredom_items],
                action_ids=["mark_seen", "save", "promote_to_study", "not_interested"],
                metadata={"attention": "low", "interrupt": False},
            ),
            PersonalInterfacePanelRead(
                panel_id="entertainment_dj",
                title="Reward without losing the thread",
                view_kind="entertainment_dj",
                priority=_priority(42 if due_cards else 66, priorities, "reward"),
                reason="Entertainment should match mood and time, then offer one-click promotion into study when useful.",
                source_pattern="Spotify DJ + YouTube/Netflix feedback loops",
                recommendation_ids=[
                    item.recommendation_id
                    for item in recommendations
                    if item.kind == PersonalRecommendationKind.ENTERTAINMENT
                ][:8],
                action_ids=["play_official", "not_interested", "promote_to_study"],
            ),
        ]
        panels = sorted(panels, key=lambda item: item.priority, reverse=True)
        overlooked: list[str] = []
        if mentions:
            overlooked.append(f"{len(mentions)} unlinked mentions need a link/dismiss decision")
        if orphan_nodes:
            overlooked.append(f"{len(orphan_nodes)} objects have no graph context")
        if stale_exports:
            overlooked.append(f"{len(stale_exports)} exports are awaiting import or retry")
        if due_cards:
            overlooked.append(f"{len(due_cards)} review cards are due")
        if blind_spots:
            overlooked.append(f"{len(blind_spots)} knowledge blind spots need source/card coverage")
        if hot_clusters:
            overlooked.append(f"{len(hot_clusters)} deduped hot clusters are waiting in low-pressure feed")
        if tracked_hot_clusters:
            overlooked.append(f"{len(tracked_hot_clusters)} tracked topics have new signal")
        return PersonalInterfaceLayoutRead(
            mode=mode,
            headline=_layout_headline(mode, request.intent),
            intent=request.intent,
            panels=panels[:12],
            overlooked=overlooked if request.include_overlooked else [],
            benchmark_patterns=[
                "Readwise Reader: unified inbox, filtered views, daily digest",
                "NotebookLM: grounded source artifacts and study guide surfaces",
                "Anki/RemNote: active recall and spaced repetition queues",
                "Obsidian/Logseq/RemNote: page refs, block refs, backlinks, portals",
                "Tana/Capacities: typed objects, fields, table/gallery/wall views",
                "Heptabase/Obsidian Canvas: spatial synthesis whiteboards",
                "YouTube/Netflix/Spotify: contextual rows, explicit feedback, DJ explanations",
                "GoodNotes/MarginNote: export, annotate, backfill, graph seed loop",
            ],
            metadata={
                "composer": "life_companion_layout_intelligence",
                "available_minutes": request.available_minutes,
                "mood": request.mood,
                "focus": request.focus,
                "graph_node_count": len(graph.nodes),
                "graph_link_count": len(graph.links),
                "interrupt_policy": "only due reviews, tracked high-signal deltas, failed exports, or explicit user asks",
                "filter_bubble_policy": "always reserve space for blind spots and exploration beyond watched sources",
            },
        )

    def _upsert_node(
        self,
        *,
        node_id: str,
        kind: PersonalNodeKind,
        title: str,
        body: str = "",
        source_id: str = "",
        source_table: str = "",
        source_url: str = "",
        tags: list[str] | None = None,
        aliases: list[str] | None = None,
        properties: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PersonalNodeRead:
        existing = self._repos.nodes.get(node_id)
        node = PersonalNodeRead(
            node_id=node_id,
            kind=kind,
            title=(title or "Untitled").strip()[:220],
            body=body or "",
            source_id=source_id,
            source_table=source_table,
            source_url=source_url,
            tags=_dedupe(tags or []),
            aliases=_dedupe(aliases or []),
            properties=properties or {},
            backlink_count=existing.backlink_count if existing else 0,
            outgoing_count=existing.outgoing_count if existing else 0,
            created_at=existing.created_at if existing else utc_now(),
            updated_at=utc_now(),
            metadata=metadata or {},
        )
        self._repos.nodes.save(node.node_id, node)
        self._upsert_block(node)
        return node

    def _upsert_block(self, node: PersonalNodeRead) -> PersonalBlockRead:
        content = "\n\n".join(part for part in [node.title, node.body] if part).strip()
        block = PersonalBlockRead(
            block_id=f"block_{node.node_id}_main",
            node_id=node.node_id,
            content=content,
            ordinal=0,
            created_at=node.created_at,
            updated_at=node.updated_at,
            metadata={"source_table": node.source_table, "source_id": node.source_id},
        )
        self._repos.blocks.save(block.block_id, block)
        return block

    def _ensure_concept_node(self, title: str, *, kind: PersonalNodeKind = PersonalNodeKind.CONCEPT) -> PersonalNodeRead:
        normalized = _normalize_title(title)
        node_id = f"{kind.value}_{_slugify(normalized)}"
        existing = self._repos.nodes.get(node_id)
        if existing is not None:
            return existing
        return self._upsert_node(
            node_id=node_id,
            kind=kind,
            title=title.strip()[:180] or "Untitled concept",
            body="",
            source_id=node_id,
            source_table="personal_graph",
            tags=[kind.value],
            aliases=[normalized],
            metadata={"auto_created": True},
        )

    def _upsert_link(
        self,
        source_node_id: str,
        target_node_id: str,
        relation: PersonalLinkRelation,
        anchor_text: str = "",
        source_block_id: str = "",
        confidence: float = 1.0,
        metadata: dict[str, Any] | None = None,
    ) -> PersonalLinkRead:
        link_id = _stable_link_id(source_node_id, target_node_id, relation.value, anchor_text, source_block_id)
        existing = self._repos.links.get(link_id)
        link = PersonalLinkRead(
            link_id=link_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relation=relation,
            anchor_text=anchor_text,
            source_block_id=source_block_id,
            confidence=confidence,
            created_at=existing.created_at if existing else utc_now(),
            metadata={**(existing.metadata if existing else {}), **(metadata or {})},
        )
        self._repos.links.save(link.link_id, link)
        return link

    def _index_node_text(self, node: PersonalNodeRead) -> None:
        block = self._repos.blocks.get(f"block_{node.node_id}_main")
        block_id = block.block_id if block else ""
        text = block.content if block else "\n".join([node.title, node.body])

        for title in _extract_wiki_links(text):
            target = self._ensure_concept_node(title)
            self._upsert_link(node.node_id, target.node_id, PersonalLinkRelation.REFERENCES, title, block_id)

        for tag in _extract_hash_tags(text):
            target = self._ensure_concept_node(tag, kind=PersonalNodeKind.TAG)
            self._upsert_link(node.node_id, target.node_id, PersonalLinkRelation.TAGGED_AS, tag, block_id)

        node_index = {_normalize_title(item.title): item for item in self._repos.nodes.list()}
        for target_text in _extract_at_mentions(text):
            target = node_index.get(_normalize_title(target_text))
            if target:
                self._upsert_link(node.node_id, target.node_id, PersonalLinkRelation.MENTIONS, target_text, block_id)
            else:
                self._upsert_mention(node.node_id, block_id, target_text, context=_context_for(text, target_text))

        for target_id in _extract_stable_ids(text):
            if self._repos.nodes.get(target_id):
                self._upsert_link(node.node_id, target_id, PersonalLinkRelation.REFERENCES, target_id, block_id)

        for other in self._repos.nodes.list():
            if other.node_id == node.node_id or len(other.title) < 4:
                continue
            normalized_title = _normalize_title(other.title)
            if normalized_title and normalized_title in _normalize_title(text):
                explicit = any(
                    link.source_node_id == node.node_id and link.target_node_id == other.node_id
                    for link in self._repos.links.list()
                )
                if not explicit:
                    self._upsert_mention(
                        node.node_id,
                        block_id,
                        other.title,
                        suggested_node_id=other.node_id,
                        context=_context_for(text, other.title),
                    )

    def _upsert_mention(
        self,
        source_node_id: str,
        source_block_id: str,
        target_text: str,
        *,
        suggested_node_id: str = "",
        context: str = "",
    ) -> PersonalMentionRead:
        normalized = _normalize_title(target_text)
        mention_id = _stable_mention_id(source_node_id, source_block_id, normalized)
        existing = self._repos.mentions.get(mention_id)
        if existing and existing.status != "pending":
            return existing
        mention = PersonalMentionRead(
            mention_id=mention_id,
            source_node_id=source_node_id,
            source_block_id=source_block_id,
            target_text=target_text[:160],
            normalized_target=normalized,
            suggested_node_id=suggested_node_id,
            status=existing.status if existing else "pending",
            context=context[:500],
            created_at=existing.created_at if existing else utc_now(),
            updated_at=utc_now(),
            metadata=existing.metadata if existing else {},
        )
        self._repos.mentions.save(mention.mention_id, mention)
        return mention

    def _refresh_node_counts(self) -> None:
        links = self._repos.links.list()
        incoming: dict[str, int] = {}
        outgoing: dict[str, int] = {}
        for link in links:
            incoming[link.target_node_id] = incoming.get(link.target_node_id, 0) + 1
            outgoing[link.source_node_id] = outgoing.get(link.source_node_id, 0) + 1
        for node in self._repos.nodes.list():
            next_node = node.model_copy(
                update={
                    "backlink_count": incoming.get(node.node_id, 0),
                    "outgoing_count": outgoing.get(node.node_id, 0),
                    "updated_at": utc_now(),
                }
            )
            self._repos.nodes.save(next_node.node_id, next_node)

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
            metadata={
                "study_item_id": item.item_id,
                "status": item.status.value,
                "reading_depth": item.reading_depth.value,
                "source_context": self._source_context(item.item_id),
            },
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
                metadata={
                    "target": "both",
                    "source_context": self._source_context(latest_plan[0].plan_id) if latest_plan else {},
                },
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

    def _attention_adjusted_recommendation(self, item: PersonalRecommendationRead) -> PersonalRecommendationRead:
        seen = self._seen_targets()
        followed = self._followed_targets()
        related = set(item.related_item_ids) | {item.recommendation_id, item.source_app}
        already_seen = bool(related & seen)
        followed_match = bool(related & followed)
        metadata = dict(item.metadata)
        metadata["seen_before"] = already_seen
        metadata["followed_match"] = followed_match
        if already_seen and not followed_match:
            metadata["attention"] = "boredom_feed"
            return item.model_copy(update={"score": max(1.0, item.score - 24), "metadata": metadata})
        if followed_match:
            metadata["attention"] = "watchlist"
            return item.model_copy(update={"score": min(100.0, item.score + 10), "metadata": metadata})
        metadata.setdefault("attention", "normal")
        return item.model_copy(update={"metadata": metadata})

    def _seen_targets(self) -> set[str]:
        return {
            item.target_id
            for item in self._repos.feedback.list()
            if item.signal in {PersonalFeedbackSignal.DONE, PersonalFeedbackSignal.NOT_INTERESTED}
        }

    def _followed_targets(self) -> set[str]:
        return {
            item.target_id
            for item in self._repos.feedback.list()
            if item.signal in {PersonalFeedbackSignal.SAVED, PersonalFeedbackSignal.MORE_LIKE_THIS}
        }

    def _tracking_topics(self) -> set[str]:
        topics: set[str] = set()
        for item in self._repos.feedback.list():
            if item.signal not in {PersonalFeedbackSignal.SAVED, PersonalFeedbackSignal.MORE_LIKE_THIS}:
                continue
            raw_topics = item.metadata.get("topics")
            if isinstance(raw_topics, list):
                topics.update(str(topic).strip().lower() for topic in raw_topics if str(topic).strip())
            if item.note:
                topics.update(topic.lower() for topic in _extract_topics(item.note))
            if item.target_id:
                topics.add(item.target_id.strip().lower())
        return {topic for topic in topics if topic}

    def _hot_clusters(self, *, limit: int = 8) -> list[dict[str, Any]]:
        candidates: list[PersonalContentItemRead | StudyDashboardItemRead] = [
            *self._repos.contents.list(),
            *self._visible_study_items(),
        ]
        seen = self._seen_targets()
        clusters: dict[str, dict[str, Any]] = {}
        for item in candidates:
            item_id = getattr(item, "content_id", "") or getattr(item, "item_id", "")
            title = getattr(item, "title", "")
            summary = getattr(item, "summary", "")
            source_url = getattr(item, "source_url", "")
            source = getattr(item, "source_app", "") or getattr(item, "source_kind", "")
            source_key = str(source.value if hasattr(source, "value") else source)
            topics = getattr(item, "topics", []) or getattr(item, "technologies", [])
            score = float(getattr(item, "score", 0.0) or 0.0)
            signature = _cluster_signature(title, source_url, topics)
            cluster = clusters.setdefault(
                signature,
                {
                    "cluster_id": signature,
                    "title": title,
                    "summary": summary,
                    "score": 0.0,
                    "source_count": 0,
                    "sources": [],
                    "item_ids": [],
                    "seen": False,
                    "topics": [],
                },
            )
            cluster["score"] = max(float(cluster["score"]), score)
            cluster["source_count"] = int(cluster["source_count"]) + 1
            cluster["seen"] = bool(cluster["seen"]) or item_id in seen
            cluster["item_ids"].append(item_id)
            if source_key and source_key not in cluster["sources"]:
                cluster["sources"].append(source_key)
            for topic in topics:
                normalized = str(topic).strip()
                if normalized and normalized not in cluster["topics"]:
                    cluster["topics"].append(normalized)
        ranked = sorted(
            clusters.values(),
            key=lambda item: (
                int(item["source_count"]),
                float(item["score"]),
                0 if item["seen"] else 1,
            ),
            reverse=True,
        )
        return ranked[:limit]

    def _knowledge_blind_spots(self, *, limit: int = 8) -> list[dict[str, Any]]:
        topic_counts: dict[str, dict[str, Any]] = {}
        for node in self._repos.nodes.list():
            for tag in [node.kind.value, *node.tags, *node.aliases]:
                normalized = str(tag).strip().lower()
                if not normalized or normalized in {"content", "card", "local", "study_item"}:
                    continue
                bucket = topic_counts.setdefault(
                    normalized,
                    {"topic": str(tag), "node_ids": [], "backlinks": 0, "cards": 0, "reviews": 0},
                )
                bucket["node_ids"].append(node.node_id)
                bucket["backlinks"] += node.backlink_count
                if node.kind == PersonalNodeKind.CARD:
                    bucket["cards"] += 1
        reviewed_cards = {review.card_id for review in self._repos.reviews.list()}
        for bucket in topic_counts.values():
            bucket["reviews"] = len([node_id for node_id in bucket["node_ids"] if node_id in reviewed_cards])
            bucket["gap_score"] = max(
                0,
                12 - int(bucket["backlinks"])
            ) + max(0, 3 - int(bucket["cards"])) * 3 + (0 if bucket["reviews"] else 4)
        gaps = sorted(topic_counts.values(), key=lambda item: int(item["gap_score"]), reverse=True)
        return gaps[:limit]

    def _source_context(self, node_id: str) -> dict[str, Any]:
        node = self._repos.nodes.get(node_id)
        backlinks = [
            link for link in self._repos.links.list()
            if link.target_node_id == node_id
        ][:8]
        related_node_ids = _dedupe(
            [
                *(link.source_node_id for link in backlinks),
                *(
                    link.target_node_id
                    for link in self._repos.links.list()
                    if link.source_node_id == node_id
                ),
            ]
        )[:8]
        related_nodes = [
            {"node_id": item.node_id, "title": item.title, "kind": item.kind.value}
            for item in (self._repos.nodes.get(related_id) for related_id in related_node_ids)
            if item is not None
        ]
        return {
            "node_id": node_id,
            "title": node.title if node else "",
            "kind": node.kind.value if node else "",
            "source_url": node.source_url if node else "",
            "backlinks": len(backlinks),
            "related_nodes": related_nodes,
            "backlink_ids": [link.link_id for link in backlinks],
        }

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
        graph = self.graph(root_node_id=plan.plan_id if plan else "", depth=2, limit=48)
        lines = [
            "# MarginNote4 Sidecar",
            "",
            f"- pdf: `{pdf_path}`",
            f"- generated_at: `{utc_now().isoformat()}`",
            f"- graph_nodes: `{len(graph.nodes)}`",
            f"- graph_links: `{len(graph.links)}`",
            "",
            "## Backlinks",
        ]
        if plan is not None:
            lines.append(f"- plan_id: `{plan.plan_id}`")
        for item in self._visible_study_items()[:20]:
            backlinks = [
                link for link in graph.links
                if link.target_node_id == item.item_id or link.source_node_id == item.item_id
            ]
            lines.append(
                f"- `{item.item_id}` -> {item.source_url or item.source_key} "
                f"(backlinks={len(backlinks)})"
            )
        lines.extend(["", "## Source Pins"])
        for node in graph.nodes[:30]:
            if node.source_url:
                lines.append(f"- `{node.node_id}` {node.title}: {node.source_url}")
        lines.extend(["", "## Graph Seed"])
        for link in graph.links[:80]:
            lines.append(
                f"- `{link.source_node_id}` --{link.relation.value}--> `{link.target_node_id}`"
                + (f" anchor={link.anchor_text}" if link.anchor_text else "")
            )
        if graph.mentions:
            lines.extend(["", "## Unlinked Mentions"])
            for mention in graph.mentions[:30]:
                lines.append(f"- `{mention.source_node_id}` mentions `{mention.target_text}`: {mention.context}")
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


def _priority(base: float, overrides: dict[str, float], key: str) -> float:
    override = overrides.get(key)
    if override is None:
        return max(0.0, min(100.0, base))
    return max(0.0, min(100.0, base + float(override)))


def _layout_mode(
    *,
    intent: str,
    due_cards: int,
    mentions: int,
    stale_exports: int,
    focus: str,
) -> str:
    lowered = intent.lower()
    if any(token in lowered for token in ("review", "复习", "卡片")) or due_cards >= 8:
        return "review"
    if any(token in lowered for token in ("export", "goodnotes", "marginnote", "导出")) or stale_exports >= 2:
        return "export"
    if any(token in lowered for token in ("fun", "dj", "reward", "无聊", "娱乐")):
        return "reward"
    if focus == "high" or mentions >= 8:
        return "focus"
    return "explore" if any(token in lowered for token in ("discover", "探索", "热点", "盲区")) else "auto"


def _layout_headline(mode: str, intent: str) -> str:
    if intent.strip():
        return f"Best view for: {intent.strip()[:80]}"
    return {
        "focus": "Focus on the missing links",
        "review": "Memory first",
        "explore": "Explore beyond the bubble",
        "export": "Close the annotation loop",
        "reward": "Lightweight reward mode",
    }.get(mode, "Today, arranged by attention")


def _filtered_view_query(request: PersonalInterfaceLayoutRequest) -> str:
    clauses = [
        f"minutes__lt:{max(10, min(request.available_minutes, 180))}",
        f"focus:{request.focus}",
        "status:(new OR unread OR tracked)",
        "seen:false OR followed:true",
    ]
    if request.intent.strip():
        clauses.append(f'title__contains:"{request.intent.strip()[:80]}" OR tag:"{request.intent.strip()[:40]}"')
    return " AND ".join(clauses)


def _cluster_signature(title: str, source_url: str, topics: list[str]) -> str:
    if source_url:
        normalized_url = re.sub(r"[?#].*$", "", source_url.strip().lower()).rstrip("/")
        if normalized_url:
            return "hot_" + hashlib.sha1(normalized_url.encode("utf-8")).hexdigest()[:12]
    title_tokens = [
        token.lower()
        for token in re.findall(r"[A-Za-z0-9\u4e00-\u9fff]{2,}", title)
        if token.lower() not in {"the", "and", "for", "with", "from"}
    ][:8]
    topic_tokens = [str(topic).strip().lower() for topic in topics[:4] if str(topic).strip()]
    raw = " ".join([*title_tokens, *topic_tokens]) or title or "hot"
    return "hot_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


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


def _extract_wiki_links(text: str) -> list[str]:
    return _dedupe([match.strip() for match in re.findall(r"\[\[([^\]\n]{1,120})\]\]", text)])


def _extract_hash_tags(text: str) -> list[str]:
    return _dedupe(
        [
            match.strip()
            for match in re.findall(r"(?<!\w)#([A-Za-z0-9_\-\u4e00-\u9fff]{2,60})", text)
        ]
    )


def _extract_at_mentions(text: str) -> list[str]:
    return _dedupe(
        [
            match.strip()
            for match in re.findall(r"(?<!\w)@([A-Za-z0-9_\-\u4e00-\u9fff]{2,80})", text)
        ]
    )


def _extract_stable_ids(text: str) -> list[str]:
    return _dedupe(
        re.findall(
            r"\b((?:item|study_item|card|plan|content|export|rec)_[A-Za-z0-9_]{6,40})\b",
            text,
        )
    )


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


def _normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _stable_link_id(source: str, target: str, relation: str, anchor: str, block_id: str) -> str:
    digest = hashlib.sha1(f"{source}|{target}|{relation}|{anchor}|{block_id}".encode("utf-8")).hexdigest()[:16]
    return f"link_{digest}"


def _stable_mention_id(source: str, block_id: str, normalized: str) -> str:
    digest = hashlib.sha1(f"{source}|{block_id}|{normalized}".encode("utf-8")).hexdigest()[:16]
    return f"mention_{digest}"


def _context_for(text: str, needle: str, *, radius: int = 90) -> str:
    lowered = text.lower()
    index = lowered.find(needle.lower())
    if index < 0:
        return " ".join(text.split())[: radius * 2]
    start = max(0, index - radius)
    end = min(len(text), index + len(needle) + radius)
    return " ".join(text[start:end].split())


def _minutes_from_text(text: str) -> int:
    match = re.search(r"(\d{1,3})", text)
    if match:
        return max(1, min(int(match.group(1)), 240))
    return 30


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-")
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    if not normalized:
        return f"node-{digest}"
    return f"{normalized[:68]}-{digest}" if len(normalized) > 68 else normalized


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
