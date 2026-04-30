from __future__ import annotations

from fastapi import APIRouter, Depends

from autoresearch.api.dependencies import (
    get_butler_dispatch_center,
    get_github_assistant_service,
    get_runtime_adapter_registry_service,
    get_telegram_notifier_service,
    get_worker_inventory_service,
    get_worker_scheduler_service,
    get_youtube_agent_service,
)
from autoresearch.core.services.butler_dispatch import ButlerDoctorCheck, ButlerDoctorRead, ButlerDispatchCenter
from autoresearch.core.services.runtime_adapter_registry import RuntimeAdapterServiceRegistry
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_inventory import WorkerInventoryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.github_assistant.service import GitHubAssistantService


router = APIRouter(prefix="/api/v1/butler", tags=["butler"])


@router.get("/doctor", response_model=ButlerDoctorRead)
def butler_doctor(
    dispatch_center: ButlerDispatchCenter = Depends(get_butler_dispatch_center),
    runtime_registry: RuntimeAdapterServiceRegistry = Depends(get_runtime_adapter_registry_service),
    worker_inventory: WorkerInventoryService = Depends(get_worker_inventory_service),
    worker_scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
    youtube_service: YouTubeAgentService = Depends(get_youtube_agent_service),
    github_service: GitHubAssistantService = Depends(get_github_assistant_service),
) -> ButlerDoctorRead:
    checks: list[ButlerDoctorCheck] = []
    checks.extend(dispatch_center.doctor_checks())
    checks.append(_check_hermes(runtime_registry))
    checks.append(_check_worker_queue(worker_scheduler=worker_scheduler, worker_inventory=worker_inventory))
    checks.append(
        ButlerDoctorCheck(
            name="telegram notifier",
            status="ok" if notifier.enabled else "degraded",
            detail="Telegram notifier is configured" if notifier.enabled else "Telegram notifier has no bot token",
        )
    )
    checks.append(_check_youtube_autoflow(youtube_service))
    checks.append(_check_github_publish(github_service))
    return ButlerDoctorRead(status=_rollup_status(checks), checks=checks)


def _check_hermes(runtime_registry: RuntimeAdapterServiceRegistry) -> ButlerDoctorCheck:
    try:
        runtime_registry.get("hermes")
    except Exception as exc:
        return ButlerDoctorCheck(
            name="Hermes runtime",
            status="fail",
            detail=str(exc).strip() or exc.__class__.__name__,
        )
    return ButlerDoctorCheck(name="Hermes runtime", status="ok", detail="Hermes runtime adapter is wired")


def _check_worker_queue(
    *,
    worker_scheduler: WorkerSchedulerService,
    worker_inventory: WorkerInventoryService,
) -> ButlerDoctorCheck:
    try:
        queue_depth = len(worker_scheduler.list_queue())
        inventory = worker_inventory.list_workers()
    except Exception as exc:
        return ButlerDoctorCheck(
            name="worker queue",
            status="fail",
            detail=str(exc).strip() or exc.__class__.__name__,
        )
    active_workers = inventory.summary.online_workers + inventory.summary.busy_workers
    status = "ok" if active_workers > 0 else "degraded"
    detail = "worker queue is reachable" if active_workers > 0 else "worker queue is reachable but no active worker is registered"
    return ButlerDoctorCheck(
        name="worker queue",
        status=status,
        detail=detail,
        metadata={"queue_depth": queue_depth, "active_workers": active_workers},
    )


def _check_youtube_autoflow(youtube_service: YouTubeAgentService) -> ButlerDoctorCheck:
    try:
        subscription_count = len(youtube_service.list_subscriptions(include_deleted=True))
    except Exception as exc:
        return ButlerDoctorCheck(
            name="YouTube autoflow",
            status="fail",
            detail=str(exc).strip() or exc.__class__.__name__,
        )
    return ButlerDoctorCheck(
        name="YouTube autoflow",
        status="ok",
        detail="YouTube repository and service are reachable",
        metadata={"subscriptions": subscription_count},
    )


def _check_github_publish(github_service: GitHubAssistantService) -> ButlerDoctorCheck:
    try:
        health = github_service.health_report()
    except Exception as exc:
        return ButlerDoctorCheck(
            name="GitHub publish",
            status="fail",
            detail=str(exc).strip() or exc.__class__.__name__,
        )
    status = "ok" if health.doctor_ok else "degraded"
    detail = "GitHub assistant is ready" if health.doctor_ok else "GitHub assistant doctor is degraded"
    return ButlerDoctorCheck(
        name="GitHub publish",
        status=status,
        detail=detail,
        metadata={
            "profile_id": health.profile_id,
            "managed_repo_count": health.managed_repo_count,
            "gh_auth_ok": health.gh_auth_ok,
        },
    )


def _rollup_status(checks: list[ButlerDoctorCheck]) -> str:
    statuses = {item.status for item in checks}
    if "fail" in statuses:
        return "fail"
    if "degraded" in statuses:
        return "degraded"
    return "ok"
