from __future__ import annotations

from fastapi import APIRouter, Depends, status

from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.api.dependencies import (
    get_approval_store_service,
    get_autoresearch_planner_service,
    get_housekeeper_service,
    get_manager_agent_service,
    get_media_job_service,
    get_telegram_notifier_service,
)
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.autoresearch_planner import AutoResearchPlannerService
from autoresearch.core.services.housekeeper import HousekeeperService
from autoresearch.core.services.media_jobs import MediaJobService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.housekeeper_contract import (
    HousekeeperModeUpdateRequest,
    HousekeeperMorningSummaryRead,
    HousekeeperStateRead,
    HousekeeperTickRead,
)


router = APIRouter(prefix="/api/v1/housekeeper", tags=["housekeeper"])


@router.get("/state", response_model=HousekeeperStateRead)
def get_housekeeper_state(
    service: HousekeeperService = Depends(get_housekeeper_service),
) -> HousekeeperStateRead:
    return service.get_state()


@router.post("/mode", response_model=HousekeeperStateRead)
def update_housekeeper_mode(
    payload: HousekeeperModeUpdateRequest,
    service: HousekeeperService = Depends(get_housekeeper_service),
) -> HousekeeperStateRead:
    return service.update_mode(payload)


@router.post("/night-explore/tick", response_model=HousekeeperTickRead, status_code=status.HTTP_200_OK)
def execute_night_explore_tick(
    service: HousekeeperService = Depends(get_housekeeper_service),
    manager_service: ManagerAgentService = Depends(get_manager_agent_service),
    planner_service: AutoResearchPlannerService = Depends(get_autoresearch_planner_service),
    media_service: MediaJobService = Depends(get_media_job_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
) -> HousekeeperTickRead:
    return service.execute_night_explore_tick(
        manager_service=manager_service,
        planner_service=planner_service,
        notifier=notifier,
        media_jobs=media_service.list(),
    )


@router.post("/summaries/morning", response_model=HousekeeperMorningSummaryRead, status_code=status.HTTP_200_OK)
def generate_morning_summary(
    service: HousekeeperService = Depends(get_housekeeper_service),
    manager_service: ManagerAgentService = Depends(get_manager_agent_service),
    planner_service: AutoResearchPlannerService = Depends(get_autoresearch_planner_service),
    approval_service: ApprovalStoreService = Depends(get_approval_store_service),
    media_service: MediaJobService = Depends(get_media_job_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
) -> HousekeeperMorningSummaryRead:
    return service.create_morning_summary(
        manager_service=manager_service,
        planner_service=planner_service,
        approval_service=approval_service,
        notifier=notifier,
        media_jobs=media_service.list(),
    )
