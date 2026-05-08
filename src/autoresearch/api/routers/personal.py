from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from autoresearch.api.dependencies import get_life_companion_service
from packages.life_companion import (
    LifeCompanionService,
    LifeCompanionStateRead,
    PersonalActivityEventRead,
    PersonalActivityEventRequest,
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
    PersonalPromoteRead,
    PersonalPromoteRequest,
    PersonalRecommendationRequest,
    PersonalRecommendationResponse,
    PersonalReviewRequest,
    PersonalReviewRead,
    PersonalSearchRead,
)


router = APIRouter(prefix="/api/v1/personal", tags=["personal"])


@router.get("/state", response_model=LifeCompanionStateRead, status_code=status.HTTP_200_OK)
def get_personal_state(
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> LifeCompanionStateRead:
    return service.state()


@router.post("/ingest", response_model=PersonalContentIngestRead, status_code=status.HTTP_200_OK)
def ingest_personal_content(
    payload: PersonalContentIngestRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalContentIngestRead:
    return service.ingest(payload)


@router.post("/recommendations", response_model=PersonalRecommendationResponse, status_code=status.HTTP_200_OK)
def create_personal_recommendations(
    payload: PersonalRecommendationRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalRecommendationResponse:
    return service.recommendations(payload)


@router.post("/plans/daily", response_model=PersonalDailyPlanRead, status_code=status.HTTP_201_CREATED)
def create_daily_personal_plan(
    payload: PersonalDailyPlanRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalDailyPlanRead:
    return service.daily_plan(payload)


@router.post("/reviews", response_model=PersonalReviewRead | list[PersonalFlashcardRead], status_code=status.HTTP_200_OK)
def review_personal_card(
    payload: PersonalReviewRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalReviewRead | list[PersonalFlashcardRead]:
    return service.review(payload)


@router.post("/cards", response_model=list[PersonalFlashcardRead], status_code=status.HTTP_201_CREATED)
def create_personal_cards(
    payload: PersonalReviewRequest | None = None,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> list[PersonalFlashcardRead]:
    return service.create_cards(payload)


@router.post("/entertainment/session", response_model=PersonalEntertainmentSessionRead, status_code=status.HTTP_200_OK)
def create_entertainment_session(
    payload: PersonalEntertainmentSessionRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalEntertainmentSessionRead:
    return service.entertainment_session(payload)


@router.post("/exports", response_model=PersonalExportJobRead, status_code=status.HTTP_201_CREATED)
def create_personal_export(
    payload: PersonalExportRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalExportJobRead:
    return service.export(payload)


@router.post("/feedback", response_model=PersonalFeedbackRead, status_code=status.HTTP_201_CREATED)
def create_personal_feedback(
    payload: PersonalFeedbackRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalFeedbackRead:
    return service.feedback(payload)


@router.post("/promote", response_model=PersonalPromoteRead, status_code=status.HTTP_201_CREATED)
def promote_personal_recommendation(
    payload: PersonalPromoteRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalPromoteRead:
    return service.promote(payload)


@router.get("/search", response_model=PersonalSearchRead, status_code=status.HTTP_200_OK)
def search_personal_content(
    q: str = Query(default=""),
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalSearchRead:
    return service.search(q)


@router.post("/events", response_model=PersonalActivityEventRead, status_code=status.HTTP_201_CREATED)
def record_personal_event(
    payload: PersonalActivityEventRequest,
    service: LifeCompanionService = Depends(get_life_companion_service),
) -> PersonalActivityEventRead:
    return service.record_event(payload)
