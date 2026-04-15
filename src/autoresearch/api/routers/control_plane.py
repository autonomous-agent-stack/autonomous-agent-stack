from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from autoresearch.api.dependencies import (
    get_agent_package_registry_service,
    get_control_plane_service,
    get_worker_registry_service,
)
from autoresearch.core.services.agent_package_registry import AgentPackageRegistryService
from autoresearch.core.services.control_plane_service import ControlPlaneService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.housekeeper_contract import (
    AgentPackageRecordRead,
    ControlPlaneTaskRead,
    WorkerRegistrationRead,
)

router = APIRouter(prefix="/api/v1/control-plane", tags=["control-plane"])


@router.get("/packages", response_model=list[AgentPackageRecordRead])
def list_control_plane_packages(
    service: AgentPackageRegistryService = Depends(get_agent_package_registry_service),
) -> list[AgentPackageRecordRead]:
    return service.list_packages()


@router.get("/packages/{package_id}", response_model=AgentPackageRecordRead)
def get_control_plane_package(
    package_id: str,
    service: AgentPackageRegistryService = Depends(get_agent_package_registry_service),
) -> AgentPackageRecordRead:
    item = service.get_package(package_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="package not found")
    return item


@router.get("/workers", response_model=list[WorkerRegistrationRead])
def list_control_plane_workers(
    service: WorkerRegistryService = Depends(get_worker_registry_service),
) -> list[WorkerRegistrationRead]:
    return service.list_workers()


@router.get("/workers/{worker_id}", response_model=WorkerRegistrationRead)
def get_control_plane_worker(
    worker_id: str,
    service: WorkerRegistryService = Depends(get_worker_registry_service),
) -> WorkerRegistrationRead:
    item = service.get_worker(worker_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="worker not found")
    return item


@router.get("/tasks", response_model=list[ControlPlaneTaskRead])
def list_control_plane_tasks(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    service: ControlPlaneService = Depends(get_control_plane_service),
) -> list[ControlPlaneTaskRead]:
    return service.list_tasks(session_id=session_id, limit=limit)


@router.get("/tasks/{task_id}", response_model=ControlPlaneTaskRead)
def get_control_plane_task(
    task_id: str,
    service: ControlPlaneService = Depends(get_control_plane_service),
) -> ControlPlaneTaskRead:
    item = service.get_task(task_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="task not found")
    return item
