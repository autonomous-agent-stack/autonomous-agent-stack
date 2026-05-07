from __future__ import annotations

from pathlib import Path
import time

from fastapi import APIRouter, Body, Depends, HTTPException, status

from autoresearch.api.dependencies import (
    get_butler_agent_state_service,
    get_butler_dispatch_center,
    get_github_assistant_service,
    get_github_ops_service,
    get_hermes_gateway_transport,
    get_runtime_settings,
    get_runtime_adapter_registry_service,
    get_telegram_notifier_service,
    get_worker_inventory_service,
    get_worker_scheduler_service,
    get_youtube_agent_service,
)
from autoresearch.api.settings import RuntimeSettings
from autoresearch.core.services.butler_agent_state import ButlerAgentStateService
from autoresearch.core.services.butler_dispatch import ButlerDoctorCheck, ButlerDoctorRead, ButlerDispatchCenter
from autoresearch.core.services.hermes_gateway_bridge import HttpHermesGatewayTransport
from autoresearch.core.services.hermes_readiness import (
    build_hermes_cli_readiness_check,
    build_hermes_interactive_callback_check,
)
from autoresearch.core.services.recovery_orchestrator import ButlerRecoveryOrchestrator
from autoresearch.core.services.runtime_adapter_registry import RuntimeAdapterServiceRegistry
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_inventory import WorkerInventoryService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.core.services.youtube_agent import YouTubeAgentService
from autoresearch.core.services.github_ops import GitHubOpsService
from autoresearch.github_assistant.service import GitHubAssistantService
from autoresearch.shared.models import (
    ButlerAgentStateRead,
    ButlerAgentStatus,
    ButlerAgentStatusChangeRequest,
    JobStatus,
)


router = APIRouter(prefix="/api/v1/butler", tags=["butler"])


@router.get("/agents", response_model=list[ButlerAgentStateRead])
def list_butler_agents(
    service: ButlerAgentStateService = Depends(get_butler_agent_state_service),
) -> list[ButlerAgentStateRead]:
    return service.list_agents()


@router.get("/agents/{agent_name}", response_model=ButlerAgentStateRead)
def get_butler_agent(
    agent_name: str,
    service: ButlerAgentStateService = Depends(get_butler_agent_state_service),
) -> ButlerAgentStateRead:
    item = service.get_agent(agent_name)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Butler agent not found")
    return item


@router.post("/agents/{agent_name}/start", response_model=ButlerAgentStateRead)
def start_butler_agent(
    agent_name: str,
    payload: ButlerAgentStatusChangeRequest = Body(default_factory=ButlerAgentStatusChangeRequest),
    service: ButlerAgentStateService = Depends(get_butler_agent_state_service),
) -> ButlerAgentStateRead:
    return _set_butler_agent_status(
        agent_name=agent_name,
        payload=payload,
        service=service,
        next_status=ButlerAgentStatus.ACTIVE,
    )


@router.post("/agents/{agent_name}/stop", response_model=ButlerAgentStateRead)
def stop_butler_agent(
    agent_name: str,
    payload: ButlerAgentStatusChangeRequest = Body(default_factory=ButlerAgentStatusChangeRequest),
    service: ButlerAgentStateService = Depends(get_butler_agent_state_service),
) -> ButlerAgentStateRead:
    return _set_butler_agent_status(
        agent_name=agent_name,
        payload=payload,
        service=service,
        next_status=ButlerAgentStatus.DISABLED,
    )


@router.post("/agents/{agent_name}/drain", response_model=ButlerAgentStateRead)
def drain_butler_agent(
    agent_name: str,
    payload: ButlerAgentStatusChangeRequest = Body(default_factory=ButlerAgentStatusChangeRequest),
    service: ButlerAgentStateService = Depends(get_butler_agent_state_service),
) -> ButlerAgentStateRead:
    return _set_butler_agent_status(
        agent_name=agent_name,
        payload=payload,
        service=service,
        next_status=ButlerAgentStatus.DRAINING,
    )


@router.post("/agents/{agent_name}/restart", response_model=ButlerAgentStateRead)
def restart_butler_agent(
    agent_name: str,
    payload: ButlerAgentStatusChangeRequest = Body(default_factory=ButlerAgentStatusChangeRequest),
    agent_state: ButlerAgentStateService = Depends(get_butler_agent_state_service),
    worker_scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> ButlerAgentStateRead:
    drain_state = _set_butler_agent_status(
        agent_name=agent_name,
        payload=payload,
        service=agent_state,
        next_status=ButlerAgentStatus.DRAINING,
        metadata={"restart_phase": "drain"},
    )
    deadline = time.monotonic() + payload.wait_seconds
    active_runs = _running_target_agent_count(worker_scheduler, drain_state.agent_name)
    while active_runs > 0 and time.monotonic() < deadline:
        time.sleep(1)
        active_runs = _running_target_agent_count(worker_scheduler, drain_state.agent_name)
    return _set_butler_agent_status(
        agent_name=drain_state.agent_name,
        payload=payload,
        service=agent_state,
        next_status=ButlerAgentStatus.ACTIVE,
        metadata={
            "restart_phase": "start",
            "restart_wait_seconds": payload.wait_seconds,
            "restart_active_runs_remaining": active_runs,
            "restart_wait_timed_out": active_runs > 0,
        },
    )


@router.get("/doctor", response_model=ButlerDoctorRead)
def butler_doctor(
    dispatch_center: ButlerDispatchCenter = Depends(get_butler_dispatch_center),
    runtime_registry: RuntimeAdapterServiceRegistry = Depends(get_runtime_adapter_registry_service),
    runtime_settings: RuntimeSettings = Depends(get_runtime_settings),
    hermes_transport: HttpHermesGatewayTransport | None = Depends(get_hermes_gateway_transport),
    worker_inventory: WorkerInventoryService = Depends(get_worker_inventory_service),
    worker_scheduler: WorkerSchedulerService = Depends(get_worker_scheduler_service),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
    youtube_service: YouTubeAgentService = Depends(get_youtube_agent_service),
    github_service: GitHubAssistantService = Depends(get_github_assistant_service),
    github_ops_service: GitHubOpsService = Depends(get_github_ops_service),
) -> ButlerDoctorRead:
    checks: list[ButlerDoctorCheck] = []
    checks.extend(dispatch_center.doctor_checks())
    checks.append(_check_hermes(runtime_registry))
    checks.append(build_hermes_cli_readiness_check())
    checks.append(
        _check_hermes_interactive_callbacks(
            runtime_settings=runtime_settings,
            hermes_transport=hermes_transport,
            worker_inventory=worker_inventory,
        )
    )
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
    checks.append(_check_github_ops(github_ops_service))
    checks.extend(ButlerRecoveryOrchestrator(repo_root=_repo_root()).doctor_checks())
    return ButlerDoctorRead(status=_rollup_status(checks), checks=checks)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _set_butler_agent_status(
    *,
    agent_name: str,
    payload: ButlerAgentStatusChangeRequest,
    service: ButlerAgentStateService,
    next_status: ButlerAgentStatus,
    metadata: dict[str, object] | None = None,
) -> ButlerAgentStateRead:
    try:
        return service.set_status(
            agent_name,
            next_status,
            actor=payload.actor,
            reason=payload.reason,
            metadata={**payload.metadata, **dict(metadata or {})},
        )
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Butler agent not found") from exc


def _running_target_agent_count(worker_scheduler: WorkerSchedulerService, agent_name: str) -> int:
    return sum(
        1
        for run in worker_scheduler.list_queue()
        if run.status == JobStatus.RUNNING
        and str((run.metadata or {}).get("target_agent") or "").strip() == agent_name
    )


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


def _check_hermes_interactive_callbacks(
    *,
    runtime_settings: RuntimeSettings,
    hermes_transport: HttpHermesGatewayTransport | None,
    worker_inventory: WorkerInventoryService,
) -> ButlerDoctorCheck:
    try:
        inventory = worker_inventory.list_workers()
    except Exception as exc:
        return ButlerDoctorCheck(
            name="Hermes interactive callbacks",
            status="fail",
            detail=str(exc).strip() or exc.__class__.__name__,
            metadata={
                "api_gateway_configured": hermes_transport is not None,
                "api_gateway_health_ok": None,
                "interactive_worker_count": 0,
                "matching_db_worker_count": 0,
                "api_db_path": str(runtime_settings.api_db_path),
            },
        )
    return build_hermes_interactive_callback_check(
        api_db_path=runtime_settings.api_db_path,
        hermes_transport=hermes_transport,
        workers=list(inventory.workers),
        probe_gateway=True,
    )


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


def _check_github_ops(github_ops_service: GitHubOpsService) -> ButlerDoctorCheck:
    report = github_ops_service.doctor()
    status = str(report.get("status") or "fail")
    detail = "GitHub ops executor is ready" if status == "ok" else "GitHub ops executor is degraded"
    return ButlerDoctorCheck(
        name="GitHub ops",
        status="ok" if status == "ok" else "degraded" if status == "degraded" else "fail",
        detail=detail,
        metadata=report,
    )


def _rollup_status(checks: list[ButlerDoctorCheck]) -> str:
    statuses = {item.status for item in checks}
    if "fail" in statuses:
        return "fail"
    if "degraded" in statuses:
        return "degraded"
    return "ok"
