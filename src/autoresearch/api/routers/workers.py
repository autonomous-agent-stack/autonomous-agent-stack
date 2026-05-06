from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status

from autoresearch.api.dependencies import (
    get_control_plane_service,
    get_openclaw_compat_service,
    get_telegram_notifier_service,
    get_telegram_settings,
    get_worker_inventory_service,
    get_worker_registry_service,
    get_worker_scheduler_service,
)
from autoresearch.api.settings import TelegramSettings
from autoresearch.control_plane.service import ControlPlaneService
from autoresearch.core.services.telegram_completion_format import (
    TELEGRAM_MARKDOWN_V2_PARSE_MODE,
    format_butler_completion_message,
    format_butler_live_status_message,
    markdown_v2_escape,
    polish_butler_completion_card,
    resolve_telegram_agent_attribution,
)
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
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
    OpenClawSessionEventAppendRequest,
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
    control_plane_service: ControlPlaneService = Depends(get_control_plane_service),
    telegram_settings: TelegramSettings = Depends(get_telegram_settings),
    notifier: TelegramNotifierService = Depends(get_telegram_notifier_service),
    openclaw_service: OpenClawCompatService = Depends(get_openclaw_compat_service),
) -> WorkerQueueItemRead:
    try:
        stored = service.report(worker_id, run_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found") from exc
    except WorkerReportError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.detail) from exc

    if stored.status in _TERMINAL_STATUSES:
        if (stored.metadata or {}).get("control_plane_task_id"):
            try:
                control_plane_service.sync_worker_run(stored)
            except Exception:
                logger.exception("control-plane v2 sync raised for worker run=%s", stored.run_id)
        if telegram_settings.butler_api_completion_enabled:
            try:
                _try_deliver_butler_completion_primary(
                    stored,
                    notifier=notifier,
                    scheduler=service,
                    openclaw_service=openclaw_service,
                )
            except Exception:
                logger.exception("butler primary completion raised for run=%s", stored.run_id)
            # Primary may merge ``telegram_butler_primary_sent``; refresh before fallback
            # so we never double-notify with a stale ``WorkerQueueItemRead``.
            refreshed = service.get_run(stored.run_id)
            if refreshed is not None:
                stored = refreshed
        if telegram_settings.butler_completion_fallback_enabled:
            try:
                _maybe_send_butler_completion_fallback(
                    stored,
                    notifier=notifier,
                    settings=telegram_settings,
                    scheduler=service,
                    openclaw_service=openclaw_service,
                )
            except Exception:
                # Fallback is a best-effort safety net; never let it break /report.
                logger.exception("butler completion fallback raised for run=%s", stored.run_id)
    elif stored.status == JobStatus.RUNNING:
        if _is_xreach_auth_recovery_pause(stored):
            if (stored.metadata or {}).get("control_plane_task_id"):
                try:
                    control_plane_service.sync_worker_run(stored)
                except Exception:
                    logger.exception("control-plane v2 xreach recovery sync raised for worker run=%s", stored.run_id)
            if telegram_settings.butler_api_completion_enabled:
                try:
                    _maybe_send_xreach_auth_recovery_card(
                        stored,
                        notifier=notifier,
                        settings=telegram_settings,
                        scheduler=service,
                        openclaw_service=openclaw_service,
                    )
                except Exception:
                    logger.exception("xreach auth recovery card raised for run=%s", stored.run_id)
        elif telegram_settings.butler_live_updates_enabled:
            try:
                _try_deliver_butler_live_edit(
                    stored,
                    notifier=notifier,
                    scheduler=service,
                    settings=telegram_settings,
                )
            except Exception:
                logger.exception("butler live edit raised for run=%s", stored.run_id)
    return stored


def _is_xreach_auth_recovery_pause(run: WorkerQueueItemRead) -> bool:
    metrics = run.metrics if isinstance(run.metrics, dict) else {}
    result = run.result if isinstance(run.result, dict) else {}
    pause_reason = str(metrics.get("worker_pause_reason") or "").strip().lower()
    error_kind = str(metrics.get("error_kind") or result.get("error_kind") or "").strip().lower()
    return pause_reason == "xreach_auth_required" or error_kind == "collector_auth_required"


def _maybe_send_xreach_auth_recovery_card(
    run: WorkerQueueItemRead,
    *,
    notifier: TelegramNotifierService,
    settings: TelegramSettings,
    scheduler: WorkerSchedulerService,
    openclaw_service: OpenClawCompatService | None = None,
) -> None:
    if not notifier.enabled:
        return
    metadata = run.metadata if isinstance(run.metadata, dict) else {}
    if not metadata.get("telegram_completion_via_api"):
        return
    if metadata.get("telegram_xreach_auth_recovery_sent"):
        return
    payload = run.payload if isinstance(run.payload, dict) else {}
    chat_id = str(payload.get("chat_id") or metadata.get("chat_id") or "").strip()
    if not chat_id:
        return
    thread_raw = payload.get("message_thread_id") or metadata.get("message_thread_id")
    thread_id: int | None = None
    if thread_raw is not None and str(thread_raw).strip() != "":
        try:
            thread_id = int(thread_raw)
        except (TypeError, ValueError):
            thread_id = None

    text = _compose_xreach_auth_recovery_text(run=run, settings=settings)
    delivered = notifier.send_message(
        chat_id=chat_id,
        text=text,
        message_thread_id=thread_id,
        parse_mode=TELEGRAM_MARKDOWN_V2_PARSE_MODE,
        reply_markup=_xreach_auth_recovery_reply_markup(run.run_id),
    )
    if delivered:
        _append_telegram_assistant_context(
            run=run,
            text=text,
            openclaw_service=openclaw_service,
            source="telegram_xreach_auth_recovery",
        )
        scheduler.merge_queue_metadata(
            run.run_id,
            {
                "telegram_xreach_auth_recovery_sent": True,
                "telegram_xreach_auth_recovery_card": "sent",
            },
        )


def _compose_xreach_auth_recovery_text(
    *,
    run: WorkerQueueItemRead,
    settings: TelegramSettings,
) -> str:
    brand = (settings.telegram_worker_display_name or "AAS Worker").strip() or "AAS Worker"
    task_name = (run.task_name or run.task_type.value or "整理X书签").strip() or "整理X书签"
    result = run.result if isinstance(run.result, dict) else {}
    attempts = result.get("xreach_auth_attempts") if isinstance(result.get("xreach_auth_attempts"), list) else []
    attempt_lines: list[str] = []
    for attempt in attempts[:4]:
        if not isinstance(attempt, dict):
            continue
        step = str(attempt.get("step") or "").strip()
        code = str(attempt.get("returncode") or "").strip()
        if step:
            attempt_lines.append(f"- {step}: {code or '?'}")
    attempt_text = "\n".join(attempt_lines) if attempt_lines else "- auth check: needs user action"
    title = f"{brand} · 需要你配合恢复 X 书签采集"
    body = "\n".join(
        [
            "Hermes 兜底判断：这不是整理失败，是本机 X 登录态需要恢复。原采集 run 已暂停，完成恢复后可以继续同一个 run。",
            "Hermes recovery: this is not a terminal collection failure. The local X login state needs recovery; the original run is paused and can continue after recovery.",
            "",
            f"任务：{task_name}",
            f"run id：{run.run_id}",
            "状态：等待用户配合 / waiting for user action",
            "",
            "已尝试 / Attempts",
            attempt_text,
            "",
            "下一步：点“打开登录页”，在本机浏览器完成登录后点“我已完成，继续采集”。也可以先点“重新检测登录态”。",
            "Next: tap Open login page, finish login locally, then tap Resume collection. You can also tap Recheck auth first.",
        ]
    )
    return "\n".join([markdown_v2_escape(title), "", markdown_v2_escape(body)])[:3900]


def _xreach_auth_recovery_reply_markup(run_id: str) -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "打开登录页", "callback_data": f"/xreach-auth-open {run_id}"},
                {"text": "我已完成，继续采集", "callback_data": f"/xreach-auth-resume {run_id}"},
            ],
            [
                {"text": "重新检测登录态", "callback_data": f"/xreach-auth-check {run_id}"},
                {"text": "取消任务", "callback_data": f"/cancel {run_id}"},
            ],
        ]
    }


def _try_deliver_butler_live_edit(
    run: WorkerQueueItemRead,
    *,
    notifier: TelegramNotifierService,
    scheduler: WorkerSchedulerService,
    settings: TelegramSettings,
) -> None:
    """Throttle-edit the queue-ack bubble while the worker reports RUNNING (Hermes ticks)."""
    if not notifier.enabled:
        return
    metadata: dict[str, Any] = run.metadata or {}
    if not metadata.get("telegram_completion_via_api"):
        return
    if metadata.get("telegram_butler_primary_sent"):
        return
    metrics: dict[str, Any] = run.metrics or {}
    if str(metrics.get("telegram_live_phase") or "").strip().lower() != "running":
        return

    payload: dict[str, Any] = run.payload or {}
    chat_id = str(payload.get("chat_id") or metadata.get("chat_id") or "").strip()
    if not chat_id:
        return

    ack_raw = metadata.get("telegram_queue_ack_message_id")
    ack_message_id: int | None = None
    if ack_raw is not None and str(ack_raw).strip() != "":
        try:
            ack_message_id = int(ack_raw)
        except (TypeError, ValueError):
            ack_message_id = None
    if ack_message_id is None:
        return

    thread_raw = payload.get("message_thread_id") or metadata.get("message_thread_id")
    thread_id: int | None = None
    if thread_raw is not None and str(thread_raw).strip() != "":
        try:
            thread_id = int(thread_raw)
        except (TypeError, ValueError):
            thread_id = None

    brand = (settings.telegram_worker_display_name or "").strip()
    text = format_butler_live_status_message(
        brand=brand,
        message=run.message,
        metrics=metrics,
    )
    if not text.strip():
        return

    body_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:24]
    now = time.time()
    last_raw = metadata.get("telegram_live_last_edit_at")
    last_hash = str(metadata.get("telegram_live_last_body_hash") or "")
    if last_raw is not None:
        try:
            last_ts = float(last_raw)
        except (TypeError, ValueError):
            last_ts = 0.0
        if (now - last_ts) < float(settings.butler_live_interval_seconds) and body_hash == last_hash:
            return

    ok = notifier.edit_message_text(
        chat_id=chat_id,
        message_id=ack_message_id,
        text=text,
        message_thread_id=thread_id,
        parse_mode=TELEGRAM_MARKDOWN_V2_PARSE_MODE,
    )
    if ok:
        try:
            scheduler.merge_queue_metadata(
                run.run_id,
                {
                    "telegram_live_last_edit_at": str(now),
                    "telegram_live_last_body_hash": body_hash,
                },
            )
        except Exception:
            logger.warning(
                "butler live edit ok but metadata write failed run=%s",
                run.run_id,
                exc_info=True,
            )


def _try_deliver_butler_completion_primary(
    run: WorkerQueueItemRead,
    *,
    notifier: TelegramNotifierService,
    scheduler: WorkerSchedulerService,
    openclaw_service: OpenClawCompatService | None = None,
) -> None:
    """Edit the queue-ack bubble via the API bot when the worker delegated the card (Hermes path)."""
    if not notifier.enabled:
        return
    metadata: dict[str, Any] = run.metadata or {}
    if not metadata.get("telegram_completion_via_api"):
        return
    if metadata.get("telegram_butler_primary_sent"):
        return
    result: dict[str, Any] = run.result if isinstance(run.result, dict) else {}
    card = str(result.get("telegram_completion_card_text") or "").strip()
    if not card:
        return
    payload: dict[str, Any] = run.payload or {}
    chat_id = str(payload.get("chat_id") or metadata.get("chat_id") or "").strip()
    if not chat_id:
        return

    ack_raw = metadata.get("telegram_queue_ack_message_id")
    ack_message_id: int | None = None
    if ack_raw is not None and str(ack_raw).strip() != "":
        try:
            ack_message_id = int(ack_raw)
        except (TypeError, ValueError):
            ack_message_id = None

    thread_raw = payload.get("message_thread_id") or metadata.get("message_thread_id")
    thread_id: int | None = None
    if thread_raw is not None and str(thread_raw).strip() != "":
        try:
            thread_id = int(thread_raw)
        except (TypeError, ValueError):
            thread_id = None

    text = polish_butler_completion_card(card)
    parse_mode = str(result.get("telegram_completion_card_parse_mode") or "").strip() or None
    delivered = False
    if ack_message_id is not None:
        delivered = notifier.edit_message_text(
            chat_id=chat_id,
            message_id=ack_message_id,
            text=text,
            message_thread_id=thread_id,
            parse_mode=parse_mode,
        )
    if not delivered:
        delivered = notifier.send_message(
            chat_id=chat_id,
            text=text,
            message_thread_id=thread_id,
            parse_mode=parse_mode,
        )
    if delivered:
        _append_telegram_assistant_context(
            run=run,
            text=text,
            openclaw_service=openclaw_service,
            source="telegram_butler_primary_completion",
        )
        try:
            scheduler.merge_queue_metadata(
                run.run_id,
                {"telegram_butler_primary_sent": True},
            )
        except Exception:
            logger.warning(
                "butler primary delivery ok but metadata write failed run=%s",
                run.run_id,
                exc_info=True,
            )


def _maybe_send_butler_completion_fallback(
    run: WorkerQueueItemRead,
    *,
    notifier: TelegramNotifierService,
    settings: TelegramSettings,
    scheduler: WorkerSchedulerService,
    openclaw_service: OpenClawCompatService | None = None,
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
    if notify_state == "deferred":
        return
    if notify_state in _WORKER_DELIVERED_STATES:
        return
    if metadata.get("telegram_butler_primary_sent"):
        return
    if metadata.get("telegram_butler_fallback_sent"):
        return
    payload: dict[str, Any] = run.payload or {}
    chat_id = str(payload.get("chat_id") or metadata.get("chat_id") or "").strip()
    if not chat_id:
        return

    ack_raw = metadata.get("telegram_queue_ack_message_id")
    ack_message_id: int | None = None
    if ack_raw is not None and str(ack_raw).strip() != "":
        try:
            ack_message_id = int(ack_raw)
        except (TypeError, ValueError):
            ack_message_id = None

    thread_raw = payload.get("message_thread_id") or metadata.get("message_thread_id")
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
            parse_mode=TELEGRAM_MARKDOWN_V2_PARSE_MODE,
        )
    if not delivered:
        delivered = notifier.send_message(
            chat_id=chat_id,
            text=text,
            message_thread_id=thread_id,
            parse_mode=TELEGRAM_MARKDOWN_V2_PARSE_MODE,
        )

    if delivered:
        _append_telegram_assistant_context(
            run=run,
            text=text,
            openclaw_service=openclaw_service,
            source="telegram_butler_fallback_completion",
        )
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


def _append_telegram_assistant_context(
    *,
    run: WorkerQueueItemRead,
    text: str,
    openclaw_service: OpenClawCompatService | None,
    source: str,
) -> None:
    if openclaw_service is None:
        return
    metadata = run.metadata if isinstance(run.metadata, dict) else {}
    payload = run.payload if isinstance(run.payload, dict) else {}
    session_id = str(
        metadata.get("control_plane_session_id")
        or metadata.get("session_id")
        or payload.get("session_id")
        or ""
    ).strip()
    if not session_id:
        return
    try:
        openclaw_service.append_event(
            session_id=session_id,
            request=OpenClawSessionEventAppendRequest(
                role="assistant",
                content=text[:3900],
                metadata={
                    "source": source,
                    "run_id": run.run_id,
                    "task_type": str(getattr(run.task_type, "value", run.task_type)),
                    "status": run.status.value,
                },
            ),
        )
    except Exception:
        logger.warning("failed to append Telegram assistant context for run=%s", run.run_id, exc_info=True)


def _compose_butler_fallback_text(
    *,
    run: WorkerQueueItemRead,
    settings: TelegramSettings,
    notify_state: str,
) -> str:
    """Same brand + KV-table layout as the worker-side card so the chat reads consistently."""
    brand = (settings.telegram_worker_display_name or "").strip()
    task_name = (run.task_name or run.task_type.value or "(unnamed)").strip() or "(unnamed)"
    payload = run.payload if isinstance(run.payload, dict) else {}
    metadata = run.metadata if isinstance(run.metadata, dict) else {}
    summary = ""
    result = run.result if isinstance(run.result, dict) else {}
    metrics = run.metrics if isinstance(run.metrics, dict) else {}
    summary = str(result.get("summary") or run.message or "").strip()
    hint = str(result.get("telegram_hint") or result.get("user_hint") or "").strip()
    phase = str(metrics.get("telegram_live_phase") or run.status.value).strip().lower() or run.status.value
    exit_reason = str(metrics.get("exit_reason") or result.get("exit_reason") or "").strip()
    error_kind = str(metrics.get("error_kind") or result.get("error_kind") or "").strip()
    collector = str(metrics.get("collector") or result.get("collector") or "").strip()
    primary_agent, agent_names = resolve_telegram_agent_attribution(
        payload,
        metadata,
        metrics,
        result,
    )
    runtime_id = (
        str(payload.get("runtime_id") or run.task_type.value or metadata.get("capability_id"))
        .strip()
        .lower()
    )
    diagnostics_parts = [f"runtime={runtime_id}", f"exit={exit_reason or error_kind or run.status.value}"]
    if error_kind:
        diagnostics_parts.append(f"error_kind={error_kind}")
    if collector:
        diagnostics_parts.append(f"collector={collector}")
    diagnostics = ", ".join(diagnostics_parts)
    body = _content_kb_downstream_completion_body(
        run=run,
        payload=payload,
        metadata=metadata,
        result=result,
        summary=summary,
    )
    if not body:
        body = "管家兜底：worker 未能直接送达 Telegram 结果。"
    if hint:
        body = f"{body}\n\n{hint}"
    elif summary and "content_kb_ingest:" not in body:
        body = f"{body}\n\n{summary}"
    return format_butler_completion_message(
        brand=brand,
        task_name=task_name,
        run_id=str(run.run_id),
        status_label=run.status.value,
        body=body,
        runtime_id=runtime_id,
        capability_id=str(metadata.get("capability_id") or payload.get("capability_id") or runtime_id),
        primary_agent=primary_agent,
        agent_names=agent_names,
        phase=phase,
        diagnostics=diagnostics,
        summary=summary[:600] if summary else None,
        notify_state=notify_state,
        error=str(run.error)[:1000] if run.error else None,
    )


def _content_kb_downstream_completion_body(
    *,
    run: WorkerQueueItemRead,
    payload: dict[str, Any],
    metadata: dict[str, Any],
    result: dict[str, Any],
    summary: str,
) -> str:
    task_type = str(getattr(run.task_type, "value", run.task_type) or "").strip().lower()
    if task_type != "content_kb_ingest" or not _has_source_collect_parent(payload, metadata, result):
        return ""
    if run.status != JobStatus.COMPLETED:
        return ""

    detail_lookup = bool(result.get("source_collect_detail_lookup") or payload.get("source_collect_detail_lookup"))
    if detail_lookup:
        lines = [
            "X 书签详情：已同步到知识库。",
            "X bookmark details: synced to the knowledge base.",
        ]
    else:
        lines = [
            "X 书签：采集结果已同步到知识库。",
            "X bookmarks: collection synced to the knowledge base.",
        ]
    answer = str(result.get("source_collect_answer") or payload.get("source_collect_answer") or "").strip()
    item_count = _optional_int(_first_present(result.get("source_collect_item_count"), payload.get("source_collect_item_count")))
    new_count = _optional_int(
        _first_present(result.get("source_collect_new_item_count"), payload.get("source_collect_new_item_count"))
    )
    known_count = _optional_int(
        _first_present(result.get("source_collect_known_item_count"), payload.get("source_collect_known_item_count"))
    )
    new_urls = _display_urls(
        result.get("source_collect_new_source_urls") or payload.get("source_collect_new_source_urls")
    )
    new_items = _display_new_item_details(
        result.get("source_collect_new_items") or payload.get("source_collect_new_items")
    )
    if answer and not new_items:
        lines.extend(["", "回答 / Answer：", answer])
    stats: list[str] = []
    if item_count is not None:
        stats.append(f"采集 {item_count}")
    if new_count is not None:
        if new_count == 0:
            stats.append("新增 0")
        else:
            stats.append(f"新增 {new_count}")
    if known_count is not None:
        stats.append(f"已知 {known_count}")
    if stats:
        lines.append(f"统计 / Stats：{'；'.join(stats)}")
    if new_count == 0:
        lines.append("结论 / Result：没有发现新书签。 / No new bookmarks found.")
    if new_items:
        lines.append("新增摘要 / New:")
        lines.extend(new_items)
    if new_urls and not new_items:
        lines.append("新增来源 / New sources：")
        lines.extend(f"- {url}" for url in new_urls)
    repo = str(result.get("repo") or "").strip()
    topic = str(result.get("topic") or payload.get("topic") or "").strip()
    directory = str(result.get("directory") or "").strip()
    files = _display_file_names(result.get("files_written"))
    kb_parts = [part for part in (repo, topic) if part]
    if kb_parts:
        lines.append(f"知识库 / KB：{' · '.join(kb_parts)}")
    elif directory:
        lines.append(f"知识库 / KB：{directory}")
    if files:
        lines.append(f"文件 / Files：{', '.join(files)}")
    return "\n".join(lines)


def _has_source_collect_parent(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    result: dict[str, Any],
) -> bool:
    if metadata.get("source_collect_downstream") is True:
        return True
    parent_keys = ("source_collect_run_id", "source_collect_worker_run_id")
    return any(payload.get(key) or metadata.get(key) or result.get(key) for key in parent_keys)


def _display_file_names(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for item in value[:5]:
        text = str(item or "").strip()
        if not text:
            continue
        names.append(text.rsplit("/", 1)[-1])
    return names


def _display_urls(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    urls: list[str] = []
    seen: set[str] = set()
    for item in value[:3]:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        urls.append(text)
        seen.add(text)
    return urls


def _display_new_item_details(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for index, item in enumerate(value[:3], start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or f"Item {index}").strip()
        url = str(item.get("url") or item.get("source_url") or "").strip()
        author = str(item.get("author") or "").strip()
        text = str(item.get("text") or item.get("content") or item.get("body") or "").strip()
        label = _compact_item_label(title=title, author=author, text=text)
        lines.append(f"{index}. {label}")
        if author:
            lines.append(f"   作者 / Author：{author}")
        if url:
            lines.append(f"   {url}")
    return lines


def _compact_item_label(*, title: str, author: str, text: str) -> str:
    clean_title = title.strip()
    if clean_title.lower().startswith("x bookmark by @"):
        clean_title = ""
    prefix = author.strip() or clean_title or "X bookmark"
    summary = _compact_text(text, limit=72)
    if summary and summary != prefix:
        return f"{prefix}：{summary}"
    return prefix


def _compact_text(text: str, *, limit: int) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(1, limit - 1)].rstrip() + "…"


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None
