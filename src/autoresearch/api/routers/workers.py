from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from autoresearch.api.dependencies import (
    get_telegram_notifier_service,
    get_telegram_settings,
    get_worker_inventory_service,
    get_worker_registry_service,
    get_worker_scheduler_service,
)
from autoresearch.api.settings import TelegramSettings
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_inventory import WorkerInventoryService
from autoresearch.core.services.worker_scheduler import (
    WorkerClaimError,
    WorkerReportError,
    WorkerSchedulerService,
)
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.shared.models import (
    JobStatus,
    WorkerClaimRead,
    WorkerClaimRequest,
    WorkerHeartbeatRequest,
    WorkerInventoryListRead,
    WorkerInventoryRead,
    WorkerInventorySummaryRead,
    WorkerQueueItemRead,
    WorkerRegisterRequest,
    WorkerRegistrationRead,
    WorkerRunReportRequest,
)


logger = logging.getLogger(__name__)

# Worker delivery markers that mean "the user already saw the worker bubble";
# any other terminal-state value (failed / skipped_no_token / missing) is what
# triggers the butler-fallback summary so the user is not left in silence.
_WORKER_DELIVERED_STATES = frozenset({"edited", "sent"})

_TERMINAL_STATUSES = frozenset(
    {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.INTERRUPTED, JobStatus.CANCELLED}
)


router = APIRouter(prefix="/api/v1/workers", tags=["workers"])


@router.get("", response_model=WorkerInventoryListRead, status_code=status.HTTP_200_OK)
def list_workers(
    service: WorkerInventoryService = Depends(get_worker_inventory_service),
) -> WorkerInventoryListRead:
    return service.list_workers()


@router.get("/summary", response_model=WorkerInventorySummaryRead, status_code=status.HTTP_200_OK)
def worker_summary(
    service: WorkerInventoryService = Depends(get_worker_inventory_service),
) -> WorkerInventorySummaryRead:
    return service.summary()


@router.get("/{worker_id}", response_model=WorkerInventoryRead, status_code=status.HTTP_200_OK)
def get_worker(
    worker_id: str,
    service: WorkerInventoryService = Depends(get_worker_inventory_service),
) -> WorkerInventoryRead:
    worker = service.get_worker(worker_id)
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")
    return worker


@router.post("/register", response_model=WorkerRegistrationRead, status_code=status.HTTP_200_OK)
def register_worker(
    payload: WorkerRegisterRequest,
    service: WorkerRegistryService = Depends(get_worker_registry_service),
) -> WorkerRegistrationRead:
    return service.register(payload)


@router.post("/{worker_id}/heartbeat", response_model=WorkerRegistrationRead, status_code=status.HTTP_200_OK)
def heartbeat_worker(
    worker_id: str,
    payload: WorkerHeartbeatRequest,
    service: WorkerRegistryService = Depends(get_worker_registry_service),
) -> WorkerRegistrationRead:
    try:
        return service.heartbeat(worker_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found") from exc


@router.post("/{worker_id}/claim", response_model=WorkerClaimRead, status_code=status.HTTP_200_OK)
def claim_worker_run(
    worker_id: str,
    payload: WorkerClaimRequest = Body(default_factory=WorkerClaimRequest),
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
) -> WorkerClaimRead:
    try:
        return service.claim(worker_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found") from exc
    except WorkerClaimError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc


@router.post(
    "/{worker_id}/runs/{run_id}/report",
    response_model=WorkerQueueItemRead,
    status_code=status.HTTP_200_OK,
)
def report_worker_run(
    worker_id: str,
    run_id: str,
    payload: WorkerRunReportRequest,
    service: WorkerSchedulerService = Depends(get_worker_scheduler_service),
    telegram_settings: TelegramSettings = Depends(get_telegram_settings),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
) -> WorkerQueueItemRead:
    try:
        stored = service.report(worker_id, run_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
    except WorkerReportError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    if telegram_settings.butler_completion_fallback_enabled and stored.status in _TERMINAL_STATUSES:
        try:
            _maybe_send_butler_completion_fallback(
                stored,
                notifier=notifier,
                settings=telegram_settings,
                scheduler=service,
            )
        except Exception:
            # Fallback is a best-effort safety net; never let it break /report.
            logger.exception("butler completion fallback raised for run=%s", stored.run_id)
    return stored


def _maybe_send_butler_completion_fallback(
    run: WorkerQueueItemRead,
    *,
    notifier: TelegramNotifierService,
    settings: TelegramSettings,
    scheduler: WorkerSchedulerService,
) -> None:
    """Send a brief brand-prefixed summary if the worker did not deliver the bubble itself.

    Dedup invariants:
    - Worker reports its own delivery state in ``metrics.telegram_notify_status``.
      We only fire the fallback when that value is missing or in a non-delivered
      state (``failed`` / ``skipped_no_token`` / ``skipped_no_chat``).
    - We mark ``metadata.telegram_butler_fallback_sent = True`` after a successful
      send so any retry of this code path becomes a no-op.
    - ``WorkerSchedulerService.report`` already rejects re-reports of terminal
      runs, so the fallback can fire at most once per run from this code path.
    """
    if not notifier.enabled:
        return
    metrics: dict[str, Any] = run.metrics or {}
    metadata: dict[str, Any] = run.metadata or {}
    notify_state = str(metrics.get("telegram_notify_status") or "").strip().lower()
    if notify_state in _WORKER_DELIVERED_STATES:
        return
    if metadata.get("telegram_butler_fallback_sent"):
        return
    payload: dict[str, Any] = run.payload or {}
    chat_id = str(payload.get("chat_id") or "").strip()
    if not chat_id:
        return

    ack_raw = metadata.get("telegram_queue_ack_message_id")
    ack_message_id: int | None = None
    if ack_raw is not None and str(ack_raw).strip() != "":
        try:
            ack_message_id = int(ack_raw)
        except (TypeError, ValueError):
            ack_message_id = None

    thread_raw = payload.get("message_thread_id")
    thread_id: int | None = None
    if thread_raw is not None and str(thread_raw).strip() != "":
        try:
            thread_id = int(thread_raw)
        except (TypeError, ValueError):
            thread_id = None

    text = _compose_butler_fallback_text(run=run, settings=settings, notify_state=notify_state)

    delivered = False
    if ack_message_id is not None:
        delivered = notifier.edit_message_text(
            chat_id=chat_id,
            message_id=ack_message_id,
            text=text,
            message_thread_id=thread_id,
        )
    if not delivered:
        delivered = notifier.send_message(
            chat_id=chat_id,
            text=text,
            message_thread_id=thread_id,
        )

    if delivered:
        try:
            scheduler.merge_queue_metadata(
                run.run_id,
                {
                    "telegram_butler_fallback_sent": True,
                    "telegram_butler_fallback_reason": notify_state or "missing_status",
                },
            )
        except Exception:
            logger.warning(
                "butler fallback succeeded but metadata write failed run=%s",
                run.run_id,
                exc_info=True,
            )


def _compose_butler_fallback_text(
    *,
    run: WorkerQueueItemRead,
    settings: TelegramSettings,
    notify_state: str,
) -> str:
    """Same brand + KV-table layout as the worker-side card so the chat reads consistently."""
    brand = (settings.telegram_worker_display_name or "").strip()
    task_name = (run.task_name or run.task_type.value or "(unnamed)").strip() or "(unnamed)"
    summary = ""
    result = run.result if isinstance(run.result, dict) else {}
    summary = str(result.get("summary") or run.message or "").strip()

    rows = [
        ("任务", task_name),
        ("run_id", str(run.run_id)),
        ("状态", run.status.value),
        ("通知", "管家兜底（worker 未送达）"),
    ]
    if notify_state:
        rows.append(("worker 投递", notify_state))
    if summary:
        rows.append(("摘要", summary[:600]))

    table_lines = ["| 项 | 值 |", "| --- | --- |"]
    for key, value in rows:
        cell = str(value).replace("|", "/").replace("\n", " ").strip()
        table_lines.append(f"| {key} | {cell[:900]} |")

    parts: list[str] = []
    if brand:
        parts.append(f"【{brand}】")
    parts.append("任务已结束。")
    parts.append("")
    parts.append("\n".join(table_lines))
    if run.error:
        parts.append("")
        parts.append(f"错误: {str(run.error)[:1000]}")
    return "\n".join(parts)[:3900]
