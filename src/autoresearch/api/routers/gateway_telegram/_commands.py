from __future__ import annotations

import inspect
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import BackgroundTasks

from autoresearch.api.settings import load_panel_settings, load_telegram_settings
from autoresearch.core.adapters import CapabilityProviderRegistry
from autoresearch.core.services.approval_store import ApprovalStoreService
from autoresearch.core.services.claude_agents import ClaudeAgentService
from autoresearch.agents.manager_agent import ManagerAgentService
from autoresearch.core.services.github_issue_service import GitHubIssueRead, GitHubIssueService
from autoresearch.core.services.group_access import GroupAccessManager
from autoresearch.core.services.openclaw_compat import OpenClawCompatService
from autoresearch.core.services.openclaw_memory import OpenClawMemoryService
from autoresearch.core.services.panel_access import PanelAccessService
from autoresearch.core.services.telegram_identity import (
    TelegramSessionIdentityRead,
    build_telegram_session_identity,
)
from autoresearch.core.services.telegram_notify import TelegramNotifierService
from autoresearch.core.services.worker_inventory import WorkerInventoryService
from autoresearch.core.services.worker_registry import WorkerRegistryService
from autoresearch.core.services.claude_session_records import ClaudeSessionRecordService
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead, ManagerDispatchRequest
from autoresearch.shared.models import (
    ApprovalDecisionRequest,
    ApprovalRequestCreateRequest,
    ApprovalRisk,
    ApprovalStatus,
    AssistantScope,
    ClaudeAgentCreateRequest,
    ChatType,
    JobStatus,
    OpenClawMemoryRecordCreateRequest,
    OpenClawSessionEventAppendRequest,
    TelegramWebhookAck,
)

from ._extract import (
    _can_telegram_task_self_approve,
    _extract_approve_query,
    _extract_issue_task_parts,
    _extract_memory_content,
    _extract_mode_target,
    _extract_skill_query,
    _is_approve_command,
    _is_help_command,
    _is_memory_command,
    _is_mode_command,
    _is_reset_command,
    _is_skills_command,
    _is_status_query,
    _is_task_command,
    _parse_approve_query,
    _parse_task_command,
    _safe_int,
    _safe_str,
)
from ._messages import (
    _build_agent_result_message,
    _build_approval_decision_message,
    _build_approval_detail_message,
    _build_approval_list_message,
    _build_github_issue_comment_body,
    _build_github_issue_comment_posted_message,
    _build_github_issue_reply_approval_message,
    _build_help_message,
    _build_manager_dispatch_queued_message,
    _build_manager_dispatch_result_message,
    _build_memory_summary_lines,
    _build_skills_catalog_message,
    _build_skill_detail_message,
    _build_status_summary_lines,
    _find_skill_detail,
    _list_skill_providers,
    _truncate_telegram_text,
    _utc_now,
)
from ._session import (
    _build_session_title,
    _build_task_name,
    _ensure_admin_channel_visibility,
    _find_existing_telegram_session,
    _find_or_create_telegram_session,
    _sync_session_runtime_identity,
    _append_user_event,
)


def _execute_agent_and_notify(
    *,
    agent_service: ClaudeAgentService,
    notifier: TelegramNotifierService,
    chat_id: str,
    agent_run_id: str,
    request_payload: ClaudeAgentCreateRequest,
) -> None:
    agent_service.execute(agent_run_id, request_payload)
    if not notifier.enabled:
        return
    run = agent_service.get(agent_run_id)
    if run is None:
        return
    notifier.send_message(chat_id=chat_id, text=_build_agent_result_message(run))


def _execute_manager_dispatch_and_notify(
    *,
    manager_service: ManagerAgentService,
    approval_service: ApprovalStoreService,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    chat_id: str,
    session_id: str,
    approval_uid: str,
    assistant_scope: AssistantScope,
    dispatch_id: str,
    issue_reference: str | None,
    issue_url: str | None,
    issue_title: str | None,
) -> None:
    dispatch: ManagerDispatchRead | None = None
    try:
        dispatch = manager_service.execute_dispatch(dispatch_id)
    except Exception as exc:
        dispatch = manager_service.get_dispatch(dispatch_id)
        error_text = str(exc).strip() or "manager dispatch failed"
        if dispatch is None:
            if notifier.enabled:
                notifier.send_message(
                    chat_id=chat_id,
                    text=_truncate_telegram_text(
                        "\n".join(
                            [
                                "[Manager Task]",
                                f"dispatch: {dispatch_id}",
                                "status: failed",
                                "",
                                error_text,
                            ]
                        )
                    ),
                )
            return
        dispatch = dispatch.model_copy(update={"error": dispatch.error or error_text})

    final_status = dispatch.status
    openclaw_service.append_event(
        session_id=session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"manager dispatch finished: {dispatch.dispatch_id}",
            metadata={
                "source": "telegram_manager_task",
                "dispatch_id": dispatch.dispatch_id,
                "status": final_status.value,
                "issue_reference": issue_reference,
            },
        ),
    )
    openclaw_service.set_status(
        session_id=session_id,
        status=JobStatus.COMPLETED if final_status == JobStatus.COMPLETED else JobStatus.FAILED,
        metadata_updates={"latest_manager_dispatch_status": final_status.value},
    )

    if notifier.enabled:
        notifier.send_message(
            chat_id=chat_id,
            text=_build_manager_dispatch_result_message(
                dispatch,
                issue_reference=issue_reference,
                issue_url=issue_url,
            ),
        )

    if not issue_reference:
        return

    approval = approval_service.create_request(
        ApprovalRequestCreateRequest(
            title=f"Reply to GitHub issue {issue_reference}",
            summary=f"Review and post the automated execution update for {issue_reference}.",
            risk=ApprovalRisk.EXTERNAL,
            source="github_issue_task",
            telegram_uid=approval_uid,
            session_id=session_id,
            assistant_scope=assistant_scope,
            metadata={
                "action_type": "github_issue_comment",
                "issue_reference": issue_reference,
                "issue_url": issue_url,
                "issue_title": issue_title,
                "dispatch_id": dispatch.dispatch_id,
                "comment_body": _build_github_issue_comment_body(
                    dispatch,
                    issue_reference=issue_reference,
                    issue_url=issue_url,
                ),
            },
        )
    )
    openclaw_service.append_event(
        session_id=session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"github issue reply approval queued: {approval.approval_id}",
            metadata={
                "source": "telegram_manager_task",
                "approval_id": approval.approval_id,
                "dispatch_id": dispatch.dispatch_id,
                "issue_reference": issue_reference,
            },
        ),
    )
    if notifier.enabled:
        notifier.send_message(
            chat_id=chat_id,
            text=_build_github_issue_reply_approval_message(
                approval_id=approval.approval_id,
                issue_reference=issue_reference,
                issue_url=issue_url,
            ),
        )


def _post_github_issue_comment_for_approval(
    *,
    approval: Any,
    approval_service: ApprovalStoreService,
    github_issue_service: GitHubIssueService,
    chat_id: str,
    scope: str,
) -> str:
    issue_reference = str(approval.metadata.get("issue_reference") or "").strip()
    comment_body = str(approval.metadata.get("comment_body") or "").strip()
    if not issue_reference or not comment_body:
        raise RuntimeError("approval is missing GitHub issue comment payload")
    output = github_issue_service.post_comment(issue_reference, comment_body)
    approval_service.update_request_metadata(
        approval.approval_id,
        {
            "comment_posted": True,
            "comment_posted_at": _utc_now(),
            "comment_post_result": output,
            "resolved_via_chat_id": chat_id,
            "resolved_scope": scope,
        },
    )
    return output


def _resolve_mini_app_url(
    *,
    magic_link_url: str | None,
    is_group_link: bool,
) -> str | None:
    if is_group_link:
        return None
    configured = (load_panel_settings().mini_app_url or "").strip()
    if configured:
        return configured
    if magic_link_url and magic_link_url.startswith("https://"):
        return magic_link_url
    return None


def _notify_status_magic_link_compat(
    *,
    notifier: TelegramNotifierService,
    chat_id: str,
    summary_lines: list[str],
    magic_link_url: str | None,
    expires_at_iso: str | None,
    is_group_link: bool,
    mini_app_url: str | None,
) -> bool:
    """Call notifier with backward-compatible kwargs for tests/stubs."""
    kwargs: dict[str, Any] = {
        "chat_id": chat_id,
        "summary_lines": summary_lines,
        "magic_link_url": magic_link_url,
        "expires_at_iso": expires_at_iso,
        "mini_app_url": mini_app_url,
    }

    try:
        signature = inspect.signature(notifier.notify_status_magic_link)
    except (TypeError, ValueError):
        signature = None

    if signature and "is_group_link" in signature.parameters:
        kwargs["is_group_link"] = is_group_link

    try:
        return bool(notifier.notify_status_magic_link(**kwargs))
    except TypeError:
        kwargs.pop("is_group_link", None)
        kwargs.pop("mini_app_url", None)
        return bool(notifier.notify_status_magic_link(**kwargs))


def _handle_status_query(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    agent_service: ClaudeAgentService,
    memory_service: OpenClawMemoryService,
    capability_registry: CapabilityProviderRegistry,
    panel_access_service: PanelAccessService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
    worker_registry: WorkerRegistryService,
    worker_inventory: WorkerInventoryService,
) -> TelegramWebhookAck:
    from autoresearch.core.runtime_identity import get_runtime_identity

    runtime_identity = get_runtime_identity()
    session = _find_existing_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
    )
    runs = []
    if session is not None:
        session = _sync_session_runtime_identity(
            openclaw_service=openclaw_service,
            session=session,
            background_tasks=background_tasks,
            notifier=notifier,
            chat_id=chat_id,
        )
        runs = [run for run in agent_service.list() if run.session_id == session.session_id]
        runs.sort(key=lambda item: item.updated_at, reverse=True)
    memory_bundle = memory_service.bundle_for_session(session.session_id) if session is not None else None
    workers = worker_registry.list_workers()
    inventory = worker_inventory.list_workers()

    summary_lines = _build_status_summary_lines(
        chat_id=chat_id,
        session=session,
        runs=runs,
        session_identity=session_identity,
        memory_bundle=memory_bundle,
        capability_registry=capability_registry,
        runtime_identity=runtime_identity,
        workers=workers,
        worker_inventory=inventory,
    )

    # Initialize GroupAccessManager for whitelist groups
    group_access_manager = GroupAccessManager()
    magic_link_url: str | None = None
    expires_at_iso: str | None = None
    is_group_link = False

    # Check if this is an internal group
    try:
        chat_id_int = int(chat_id)
        if group_access_manager.is_internal_group(chat_id_int):
            # Generate group-scoped magic link
            user_id = (
                extracted.get("from_user_id")
                or extracted.get("from_id")
                or update.get("message", {}).get("from", {}).get("id")
            )
            if user_id:
                group_link = group_access_manager.create_group_magic_link(
                    chat_id=chat_id_int,
                    user_id=int(user_id),
                )
                if group_link:
                    magic_link_url = group_link.url
                    expires_at_iso = group_link.expires_at.isoformat()
                    is_group_link = True
    except (ValueError, TypeError):
        pass

    # Fall back to regular magic link if not in whitelist
    if not magic_link_url and panel_access_service.enabled:
        try:
            magic_link = panel_access_service.create_magic_link(chat_id)
            magic_link_url = magic_link.url
            expires_at_iso = magic_link.expires_at.isoformat()
        except (RuntimeError, ValueError, PermissionError):
            magic_link_url = None
            expires_at_iso = None

    mini_app_url = _resolve_mini_app_url(
        magic_link_url=magic_link_url,
        is_group_link=is_group_link,
    )

    if notifier.enabled:
        background_tasks.add_task(
            _notify_status_magic_link_compat,
            notifier=notifier,
            chat_id=chat_id,
            summary_lines=summary_lines,
            magic_link_url=magic_link_url,
            expires_at_iso=expires_at_iso,
            is_group_link=is_group_link,
            mini_app_url=mini_app_url,
        )

    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id if session is not None else None,
        metadata={
            "source": "telegram_status_query",
            "update_type": extracted.get("raw_type"),
            "magic_link_url": magic_link_url,
            "magic_link_expires_at": expires_at_iso,
            "active_runs": len(runs),
            "provider_count": len(capability_registry.list_descriptors()),
            "worker_count": inventory.summary.total_workers,
            "is_group_link": is_group_link,
            "mini_app_url": mini_app_url,
            "scope": session_identity.scope.value,
            "session_key": session_identity.session_key,
        },
    )


def _handle_help_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    background_tasks: BackgroundTasks,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=_build_help_message(session_identity=session_identity),
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        metadata={
            "source": "telegram_help",
            "scope": session_identity.scope.value,
            "chat_type": session_identity.chat_context.chat_type.value,
        },
    )


def _handle_task_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    approval_service: ApprovalStoreService,
    manager_service: ManagerAgentService,
    github_issue_service: GitHubIssueService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    task_query, approval_requested = _parse_task_command(extracted["text"])
    if not task_query:
        message_text = (
            "用法:\n"
            "/task <需求>\n"
            "/task --approve <需求>\n"
            "/task issue <owner/repo#123 | #123 | GitHub issue URL> [补充说明]"
        )
        if notifier.enabled:
            background_tasks.add_task(notifier.send_message, chat_id=chat_id, text=message_text)
        return TelegramWebhookAck(
            accepted=False,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            reason="missing task payload",
            metadata={"source": "telegram_manager_task", "scope": session_identity.scope.value},
        )

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
        text=extracted["text"],
        update=update,
        extracted=extracted,
        session_identity=session_identity,
    )

    issue: GitHubIssueRead | None = None
    manager_prompt = task_query
    task_source = "prompt"
    operator_note = ""
    issue_reference: str | None = None
    issue_url: str | None = None
    approval_granted = approval_requested and _can_telegram_task_self_approve(
        session_identity=session_identity
    )

    if approval_requested and not approval_granted and notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text="`--approve` 仅对 owner/partner 生效；本次仍按常规审批流执行。",
        )

    if task_query.casefold().startswith("issue "):
        issue_reference, operator_note = _extract_issue_task_parts(task_query)
        try:
            issue = github_issue_service.fetch_issue(issue_reference)
        except Exception as exc:
            return TelegramWebhookAck(
                accepted=False,
                update_id=_safe_int(update.get("update_id")),
                chat_id=chat_id,
                session_id=session.session_id,
                reason=str(exc),
                metadata={
                    "source": "telegram_manager_task",
                    "task_source": "issue",
                    "scope": session_identity.scope.value,
                },
            )
        manager_prompt = github_issue_service.build_manager_prompt(issue, operator_note=operator_note or None)
        task_source = "issue"
        issue_reference = issue.reference.display
        issue_url = issue.url

    dispatch = manager_service.create_dispatch(
        ManagerDispatchRequest(
            prompt=manager_prompt,
            approval_granted=approval_granted,
            auto_dispatch=True,
            metadata={
                "source": "telegram_manager_task",
                "task_source": task_source,
                "telegram_chat_id": chat_id,
                "telegram_user_id": session_identity.actor.user_id,
                "telegram_session_id": session.session_id,
                "telegram_scope": session_identity.scope.value,
                "raw_task_query": task_query,
                "operator_note": operator_note,
                "github_issue_reference": issue_reference,
                "github_issue_url": issue_url,
                "github_issue_title": issue.title if issue is not None else None,
                "approval_requested": approval_requested,
                "approval_granted": approval_granted,
                "approval_source": "telegram_task_flag" if approval_granted else None,
            },
        )
    )
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"manager dispatch queued: {dispatch.dispatch_id}",
            metadata={
                "source": "telegram_manager_task",
                "dispatch_id": dispatch.dispatch_id,
                "task_source": task_source,
                "issue_reference": issue_reference,
            },
        ),
    )
    openclaw_service.set_status(
        session_id=session.session_id,
        status=JobStatus.QUEUED,
        metadata_updates={"latest_manager_dispatch_id": dispatch.dispatch_id},
    )

    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=_build_manager_dispatch_queued_message(dispatch, issue_reference=issue_reference),
        )

    background_tasks.add_task(
        _execute_manager_dispatch_and_notify,
        manager_service=manager_service,
        approval_service=approval_service,
        openclaw_service=openclaw_service,
        notifier=notifier,
        chat_id=chat_id,
        session_id=session.session_id,
        approval_uid=session_identity.actor.user_id or chat_id,
        assistant_scope=session_identity.scope,
        dispatch_id=dispatch.dispatch_id,
        issue_reference=issue_reference,
        issue_url=issue_url,
        issue_title=issue.title if issue is not None else None,
    )

    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            "source": "telegram_manager_task",
            "dispatch_id": dispatch.dispatch_id,
            "task_source": task_source,
            "issue_reference": issue_reference,
            "issue_url": issue_url,
            "scope": session_identity.scope.value,
        },
    )


def _handle_approve_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    approval_service: ApprovalStoreService,
    github_issue_service: GitHubIssueService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    approval_query = _extract_approve_query(extracted["text"])
    approval_id, approval_action, approval_note = _parse_approve_query(approval_query)
    approval_uid = session_identity.actor.user_id or chat_id
    message_source = "telegram_approve_query"
    if approval_action is not None and approval_id:
        approval = approval_service.get_request(approval_id)
        if approval is None or approval.telegram_uid != approval_uid:
            message_text = f"未找到 approval: {approval_id}"
        else:
            decision = "approved" if approval_action == "approve" else "rejected"
            try:
                approval = approval_service.resolve_request(
                    approval.approval_id,
                    ApprovalDecisionRequest(
                        decision=decision,
                        decided_by=approval_uid,
                        note=approval_note or None,
                        metadata={
                            "resolved_via": "telegram_command",
                            "chat_id": chat_id,
                            "scope": session_identity.scope.value,
                        },
                    ),
                )
                message_text = _build_approval_decision_message(approval)
                message_source = "telegram_approve_decision"
                approval_query = approval.approval_id
                if decision == "approved" and approval.metadata.get("action_type") == "github_issue_comment":
                    comment_output = _post_github_issue_comment_for_approval(
                        approval=approval,
                        approval_service=approval_service,
                        github_issue_service=github_issue_service,
                        chat_id=chat_id,
                        scope=session_identity.scope.value,
                    )
                    message_text = "\n\n".join(
                        [
                            message_text,
                            _build_github_issue_comment_posted_message(
                                approval_id=approval.approval_id,
                                issue_reference=str(approval.metadata.get("issue_reference") or "unknown"),
                                output=comment_output or None,
                            ),
                        ]
                    ).strip()
            except ValueError as exc:
                message_text = str(exc)
                message_source = "telegram_approve_decision"
            except RuntimeError as exc:
                message_text = "\n\n".join(
                    [
                        _build_approval_decision_message(approval),
                        f"[GitHub Reply Failed]\n{str(exc).strip()}",
                    ]
                ).strip()
                message_source = "telegram_approve_decision"
    elif approval_id:
        approval = approval_service.get_request(approval_id)
        if approval is None or approval.telegram_uid != approval_uid:
            message_text = f"未找到 approval: {approval_id}"
        else:
            approval_query = approval.approval_id
            message_text = _build_approval_detail_message(approval)
    else:
        approvals = approval_service.list_requests(
            status=ApprovalStatus.PENDING,
            telegram_uid=approval_uid,
            limit=10,
        )
        message_text = _build_approval_list_message(approvals)

    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=message_text,
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        metadata={
            "source": message_source,
            "approval_id": approval_query or None,
            "decision": approval_action or None,
            "scope": session_identity.scope.value,
        },
    )


def _handle_mode_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    from autoresearch.shared.models import OpenClawSessionCreateRequest

    target_scope = _extract_mode_target(extracted["text"])
    chat_type = session_identity.chat_context.chat_type

    if chat_type != ChatType.PRIVATE:
        message_text = f"当前 chat_type={chat_type.value}，群组或频道固定为 shared 模式。"
        if notifier.enabled:
            background_tasks.add_task(notifier.send_message, chat_id=chat_id, text=message_text)
        return TelegramWebhookAck(
            accepted=True,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            metadata={
                "source": "telegram_mode_query",
                "scope": session_identity.scope.value,
                "chat_type": chat_type.value,
                "switch_allowed": False,
            },
        )

    if target_scope is None:
        message_text = (
            f"当前模式: {session_identity.scope.value}\n"
            "用法:\n"
            "- /mode personal\n"
            "- /mode shared"
        )
        if notifier.enabled:
            background_tasks.add_task(notifier.send_message, chat_id=chat_id, text=message_text)
        return TelegramWebhookAck(
            accepted=True,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            metadata={
                "source": "telegram_mode_query",
                "scope": session_identity.scope.value,
                "switch_allowed": True,
            },
        )

    target_identity = build_telegram_session_identity(
        extracted,
        load_telegram_settings(),
        scope_override=target_scope,
    )
    session = _find_or_create_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=target_identity,
        background_tasks=background_tasks,
        notifier=notifier,
    )
    session = openclaw_service.update_metadata(
        session.session_id,
        {
            "telegram_mode_preference": target_scope.value,
            "mode_switched_at": _utc_now(),
            "mode_switched_from": session_identity.scope.value,
        },
    )
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"mode selected: {target_scope.value}",
            metadata={
                "source": "telegram_mode_command",
                "scope": target_scope.value,
                "previous_scope": session_identity.scope.value,
            },
        ),
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=(
                f"模式已切换到 {target_scope.value}。\n"
                f"session: {session.session_id}\n"
                f"session_key: {session.session_key}"
            ),
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            "source": "telegram_mode_switch",
            "scope": session.scope.value,
            "session_key": session.session_key,
            "assistant_id": session.assistant_id,
        },
    )


def _handle_skills_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    notifier: TelegramNotifierService,
    capability_registry: CapabilityProviderRegistry,
) -> TelegramWebhookAck:
    skill_query = _extract_skill_query(extracted["text"])
    skill_providers = _list_skill_providers(capability_registry)
    catalogs = [(provider_id, provider.list_skills()) for provider_id, provider in skill_providers]
    total_skills = sum(len(catalog.skills) for _, catalog in catalogs)

    if skill_query:
        detail = _find_skill_detail(skill_query=skill_query, skill_providers=skill_providers)
        if detail is None:
            message_text = f"未找到 skill: {skill_query}"
        else:
            message_text = _build_skill_detail_message(provider_id=detail[0], skill=detail[1])
    else:
        message_text = _build_skills_catalog_message(catalogs)

    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=message_text,
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        metadata={
            "source": "telegram_skills_query",
            "skill_query": skill_query or None,
            "skill_provider_count": len(skill_providers),
            "skill_count": total_skills,
        },
    )


def _handle_reset_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    from autoresearch.shared.models import OpenClawSessionCreateRequest

    existing_session = _find_existing_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
    )

    previous_session_id: str | None = None
    if existing_session is not None:
        previous_session_id = existing_session.session_id
        existing_metadata = dict(existing_session.metadata)
        existing_metadata.update(
            {
                "reset_at": _utc_now(),
                "reset_source": "telegram_command",
                "archived_session_key": existing_session.session_key,
            }
        )
        archived_session_key = (
            f"{existing_session.session_key}#archived:{int(time.time())}"
            if existing_session.session_key
            else None
        )
        archived_session = existing_session.model_copy(
            update={
                "session_key": archived_session_key,
                "status": JobStatus.INTERRUPTED,
                "updated_at": datetime.now(timezone.utc),
                "metadata": existing_metadata,
            }
        )
        openclaw_service.save_session(archived_session)

    session = openclaw_service.create_session(
        OpenClawSessionCreateRequest(
            channel="telegram",
            external_id=chat_id,
            title=_build_session_title(chat_id=chat_id, session_identity=session_identity),
            scope=session_identity.scope,
            session_key=session_identity.session_key,
            assistant_id=session_identity.assistant_id,
            actor=session_identity.actor,
            chat_context=session_identity.chat_context,
            metadata={
                "source": "telegram_reset",
                "created_at": _utc_now(),
                "reset_from_session_id": previous_session_id,
                "scope": session_identity.scope.value,
                "session_key": session_identity.session_key,
                "assistant_id": session_identity.assistant_id,
                "chat_type": session_identity.chat_context.chat_type.value,
                "actor_role": session_identity.actor.role.value,
                "actor_user_id": session_identity.actor.user_id,
                "telegram_mode_preference": session_identity.scope.value,
            },
        )
    )
    session = _sync_session_runtime_identity(
        openclaw_service=openclaw_service,
        session=session,
        background_tasks=background_tasks,
        notifier=notifier,
        chat_id=chat_id,
    )
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content="session reset via telegram",
            metadata={
                "source": "telegram_reset",
                "previous_session_id": previous_session_id,
            },
        ),
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=(
                f"会话已重置。\nnew_session: {session.session_id}"
                + (f"\nprevious_session: {previous_session_id}" if previous_session_id else "")
            ),
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            "source": "telegram_reset",
            "previous_session_id": previous_session_id,
            "scope": session.scope.value,
            "session_key": session.session_key,
        },
    )


def _handle_memory_command(
    *,
    chat_id: str,
    update: dict[str, Any],
    extracted: dict[str, Any],
    background_tasks: BackgroundTasks,
    openclaw_service: OpenClawCompatService,
    memory_service: OpenClawMemoryService,
    notifier: TelegramNotifierService,
    session_identity: TelegramSessionIdentityRead,
) -> TelegramWebhookAck:
    session = _find_or_create_telegram_session(
        openclaw_service=openclaw_service,
        chat_id=chat_id,
        session_identity=session_identity,
        background_tasks=background_tasks,
        notifier=notifier,
    )
    memory_content = _extract_memory_content(extracted["text"])
    if not memory_content:
        bundle = memory_service.bundle_for_session(session.session_id)
        if notifier.enabled:
            background_tasks.add_task(
                notifier.send_message,
                chat_id=chat_id,
                text="\n".join(_build_memory_summary_lines(bundle)),
            )
        return TelegramWebhookAck(
            accepted=True,
            update_id=_safe_int(update.get("update_id")),
            chat_id=chat_id,
            session_id=session.session_id,
            metadata={
                "source": "telegram_memory_summary",
                "scope": session.scope.value,
                "session_key": session.session_key,
                "personal_memory_count": len(bundle.personal_memories),
                "shared_memory_count": len(bundle.shared_memories),
            },
        )

    record = memory_service.remember_for_session(
        session.session_id,
        OpenClawMemoryRecordCreateRequest(
            content=memory_content,
            source="telegram_explicit_memory",
            metadata={
                "chat_id": chat_id,
                "update_id": _safe_int(update.get("update_id")),
                "message_id": extracted.get("message_id"),
                "chat_type": session_identity.chat_context.chat_type.value,
            },
        ),
    )
    openclaw_service.append_event(
        session_id=session.session_id,
        request=OpenClawSessionEventAppendRequest(
            role="status",
            content=f"memory stored: {record.scope.value}",
            metadata={
                "memory_id": record.memory_id,
                "scope": record.scope.value,
                "source": record.source,
            },
        ),
    )
    if notifier.enabled:
        background_tasks.add_task(
            notifier.send_message,
            chat_id=chat_id,
            text=f"记忆已保存到 {record.scope.value}: {record.memory_id}",
        )
    return TelegramWebhookAck(
        accepted=True,
        update_id=_safe_int(update.get("update_id")),
        chat_id=chat_id,
        session_id=session.session_id,
        metadata={
            "source": "telegram_memory_store",
            "memory_id": record.memory_id,
            "scope": record.scope.value,
            "session_key": session.session_key,
        },
    )
