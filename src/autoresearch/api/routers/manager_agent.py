from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from autoresearch.api.dependencies import get_housekeeper_service, get_manager_agent_service
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.housekeeper import HousekeeperService
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead, ManagerDispatchRequest


router = APIRouter(prefix="/api/v1/agents/manager", tags=["manager-agent"])


@router.post(
    "/dispatch",
    response_model=ManagerDispatchRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def dispatch_manager_agent(
    payload: ManagerDispatchRequest,
    background_tasks: BackgroundTasks,
    service: ManagerAgentService = Depends(get_manager_agent_service),
    housekeeper_service: HousekeeperService = Depends(get_housekeeper_service),
) -> ManagerDispatchRead:
    prepared, _, _ = housekeeper_service.prepare_manager_request(
        payload,
        manager_service=service,
        trigger_source="api",
    )
    dispatch = service.create_dispatch(prepared)
    if prepared.auto_dispatch:
        background_tasks.add_task(service.execute_dispatch, dispatch.dispatch_id)
    return dispatch


@router.get("/dispatches", response_model=list[ManagerDispatchRead])
def list_manager_dispatches(
    service: ManagerAgentService = Depends(get_manager_agent_service),
) -> list[ManagerDispatchRead]:
    return service.list_dispatches()


@router.get("/dispatches/{dispatch_id}", response_model=ManagerDispatchRead)
def get_manager_dispatch(
    dispatch_id: str,
    service: ManagerAgentService = Depends(get_manager_agent_service),
) -> ManagerDispatchRead:
    dispatch = service.get_dispatch(dispatch_id)
    if dispatch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager dispatch not found")
    return dispatch
