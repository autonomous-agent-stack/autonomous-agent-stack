from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from autoresearch.api.dependencies import get_housekeeper_service, get_media_job_service, get_telegram_notifier_service
from autoresearch.core.services.housekeeper import HousekeeperService
from autoresearch.core.services.media_jobs import MediaJobService
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.shared.media_job_contract import MediaJobRead, MediaJobRequest


router = APIRouter(prefix="/api/v1/media/jobs", tags=["media-jobs"])


@router.post("", response_model=MediaJobRead, status_code=status.HTTP_202_ACCEPTED)
def create_media_job(
    payload: MediaJobRequest,
    background_tasks: BackgroundTasks,
    service: MediaJobService = Depends(get_media_job_service),
    housekeeper_service: HousekeeperService = Depends(get_housekeeper_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
) -> MediaJobRead:
    job = service.create(payload)
    background_tasks.add_task(
        _execute_media_job,
        service=service,
        housekeeper_service=housekeeper_service,
        notifier=notifier,
        job_id=job.job_id,
    )
    return job


@router.get("", response_model=list[MediaJobRead])
def list_media_jobs(
    service: MediaJobService = Depends(get_media_job_service),
) -> list[MediaJobRead]:
    return service.list()


@router.get("/{job_id}", response_model=MediaJobRead)
def get_media_job(
    job_id: str,
    service: MediaJobService = Depends(get_media_job_service),
) -> MediaJobRead:
    job = service.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media job not found")
    return job


def _execute_media_job(
    *,
    service: MediaJobService,
    housekeeper_service: HousekeeperService,
    notifier: TelegramNotifierService,
    job_id: str,
) -> None:
    completed = service.execute(job_id)
    housekeeper_service.record_media_job_outcome(
        job=completed,
        notifier=notifier,
        media_jobs=service.list(),
    )
