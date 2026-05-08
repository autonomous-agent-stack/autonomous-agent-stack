from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import Field

from autoresearch.shared.models import StrictModel, StudyDashboardItemRead, utc_now


class PersonalContentKind(str, Enum):
    ARTICLE = "article"
    PDF = "pdf"
    NEWSLETTER = "newsletter"
    RSS = "rss"
    VIDEO = "video"
    PODCAST = "podcast"
    NOTE = "note"
    FLASHCARD_DECK = "flashcard_deck"
    ENTERTAINMENT = "entertainment"
    STUDY_ITEM = "study_item"
    LOCAL = "local"


class PersonalRecommendationKind(str, Enum):
    STUDY = "study"
    REVIEW = "review"
    ENTERTAINMENT = "entertainment"
    EXPORT = "export"
    PROMOTE = "promote"
    REWARD = "reward"


class PersonalFeedbackSignal(str, Enum):
    LIKE = "like"
    DISLIKE = "dislike"
    NOT_INTERESTED = "not_interested"
    MORE_LIKE_THIS = "more_like_this"
    HIDE_SOURCE = "hide_source"
    DONE = "done"
    SAVED = "saved"


class PersonalExportTarget(str, Enum):
    GOODNOTES = "goodnotes"
    MARGINNOTE = "marginnote"
    BOTH = "both"


class PersonalExportStatus(str, Enum):
    PREPARED = "prepared"
    COPIED = "copied"
    AWAITING_IMPORT = "awaiting_import"
    IMPORTED = "imported"
    BACKFILLED = "backfilled"
    FAILED = "failed"


class PersonalReviewRating(str, Enum):
    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


class PersonalNodeKind(str, Enum):
    CONTENT = "content"
    CONCEPT = "concept"
    SOURCE = "source"
    TAG = "tag"
    CARD = "card"
    PLAN = "plan"
    RECOMMENDATION = "recommendation"
    EXPORT = "export"
    ENTERTAINMENT = "entertainment"
    CANVAS = "canvas"


class PersonalLinkRelation(str, Enum):
    REFERENCES = "references"
    MENTIONS = "mentions"
    TAGGED_AS = "tagged_as"
    DERIVED_FROM = "derived_from"
    SOURCE_OF = "source_of"
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    PART_OF = "part_of"
    PROMOTES_TO = "promotes_to"


class LifeCompanionDependencyRead(StrictModel):
    package_id: str
    enabled: bool = False


class PersonalContentItemRead(StrictModel):
    content_id: str
    kind: PersonalContentKind = PersonalContentKind.LOCAL
    title: str
    summary: str = ""
    source_url: str = ""
    source_app: str = ""
    tags: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    external_refs: dict[str, str] = Field(default_factory=dict)
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalContentIngestRequest(StrictModel):
    title: str = ""
    text: str = ""
    source_url: str = ""
    source_app: str = ""
    kind: PersonalContentKind = PersonalContentKind.LOCAL
    tags: list[str] = Field(default_factory=list)
    scan_exports: bool = False
    limit: int = Field(default=50, ge=1, le=200)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalContentIngestRead(StrictModel):
    status: Literal["completed", "skipped", "degraded", "disabled"] = "completed"
    items: list[PersonalContentItemRead] = Field(default_factory=list)
    scanned_count: int = 0
    imported_count: int = 0
    skipped_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalHighlightRead(StrictModel):
    highlight_id: str
    content_id: str
    text: str
    note: str = ""
    location: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalNoteRead(StrictModel):
    note_id: str
    content_id: str
    text: str
    source_app: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalSourceAccountRead(StrictModel):
    account_id: str
    provider: str
    display_name: str = ""
    auth_status: Literal["unknown", "auth_required", "authorized", "disabled"] = "unknown"
    scopes: list[str] = Field(default_factory=list)
    enabled: bool = True
    last_sync_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalPreferenceProfileRead(StrictModel):
    profile_id: str
    display_name: str = "Default"
    mood_weights: dict[str, float] = Field(default_factory=dict)
    topic_affinities: dict[str, float] = Field(default_factory=dict)
    source_weights: dict[str, float] = Field(default_factory=dict)
    hidden_sources: list[str] = Field(default_factory=list)
    recent_context: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalFlashcardRead(StrictModel):
    card_id: str
    content_id: str = ""
    study_item_id: str = ""
    front: str
    back: str
    tags: list[str] = Field(default_factory=list)
    due_at: datetime = Field(default_factory=utc_now)
    interval_days: int = Field(default=1, ge=0)
    ease: float = Field(default=2.5, ge=1.0, le=4.0)
    review_count: int = 0
    external_refs: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalReviewRequest(StrictModel):
    card_id: str = ""
    rating: PersonalReviewRating | None = None
    limit: int = Field(default=20, ge=1, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalReviewRead(StrictModel):
    review_id: str
    card_id: str
    rating: PersonalReviewRating | None = None
    next_due_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalRecommendationRead(StrictModel):
    recommendation_id: str
    kind: PersonalRecommendationKind
    title: str
    summary: str = ""
    reason: str = ""
    source_url: str = ""
    source_app: str = ""
    score: float = Field(default=0.0, ge=0.0, le=100.0)
    estimated_minutes: int = Field(default=10, ge=1, le=240)
    actions: list[str] = Field(default_factory=list)
    related_item_ids: list[str] = Field(default_factory=list)
    legal_boundary: str = (
        "Use official, public, user-owned, or normal paid-account access only."
    )
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalRecommendationRowRead(StrictModel):
    row_id: str
    title: str
    reason: str = ""
    items: list[PersonalRecommendationRead] = Field(default_factory=list)


class PersonalRecommendationRequest(StrictModel):
    mood: str = "mixed"
    focus: Literal["low", "medium", "high"] = "medium"
    company: Literal["solo", "friends", "boss", "family"] = "solo"
    available_minutes: int = Field(default=60, ge=5, le=480)
    request_text: str = ""
    include_entertainment: bool = True
    include_study: bool = True
    include_review: bool = True
    limit: int = Field(default=24, ge=1, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalRecommendationResponse(StrictModel):
    status: Literal["completed", "degraded", "disabled"] = "completed"
    rows: list[PersonalRecommendationRowRead] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalDailyPlanBlockRead(StrictModel):
    block_id: str
    kind: Literal["study", "review", "entertainment", "reward", "export", "reflect"]
    title: str
    minutes: int = Field(default=25, ge=1, le=240)
    recommendation_ids: list[str] = Field(default_factory=list)
    status: Literal["planned", "done", "skipped"] = "planned"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalDailyPlanRequest(StrictModel):
    plan_date: str = ""
    mood: str = "mixed"
    focus: Literal["low", "medium", "high"] = "medium"
    available_minutes: int = Field(default=90, ge=15, le=720)
    auto_export: bool = True
    requested_by: str = "local-user"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalDailyPlanRead(StrictModel):
    plan_id: str
    plan_date: str
    title: str
    status: Literal["planned", "active", "completed", "disabled"] = "planned"
    blocks: list[PersonalDailyPlanBlockRead] = Field(default_factory=list)
    recommendation_rows: list[PersonalRecommendationRowRead] = Field(default_factory=list)
    export_job_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalEntertainmentSessionRequest(StrictModel):
    request_text: str = ""
    mood: str = "mixed"
    focus: Literal["low", "medium", "high"] = "medium"
    company: Literal["solo", "friends", "boss", "family"] = "solo"
    available_minutes: int = Field(default=45, ge=5, le=240)
    requested_by: str = "local-user"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalEntertainmentSessionRead(StrictModel):
    status: Literal["completed", "disabled", "degraded"] = "completed"
    recommendations: list[PersonalRecommendationRead] = Field(default_factory=list)
    answer: str = ""
    selected_profile: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalExportRequest(StrictModel):
    target: PersonalExportTarget = PersonalExportTarget.BOTH
    plan_id: str = ""
    title: str = ""
    include_cards: bool = True
    include_marginnote_sidecar: bool = True
    requested_by: str = "local-user"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalExportJobRead(StrictModel):
    export_id: str
    target: PersonalExportTarget
    status: PersonalExportStatus = PersonalExportStatus.PREPARED
    title: str
    artifact_paths: list[str] = Field(default_factory=list)
    copied_paths: list[str] = Field(default_factory=list)
    backfilled_paths: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalFeedbackRequest(StrictModel):
    target_id: str
    signal: PersonalFeedbackSignal
    note: str = ""
    source: str = "api"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalFeedbackRead(StrictModel):
    feedback_id: str
    target_id: str
    signal: PersonalFeedbackSignal
    note: str = ""
    source: str = "api"
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalPromoteRequest(StrictModel):
    recommendation_id: str = ""
    title: str = ""
    summary: str = ""
    source_url: str = ""
    requested_by: str = "local-user"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalPromoteRead(StrictModel):
    status: Literal["completed", "disabled", "degraded"] = "completed"
    content: PersonalContentItemRead | None = None
    study_item: StudyDashboardItemRead | None = None
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalActivityEventRead(StrictModel):
    event_id: str
    event_type: str
    target_id: str = ""
    source: str = "api"
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalActivityEventRequest(StrictModel):
    event_type: str
    target_id: str = ""
    source: str = "api"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalNodeRead(StrictModel):
    node_id: str
    kind: PersonalNodeKind
    title: str
    body: str = ""
    source_id: str = ""
    source_table: str = ""
    source_url: str = ""
    tags: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)
    backlink_count: int = 0
    outgoing_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalBlockRead(StrictModel):
    block_id: str
    node_id: str
    content: str
    ordinal: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalLinkCreateRequest(StrictModel):
    source_node_id: str
    target_node_id: str
    relation: PersonalLinkRelation = PersonalLinkRelation.REFERENCES
    anchor_text: str = ""
    source_block_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalLinkRead(StrictModel):
    link_id: str
    source_node_id: str
    target_node_id: str
    relation: PersonalLinkRelation = PersonalLinkRelation.REFERENCES
    anchor_text: str = ""
    source_block_id: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalMentionRead(StrictModel):
    mention_id: str
    source_node_id: str
    source_block_id: str = ""
    target_text: str
    normalized_target: str
    suggested_node_id: str = ""
    status: Literal["pending", "promoted", "dismissed"] = "pending"
    context: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalMentionPromoteRequest(StrictModel):
    mention_id: str
    target_node_id: str = ""
    relation: PersonalLinkRelation = PersonalLinkRelation.MENTIONS
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalGraphRead(StrictModel):
    status: Literal["ok", "disabled", "missing_dependency"] = "ok"
    root_node_id: str = ""
    nodes: list[PersonalNodeRead] = Field(default_factory=list)
    links: list[PersonalLinkRead] = Field(default_factory=list)
    mentions: list[PersonalMentionRead] = Field(default_factory=list)
    depth: int = 1
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalCanvasRead(StrictModel):
    canvas_id: str
    title: str
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    viewport: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalCanvasUpsertRequest(StrictModel):
    canvas_id: str = "default"
    title: str = "Life Companion Map"
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    viewport: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalInterfacePanelRead(StrictModel):
    panel_id: str
    title: str
    view_kind: Literal[
        "today_home",
        "filtered_view",
        "object_dashboard",
        "graph",
        "canvas",
        "portal",
        "review_queue",
        "entertainment_dj",
        "export_status",
        "blind_spots",
        "hot_feed",
        "tracking",
        "boredom_feed",
        "timeline",
    ]
    priority: float = Field(default=50.0, ge=0.0, le=100.0)
    reason: str = ""
    source_pattern: str = ""
    query: str = ""
    node_ids: list[str] = Field(default_factory=list)
    recommendation_ids: list[str] = Field(default_factory=list)
    action_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalInterfaceLayoutRequest(StrictModel):
    intent: str = ""
    mood: str = "mixed"
    focus: Literal["low", "medium", "high"] = "medium"
    available_minutes: int = Field(default=90, ge=5, le=720)
    priorities: dict[str, float] = Field(default_factory=dict)
    include_overlooked: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalInterfaceLayoutRead(StrictModel):
    status: Literal["ok", "disabled", "missing_dependency"] = "ok"
    mode: Literal["auto", "focus", "review", "explore", "export", "reward"] = "auto"
    headline: str = "Life Companion"
    intent: str = ""
    panels: list[PersonalInterfacePanelRead] = Field(default_factory=list)
    overlooked: list[str] = Field(default_factory=list)
    benchmark_patterns: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalAccessMagicLinkRequest(StrictModel):
    telegram_uid: str = "local-user"
    ttl_seconds: int | None = Field(default=None, ge=30, le=86400)


class PersonalAccessRead(StrictModel):
    status: Literal["created", "verified", "disabled", "failed"]
    enabled: bool = False
    url: str = ""
    expires_at: datetime | None = None
    telegram_uid: str = ""
    reason: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalSearchRead(StrictModel):
    query: str
    items: list[PersonalContentItemRead] = Field(default_factory=list)
    recommendations: list[PersonalRecommendationRead] = Field(default_factory=list)
    cards: list[PersonalFlashcardRead] = Field(default_factory=list)
    nodes: list[PersonalNodeRead] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)


class LifeCompanionStateRead(StrictModel):
    status: Literal["ok", "degraded", "disabled", "missing_dependency"]
    package_id: str = "personal.life_companion"
    enabled: bool = False
    dependencies: list[LifeCompanionDependencyRead] = Field(default_factory=list)
    rows: list[PersonalRecommendationRowRead] = Field(default_factory=list)
    active_plan: PersonalDailyPlanRead | None = None
    due_cards: list[PersonalFlashcardRead] = Field(default_factory=list)
    exports: list[PersonalExportJobRead] = Field(default_factory=list)
    source_accounts: list[PersonalSourceAccountRead] = Field(default_factory=list)
    preference_profile: PersonalPreferenceProfileRead | None = None
    graph: PersonalGraphRead | None = None
    canvas: PersonalCanvasRead | None = None
    layout: PersonalInterfaceLayoutRead | None = None
    access: PersonalAccessRead | None = None
    recent_activity: list[PersonalActivityEventRead] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)
