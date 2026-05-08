from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status

from autoresearch.api.dependencies import get_life_companion_service, get_panel_access_service
from autoresearch.api.settings import get_feature_settings
from autoresearch.core.services.panel_access import PanelAccessService
from packages.life_companion import (
    LifeCompanionService,
    LifeCompanionStateRead,
    PersonalAccessMagicLinkRequest,
    PersonalAccessRead,
    PersonalActivityEventRead,
    PersonalActivityEventRequest,
    PersonalCanvasRead,
    PersonalCanvasUpsertRequest,
    PersonalContentIngestRead,
    PersonalContentIngestRequest,
    PersonalDailyPlanRead,
    PersonalDailyPlanRequest,
    PersonalEntertainmentSessionRead,
    PersonalEntertainmentSessionRequest,
    PersonalExportJobRead,
    PersonalExportRequest,
    PersonalFeedbackRead,
    PersonalFeedbackRequest,
    PersonalFlashcardRead,
    PersonalGraphRead,
    PersonalInterfaceLayoutRead,
    PersonalInterfaceLayoutRequest,
    PersonalLinkCreateRequest,
    PersonalLinkRead,
    PersonalMentionPromoteRequest,
    PersonalMentionRead,
    PersonalNodeRead,
    PersonalPromoteRead,
    PersonalPromoteRequest,
    PersonalRecommendationRequest,
    PersonalRecommendationResponse,
    PersonalReviewRequest,
    PersonalReviewRead,
    PersonalSearchRead,
)


router = APIRouter(prefix="/api/v1/personal", tags=["personal"])


def _personal_remote_enabled() -> bool:
    return bool(get_feature_settings().personal_remote_enabled)


def _extract_token(request: Request, authorization: str = "") -> str:
    raw_auth = authorization.strip()
    if raw_auth.lower().startswith("bearer "):
        return raw_auth.split(" ", 1)[1].strip()
    return (request.query_params.get("token") or "").strip()


def _require_personal_remote_access(request: Request, authorization: str = "") -> None:
    if not _personal_remote_enabled():
        return
    token = _extract_token(request, authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="personal remote token required")
    try:
        get_panel_access_service().verify_token(token)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def _personal_remote_dependency(
    request: Request,
    authorization: str = Header(default=""),
) -> None:
    _require_personal_remote_access(request, authorization)


protected_router = APIRouter(dependencies=[Depends(_personal_remote_dependency)])


def _build_personal_magic_url(token: str) -> str:
    base = get_feature_settings().personal_remote_base_url.strip() or "http://127.0.0.1:3000/study"
    parsed = urlparse(base)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["token"] = token
    return urlunparse(parsed._replace(query=urlencode(query)))


@router.post("/access/magic-link", response_model=PersonalAccessRead, status_code=status.HTTP_201_CREATED)
def create_personal_magic_link(
    payload: PersonalAccessMagicLinkRequest,
    panel_access: PanelAccessService = Depends(get_panel_access_service),
) -> PersonalAccessRead:
    if not _personal_remote_enabled():
        return PersonalAccessRead(status="disabled", enabled=False, reason="personal remote access is disabled")
    try:
        magic = panel_access.create_magic_link(payload.telegram_uid, ttl_seconds=payload.ttl_seconds)
    except (RuntimeError, PermissionError, ValueError) as exc:
        return PersonalAccessRead(status="failed", enabled=True, reason=str(exc))
    token = dict(parse_qsl(urlparse(magic.url).query)).get("token", "")
    return PersonalAccessRead(
        status="created",
        enabled=True,
        url=_build_personal_magic_url(token),
        expires_at=magic.expires_at,
        telegram_uid=magic.telegram_uid,
    )


@router.get("/access/verify", response_model=PersonalAccessRead, status_code=status.HTTP_200_OK)
def verify_personal_access(
    request: Request,
    authorization: str = Header(default=""),
    panel_access: PanelAccessService = Depends(get_panel_access_service),
) -> PersonalAccessRead:
    if not _personal_remote_enabled():
        return PersonalAccessRead(status="disabled", enabled=False, reason="personal remote access is disabled")
    token = _extract_token(request, authorization)
    if not token:
        return PersonalAccessRead(status="failed", enabled=True, reason="personal remote token required")
    try:
        claims = panel_access.verify_token(token)
    except (PermissionError, ValueError) as exc:
        return PersonalAccessRead(status="failed", enabled=True, reason=str(exc))
    return PersonalAccessRead(
        status="verified",
        enabled=True,
        expires_at=claims.expires_at,
        telegram_uid=claims.telegram_uid,
        metadata={"token_id": claims.token_id or ""},
    )


@protected_router.get("/state", response_model=LifeCompanionStateRead, status_code=status.HTTP_200_OK)
def get_personal_state(
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> LifeCompanionStateRead:
    return service.state()


@protected_router.post("/ingest", response_model=PersonalContentIngestRead, status_code=status.HTTP_200_OK)
def ingest_personal_content(
    payload: PersonalContentIngestRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalContentIngestRead:
    return service.ingest(payload)


@protected_router.post("/recommendations", response_model=PersonalRecommendationResponse, status_code=status.HTTP_200_OK)
def create_personal_recommendations(
    payload: PersonalRecommendationRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalRecommendationResponse:
    return service.recommendations(payload)


@protected_router.post("/plans/daily", response_model=PersonalDailyPlanRead, status_code=status.HTTP_201_CREATED)
def create_daily_personal_plan(
    payload: PersonalDailyPlanRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalDailyPlanRead:
    return service.daily_plan(payload)


@protected_router.post("/reviews", response_model=PersonalReviewRead | list[PersonalFlashcardRead], status_code=status.HTTP_200_OK)
def review_personal_card(
    payload: PersonalReviewRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalReviewRead | list[PersonalFlashcardRead]:
    return service.review(payload)


@protected_router.post("/cards", response_model=list[PersonalFlashcardRead], status_code=status.HTTP_201_CREATED)
def create_personal_cards(
    payload: PersonalReviewRequest | None = None,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> list[PersonalFlashcardRead]:
    return service.create_cards(payload)


@protected_router.post("/entertainment/session", response_model=PersonalEntertainmentSessionRead, status_code=status.HTTP_200_OK)
def create_entertainment_session(
    payload: PersonalEntertainmentSessionRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalEntertainmentSessionRead:
    return service.entertainment_session(payload)


@protected_router.post("/exports", response_model=PersonalExportJobRead, status_code=status.HTTP_201_CREATED)
def create_personal_export(
    payload: PersonalExportRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalExportJobRead:
    return service.export(payload)


@protected_router.post("/feedback", response_model=PersonalFeedbackRead, status_code=status.HTTP_201_CREATED)
def create_personal_feedback(
    payload: PersonalFeedbackRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalFeedbackRead:
    return service.feedback(payload)


@protected_router.post("/promote", response_model=PersonalPromoteRead, status_code=status.HTTP_201_CREATED)
def promote_personal_recommendation(
    payload: PersonalPromoteRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalPromoteRead:
    return service.promote(payload)


@protected_router.get("/search", response_model=PersonalSearchRead, status_code=status.HTTP_200_OK)
def search_personal_content(
    q: str = Query(default=""),
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalSearchRead:
    return service.search(q)


@protected_router.post("/events", response_model=PersonalActivityEventRead, status_code=status.HTTP_201_CREATED)
def record_personal_event(
    payload: PersonalActivityEventRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalActivityEventRead:
    return service.record_event(payload)


@protected_router.get("/nodes", response_model=list[PersonalNodeRead], status_code=status.HTTP_200_OK)
def list_personal_nodes(
    q: str = Query(default=""),
    kind: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=300),
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> list[PersonalNodeRead]:
    return service.list_nodes(query=q, kind=kind, limit=limit)


@protected_router.get("/nodes/{node_id}", response_model=PersonalNodeRead, status_code=status.HTTP_200_OK)
def get_personal_node(
    node_id: str,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalNodeRead:
    node = service.get_node(node_id)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="node not found")
    return node


@protected_router.get("/links", response_model=list[PersonalLinkRead], status_code=status.HTTP_200_OK)
def list_personal_links(
    node_id: str = Query(default=""),
    relation: str = Query(default=""),
    limit: int = Query(default=200, ge=1, le=500),
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> list[PersonalLinkRead]:
    return service.list_links(node_id=node_id, relation=relation, limit=limit)


@protected_router.post("/links", response_model=PersonalLinkRead, status_code=status.HTTP_201_CREATED)
def create_personal_link(
    payload: PersonalLinkCreateRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalLinkRead:
    try:
        return service.create_link(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@protected_router.delete("/links/{link_id}", status_code=status.HTTP_200_OK)
def delete_personal_link(
    link_id: str,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> dict[str, Any]:
    return {"deleted": service.delete_link(link_id), "link_id": link_id}


@protected_router.get("/nodes/{node_id}/backlinks", response_model=list[PersonalLinkRead], status_code=status.HTTP_200_OK)
def get_personal_backlinks(
    node_id: str,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> list[PersonalLinkRead]:
    return service.backlinks(node_id)


@protected_router.get("/mentions", response_model=list[PersonalMentionRead], status_code=status.HTTP_200_OK)
def list_personal_mentions(
    mention_status: str = Query(default="pending", alias="status"),
    limit: int = Query(default=100, ge=1, le=300),
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> list[PersonalMentionRead]:
    service.sync_graph()
    return service.mentions(status=mention_status, limit=limit)


@protected_router.post("/mentions/{mention_id}/promote", response_model=PersonalMentionRead, status_code=status.HTTP_200_OK)
def promote_personal_mention(
    mention_id: str,
    payload: PersonalMentionPromoteRequest | None = None,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalMentionRead:
    request = payload or PersonalMentionPromoteRequest(mention_id=mention_id)
    request = request.model_copy(update={"mention_id": mention_id})
    try:
        return service.promote_mention(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@protected_router.get("/graph", response_model=PersonalGraphRead, status_code=status.HTTP_200_OK)
def get_personal_graph(
    root_node_id: str = Query(default=""),
    depth: int = Query(default=1, ge=0, le=4),
    limit: int = Query(default=80, ge=1, le=300),
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalGraphRead:
    service.sync_graph()
    return service.graph(root_node_id=root_node_id, depth=depth, limit=limit)


@protected_router.get("/canvas", response_model=PersonalCanvasRead, status_code=status.HTTP_200_OK)
def get_personal_canvas(
    canvas_id: str = Query(default="default"),
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalCanvasRead:
    service.sync_graph()
    return service.canvas(canvas_id=canvas_id)


@protected_router.post("/layout", response_model=PersonalInterfaceLayoutRead, status_code=status.HTTP_200_OK)
def compose_personal_layout(
    payload: PersonalInterfaceLayoutRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalInterfaceLayoutRead:
    return service.interface_layout(payload)


@protected_router.post("/canvas", response_model=PersonalCanvasRead, status_code=status.HTTP_200_OK)
def upsert_personal_canvas(
    payload: PersonalCanvasUpsertRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalCanvasRead:
    return service.upsert_canvas(payload)


router.include_router(protected_router)
