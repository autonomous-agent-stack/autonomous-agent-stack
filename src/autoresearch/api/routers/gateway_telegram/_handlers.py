from __future__ import annotations

from typing import Any

from fastapi import BackgroundTasks

from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.standby_youtube_autoflow import (
    extract_urls_from_text,
    extract_youtube_urls_from_text,
)
from autoresearch.core.services.telegram_identity import TelegramSessionIdentityRead
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_scheduler import WorkerSchedulerService
from autoresearch.shared.models import (
    OpenClawSessionEventAppendRequest,
    StandbyYouTubeAutoflowRequest,
    TelegramWebhookAck,
    WorkerQueueItemCreateRequest,
    WorkerTaskType,
)

from ._extract import _safe_int, _safe_str
from ._messages import _telegram_queue_ack_message, _truncate_telegram_text, _utc_now
from ._session import (
    _append_user_event,
    _build_task_name,
    _find_or_create_telegram_session,
)


def _classify_telegram_youtube_ingress(text: str) -> tuple[str, str | None, str | None]:
    normalized_text = text.strip()
    if not normalized_text:
        return ("skip", None, None)

    all_urls = extract_urls_from_text(normalized_text)
    youtube_urls = extract_youtube_urls_from_text(normalized_text)
    has_youtube_hint = "youtu" in normalized_text.lower()

    if not all_urls:
        if has_youtube_hint:
            return ("reject", None, "未找到合法的 YouTube URL。")
        return ("skip", None, None)

    if len(all_urls) > 1:
        if youtube_urls or has_youtube_hint:
            return ("reject", None, "当前只支持每条消息提交 1 条 YouTube 链接。")
        return ("skip", None, None)

    only_url = all_urls[0]
    if len(youtube_urls) == 1 and youtube_urls[0] == only_url:
        return ("accept", only_url, None)
    if has_youtube_hint:
        return ("reject", None, "消息里必须只包含 1 条合法的 YouTube URL。")
    return ("skip", None, None)


def _handle_telegram_youtube_autoflow(
    *,
    chat_id: str,
    text: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
    worker_scheduler: WorkerSchedulerService,
    decision: str,
    source_url: str | None,
    rejection_reason: str | None,
) -> TelegramWebhookAck:
    session = _find_or_create_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
        background_tasks=background_tasks,
        notifier=notifier,
    )
    _append_user_event(
        openclaw_service=openclaw_service,
        session=session,
        text=text,
        update=update,
        extracted=extracted,
        session_identity=session_identity,
    )

    metadata = {
        "source": "telegram_youtube_autoflow",
        "chat_id": chat_id,
        "update_id": _safe_int(update.get("update_id")),
        "message_id": extracted.get("message_id"),
        "username": extracted.get("username"),
        "scope": session_identity.scope.value,
        "session_key": session_identity.session_key,
        "assistant_id": session_identity.assistant_id,
        "chat_type": session_identity.chat_context.chat_type.value,
        "actor_role": session_identity.actor.role.value,
        "actor_user_id": session_identity.actor.user_id,
        "session_id": session.session_id,
    }

    if decision != "accept" or source_url is None:
        reason = rejection_reason or "消息里必须只包含 1 条合法的 YouTube URL。"
        _record_telegram_youtube_autoflow_status(
            openclaw_service=openclaw_service,
            session_id=session.session_id,
            content="youtube autoflow rejected",
            metadata={
                **metadata,
                "status": "rejected",
                "reason": reason,
            },
        )
        if notifier.enabled:
            background_tasks.add_task(
                notifier.send_message,
                chat_id=chat_id,
                text=_build_telegram_youtube_autoflow_message(
                    status="rejected",
                    reason=reason,
                ),
            )
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            session_id=session.session_id,
            reason=reason,
            metadata={
                **metadata,
                "status": "rejected",
            },
        )

    requested_by = session_identity.actor.user_id or _safe_str(extracted.get("from_user_id")) or chat_id
    request_payload = StandbyYouTubeAutoflowRequest(
        source_url=source_url,
        input_text=text,
        requested_by=requested_by,
        source="telegram_gateway",
        metadata=metadata,
    )

    try:
        queued_run = worker_scheduler.enqueue(
            WorkerQueueItemCreateRequest(
                task_name="telegram_youtube_autoflow",
                task_type=WorkerTaskType.YOUTUBE_AUTOFLOW,
                payload=request_payload.model_dump(mode="json"),
                requested_by=requested_by,
                metadata={
                    **metadata,
                    "source_url": source_url,
                    "message_thread_id": extracted.get("message_thread_id"),
                    "telegram_completion_via_api": True,
                },
            )
        )
    except Exception as exc:
        reason = str(exc).strip() or "failed to enqueue youtube_autoflow"
        _record_telegram_youtube_autoflow_status(
            openclaw_service=openclaw_service,
            session_id=session.session_id,
            content="youtube autoflow enqueue failed",
            metadata={
                **metadata,
                "status": "failed",
                "reason": reason,
                "source_url": source_url,
            },
        )
        if notifier.enabled:
            background_tasks.add_task(
                notifier.send_message,
                chat_id=chat_id,
                text=_build_telegram_youtube_autoflow_message(
                    status="failed",
                    reason=reason,
                    source_url=source_url,
                ),
            )
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            session_id=session.session_id,
            reason=reason,
            metadata={
                **metadata,
                "status": "failed",
                "source_url": source_url,
            },
        )

    _record_telegram_youtube_autoflow_status(
        openclaw_service=openclaw_service,
        session_id=session.session_id,
        content=f"youtube autoflow queued: {queued_run.run_id}",
        metadata={
            **metadata,
            "status": "accepted",
            "run_id": queued_run.run_id,
            "task_type": queued_run.task_type.value,
            "source_url": source_url,
        },
    )
    if notifier.enabled:
        ack_text = _telegram_queue_ack_message(
            task_name="telegram_youtube_autoflow",
            run_id=queued_run.run_id,
            worker_brand="YouTube Ops",
            runtime_id="youtube_autoflow",
            agent_name="youtube_ops",
        )
        ack_message_id = notifier.send_message_get_message_id(
            chat_id=chat_id,
            text=ack_text,
            message_thread_id=_safe_int(extracted.get("message_thread_id")),
        )
        if ack_message_id is not None:
            worker_scheduler.merge_queue_metadata(
                queued_run.run_id,
                {
                    "telegram_queue_ack_message_id": ack_message_id,
                    "telegram_completion_via_api": True,
                    "chat_id": chat_id,
                    "message_thread_id": extracted.get("message_thread_id"),
                },
            )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            **metadata,
            "status": "accepted",
            "run_id": queued_run.run_id,
            "task_type": queued_run.task_type.value,
            "source_url": source_url,
        },
    )


def _record_telegram_youtube_autoflow_status(
    *,
    openclaw_service: OpenClawCompatService,
    session_id: str,
    content: str,
    metadata: dict[str, Any],
) -> None:
    openclaw_service.append_event(
        session_id=session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=content,
            metadata=metadata,
        ),
    )
    openclaw_service.update_metadata(
        session_id=session_id,
        metadata_updates={
            "latest_telegram_youtube_autoflow_status": metadata.get("status"),
            "latest_telegram_youtube_autoflow_reason": metadata.get("reason"),
            "latest_telegram_youtube_autoflow_run_id": metadata.get("run_id"),
            "latest_telegram_youtube_autoflow_task_type": metadata.get("task_type"),
            "latest_telegram_youtube_autoflow_source_url": metadata.get("source_url"),
        },
    )


def _build_telegram_youtube_autoflow_message(
    *,
    status: str,
    reason: str | None = None,
    run_id: str | None = None,
    source_url: str | None = None,
) -> str:
    lines = [
        "[YouTube Autoflow]",
        f"status: {status}",
    ]
    if run_id:
        lines.append(f"run: {run_id}")
    if source_url:
        lines.append(f"url: {source_url}")
    if reason:
        lines.extend(["", reason])
    return _truncate_telegram_text("\n".join(lines).strip())


def _handle_butler_excel_audit(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    text: str,
    background_tasks: BackgroundTasks,
    notifier: TelegramNotifierService,
    session_identity: Any,
    butler_classification: Any,
) -> TelegramWebhookAck:
    """Route detected Excel audit intent to ExcelAuditService (async)."""
    from autoresearch.shared.excel_audit_contract import ExcelAuditCreateRequest
    from autoresearch.api.dependencies import get_excel_audit_service

    attachments = butler_classification.extracted_params.get("attachments", [])

    service = get_excel_audit_service()
    req = ExcelAuditCreateRequest(
        task_brief=text,
        source_files=attachments,
    )

    # Step 1: Create job record (fast, sync) — returns QUEUED status
    record = service.create(req)

    # Store DSL params for async execution
    record = record.model_copy(update={
        "metadata": {
            "source_files": attachments,
            "rules": [r.model_dump() for r in req.rules],
            "sheet_mapping": req.sheet_mapping.model_dump(),
            "outputs": req.options,
        },
    })
    service._repository.save(record.audit_id, record)

    # Step 2: Send immediate acceptance notice
    if notifier.enabled:
        thread_id = _safe_int(extracted.get("message_thread_id"))
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=f"📊 Excel 核对已受理，任务号: {record.audit_id}，正在后台执行...",
            message_thread_id=thread_id,
        )

    # Step 3: Schedule actual execution in background
    background_tasks.add_task(
        _execute_excel_audit_background,
        audit_id=record.audit_id,
        chat_id=chat_id,
        thread_id=_safe_int(extracted.get("message_thread_id")),
        notifier=notifier,
    )

    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        reason="butler routed to excel_audit (async)",
        metadata={
            "butler_task_type": "excel_audit",
            "butler_confidence": butler_classification.confidence,
            "audit_id": record.audit_id,
        },
    )


def _execute_excel_audit_background(
    *,
    audit_id: str,
    chat_id: str,
    thread_id: int | None,
    notifier: TelegramNotifierService,
) -> None:
    """Background task: run Excel audit and notify result."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        from autoresearch.api.dependencies import get_excel_audit_service
        service = get_excel_audit_service()
        result = service.execute(audit_id)

        summary_lines = [
            "📊 Excel 核对完成",
            f"任务号: {result.audit_id}",
            f"状态: {result.status.value}",
            f"检查行数: {result.result.rows_checked}",
            f"差异行数: {result.result.rows_mismatched}",
            f"差异金额: {result.result.mismatch_amount_total:.2f}",
        ]
        if result.artifacts:
            summary_lines.append("")
            summary_lines.append("报告文件:")
            for a in result.artifacts:
                summary_lines.append(f"  - {a}")
        if result.error:
            summary_lines.append(f"错误: {result.error}")

        reply_text = "\n".join(summary_lines)
    except Exception as exc:
        logger.exception("Excel audit background execution failed for %s", audit_id)
        reply_text = f"Excel 核对失败 ({audit_id}): {exc}"

    if notifier.enabled:
        try:
            notifier.send_message(
                chat_id=chat_id,
                text=reply_text,
                message_thread_id=thread_id,
            )
        except Exception:
            logger.exception("Failed to send Excel audit result notification")
