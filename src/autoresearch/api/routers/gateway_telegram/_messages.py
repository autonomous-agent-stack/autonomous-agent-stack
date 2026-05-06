from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autoresearch.control_plane.contracts import (
    ControlPlaneApprovalRead,
    ControlPlaneApprovalStatus,
    ControlPlaneTaskRead,
    ControlPlaneTaskStatus,
)
from autoresearch.core.adapters import CapabilityDomain, CapabilityProviderRegistry, SkillProvider
from autoresearch.core.services.telegram_completion_format import format_butler_queue_ack_message
from autoresearch.core.services.telegram_identity import TelegramSessionIdentityRead
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead
from autoresearch.shared.models import (
    ApprovalStatus,
    ChatType,
    JobStatus,
    OpenClawMemoryBundleRead,
    OpenClawSessionRead,
    WorkerMode,
)


def _build_agent_result_message(run: Any) -> str:
    status_value = run.status.value
    lines = [
        f"[任务结果] {run.task_name}",
        f"状态: {status_value}",
        f"run: {run.agent_run_id}",
    ]
    if status_value == "completed":
        output = (run.stdout_preview or "").strip()
        if output:
            lines.extend(["", "输出:", output])
        else:
            lines.extend(["", "输出为空。"])
    else:
        err = (run.error or run.stderr_preview or "unknown error").strip()
        lines.extend(["", "错误:", err])

    text = "\n".join(lines).strip()
    # Telegram text message hard limit is 4096 chars.
    if len(text) > 3900:
        return text[:3900] + "\n...[truncated]"
    return text


def _build_help_message(*, session_identity: TelegramSessionIdentityRead) -> str:
    chat_type = session_identity.chat_context.chat_type
    lines = [
        "[Telegram Commands]",
        "/start 查看欢迎信息和命令列表",
        "/status 查看当前会话、任务和能力摘要",
        "/task <需求> 走 Manager Agent DAG 执行任务",
        "/task --approve <需求> owner/partner 直通 Draft PR 审批上下文",
        "/task issue <issue_ref> [补充说明] 读取 GitHub issue 后派发修复",
        "/approve 查看待审批列表",
        "/approve <approval_id> 查看待审批详情",
        "/approve <approval_id> approve [备注] 批准待审批事项",
        "/approve <approval_id> reject [备注] 拒绝待审批事项",
        "/memory 查看长期记忆摘要",
        "/memory <内容> 写入长期记忆",
        "/skills 查看可用 skills",
        "/skills <skill_key> 查看 skill 详情",
        "/cancel [run_id|task_id] 取消最近或指定任务 / cancel latest or selected task",
        "/retry [run_id|task_id] 重试最近或指定失败任务 / retry latest or selected failed task",
        "/force-fail [run_id|task_id] owner 强制失败 v2 任务 / owner-only force-fail for v2 tasks",
        "/reset 重置当前会话",
    ]
    if chat_type == ChatType.PRIVATE:
        lines.extend(
            [
                "/mode 查看当前模式",
                "/mode personal 切到 personal",
                "/mode shared 切到 shared",
            ]
        )
    else:
        lines.append("/mode 群组固定为 shared，仅用于查看说明")
    lines.append("/help 查看本帮助")
    return "\n".join(lines)


def _build_manager_dispatch_queued_message(
    dispatch: ManagerDispatchRead,
    *,
    issue_reference: str | None,
) -> str:
    task_count = len(dispatch.execution_plan.tasks) if dispatch.execution_plan is not None else 0
    lines = [
        "[Manager Task]",
        f"dispatch: {dispatch.dispatch_id}",
        f"strategy: {dispatch.execution_plan.strategy.value if dispatch.execution_plan is not None else 'single_task'}",
        f"tasks: {task_count}",
    ]
    if issue_reference:
        lines.append(f"issue: {issue_reference}")
    lines.append("已接收，开始拆解并执行。")
    return _truncate_telegram_text("\n".join(lines))


def _build_manager_dispatch_result_message(
    dispatch: ManagerDispatchRead,
    *,
    issue_reference: str | None,
    issue_url: str | None,
) -> str:
    task_count = len(dispatch.execution_plan.tasks) if dispatch.execution_plan is not None else 0
    completed_count = (
        sum(1 for item in dispatch.execution_plan.tasks if item.status == JobStatus.COMPLETED)
        if dispatch.execution_plan is not None
        else 0
    )
    lines = [
        "[Manager Task]",
        f"dispatch: {dispatch.dispatch_id}",
        f"status: {dispatch.status.value}",
        f"tasks: {completed_count}/{task_count}",
    ]
    if issue_reference:
        lines.append(f"issue: {issue_reference}")
    if issue_url:
        lines.append(f"url: {issue_url}")
    if dispatch.summary:
        lines.extend(["", dispatch.summary])

    promotion = dispatch.run_summary.promotion if dispatch.run_summary is not None else None
    if promotion is not None and promotion.pr_url:
        lines.append(f"draft_pr: {promotion.pr_url}")
    elif dispatch.run_summary is not None and dispatch.run_summary.promotion_patch_uri:
        lines.append(f"patch: {dispatch.run_summary.promotion_patch_uri}")

    error_text = (
        dispatch.error
        or (
            dispatch.run_summary.driver_result.error
            if dispatch.run_summary is not None and dispatch.run_summary.driver_result.error
            else None
        )
    )
    if error_text:
        lines.extend(["", "error:", error_text.strip()])
    return _truncate_telegram_text("\n".join(lines))


def _build_github_issue_comment_body(
    dispatch: ManagerDispatchRead,
    *,
    issue_reference: str,
    issue_url: str | None,
) -> str:
    lines = [
        "Automated progress update from the local autonomous agent stack.",
        "",
        f"- Issue: {issue_reference}",
        f"- Dispatch: {dispatch.dispatch_id}",
        f"- Status: {dispatch.status.value}",
    ]
    if issue_url:
        lines.append(f"- Issue URL: {issue_url}")
    if dispatch.summary:
        lines.append(f"- Summary: {dispatch.summary}")
    promotion = dispatch.run_summary.promotion if dispatch.run_summary is not None else None
    if promotion is not None and promotion.pr_url:
        lines.append(f"- Draft PR: {promotion.pr_url}")
    error_text = (
        dispatch.error
        or (
            dispatch.run_summary.driver_result.error
            if dispatch.run_summary is not None and dispatch.run_summary.driver_result.error
            else None
        )
    )
    if error_text:
        lines.append(f"- Error: {error_text.strip()}")
    lines.extend(
        [
            "",
            "This update was prepared automatically from Telegram `/task issue` and still expects human review before merge.",
        ]
    )
    return "\n".join(lines).strip()


def _build_github_issue_reply_approval_message(
    *,
    approval_id: str,
    issue_reference: str,
    issue_url: str | None,
) -> str:
    lines = [
        "[GitHub Reply Pending]",
        f"approval: {approval_id}",
        f"issue: {issue_reference}",
    ]
    if issue_url:
        lines.append(f"url: {issue_url}")
    lines.extend(
        [
            "",
            f"/approve {approval_id} approve  发布执行结果到 GitHub issue",
            f"/approve {approval_id} reject  保留结果，仅在 Telegram 查看",
        ]
    )
    return _truncate_telegram_text("\n".join(lines))


def _build_github_issue_comment_posted_message(
    *,
    approval_id: str,
    issue_reference: str,
    output: str | None,
) -> str:
    lines = [
        "[GitHub Reply Posted]",
        f"approval: {approval_id}",
        f"issue: {issue_reference}",
    ]
    if output:
        lines.extend(["", output.strip()])
    return _truncate_telegram_text("\n".join(lines))


def _truncate_telegram_text(text: str) -> str:
    normalized = text.strip()
    if len(normalized) > 3900:
        return normalized[:3900] + "\n...[truncated]"
    return normalized


def _telegram_md_cell(value: str, *, max_len: int = 120) -> str:
    """Plain-text Markdown-ish tables for Telegram (no parse_mode); keep cells on one line."""
    text = str(value).replace("|", "/").replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[: max(1, max_len - 1)] + "…"


def _telegram_two_column_table(rows: list[tuple[str, str]]) -> list[str]:
    if not rows:
        return []
    lines = ["| 项 | 值 |", "| --- | --- |"]
    for key, val in rows:
        lines.append(f"| {_telegram_md_cell(key, max_len=40)} | {_telegram_md_cell(val)} |")
    return lines


def _telegram_queue_ack_message(
    *,
    task_name: str,
    run_id: str,
    worker_brand: str,
    runtime_id: str | None = None,
    agent_name: str | None = None,
    agent_names: list[str] | None = None,
) -> str:
    return format_butler_queue_ack_message(
        task_name=task_name,
        run_id=run_id,
        worker_brand=worker_brand,
        runtime_id=runtime_id,
        primary_agent=agent_name,
        agent_names=agent_names,
    )


def _build_status_summary_lines(
    *,
    chat_id: str,
    session: OpenClawSessionRead | None,
    runs: list[Any],
    session_identity: TelegramSessionIdentityRead,
    memory_bundle: OpenClawMemoryBundleRead | None,
    capability_registry: CapabilityProviderRegistry,
    runtime_identity: dict[str, str],
    workers: list[Any],
    worker_inventory,
) -> list[str]:
    runtime_display = runtime_identity["runtime_display"]
    if session is None:
        lines = [
            "会话 / Session：暂无历史会话 / no history yet",
            f"范围 / Scope：{session_identity.scope.value}",
            f"运行 / Runtime：{runtime_display}",
        ]
        _append_worker_inventory_lines(lines, worker_inventory)
        return lines

    runtime_display = str(session.metadata.get("runtime_display") or runtime_display)
    effective_session_status = _effective_session_status(
        session=session,
        runs=runs,
        worker_inventory=worker_inventory,
        session_key=session.session_key or session_identity.session_key,
    )
    active_worker_runs = sum(int(getattr(worker, "active_tasks", 0) or 0) for worker in getattr(worker_inventory, "workers", []) or [])
    active_runs = sum(1 for run in runs if run.status.value in {"queued", "running"}) + active_worker_runs
    lines = [
        f"会话 / Session：{_status_text(effective_session_status)}；运行中 {active_runs} 个 / active {active_runs}",
        f"范围 / Scope：{session.scope.value}",
        f"运行 / Runtime：{runtime_display}",
    ]
    previous_runtime = str(session.metadata.get("runtime_previous_display") or "").strip()
    switched_at = str(session.metadata.get("runtime_switched_at") or "").strip()
    if previous_runtime and switched_at:
        lines.append(f"切换 / Switched：{previous_runtime} -> {runtime_display}")
    _append_worker_inventory_lines(lines, worker_inventory)
    worker_recent = _worker_recent_task_lines(
        worker_inventory,
        session_key=session.session_key or session_identity.session_key,
    )
    worker_latest_at = _worker_latest_updated_at(
        worker_inventory,
        session_key=session.session_key or session_identity.session_key,
    )
    agent_recent = [
        f"- {_status_text(run.status.value)} · {_truncate_inline(str(run.task_name or '未命名任务'), limit=52)}"
        for run in runs
        if not _agent_run_shadowed_by_worker_success(run, worker_latest_at)
    ]
    recent_lines = (worker_recent + agent_recent)[:5]
    if not recent_lines:
        lines.append("最近任务 / Recent：暂无 / none")
        return lines

    lines.append("最近任务 / Recent:")
    lines.extend(recent_lines)
    return lines


def _effective_session_status(
    *,
    session: OpenClawSessionRead,
    runs: list[Any],
    worker_inventory,
    session_key: str,
) -> str:
    latest = _worker_latest_summary(worker_inventory, session_key=session_key)
    if latest is None:
        return session.status.value
    worker_updated_at = getattr(latest, "updated_at", None)
    agent_updated_at = _latest_agent_updated_at(runs)
    if _datetime_lt(worker_updated_at, agent_updated_at):
        return session.status.value
    status = getattr(getattr(latest, "status", None), "value", getattr(latest, "status", ""))
    if status == JobStatus.COMPLETED.value:
        return "succeeded"
    if status in {JobStatus.QUEUED.value, JobStatus.RUNNING.value}:
        return "running"
    if status == JobStatus.CANCELLED.value:
        return "cancelled"
    if status == JobStatus.FAILED.value:
        return "failed"
    return session.status.value


def _worker_recent_task_lines(worker_inventory, *, session_key: str) -> list[str]:
    summaries = _worker_latest_summaries(worker_inventory, session_key=session_key)
    lines: list[str] = []
    for _worker_id, latest in summaries[:3]:
        status = getattr(getattr(latest, "status", None), "value", getattr(latest, "status", "unknown"))
        suffix = _worker_delivery_suffix(latest)
        lines.append(f"- {_status_text(status)} · {_compact_task_name(latest)}{suffix}")
    return lines


def _worker_latest_updated_at(worker_inventory, *, session_key: str):
    latest = _worker_latest_summary(worker_inventory, session_key=session_key)
    return getattr(latest, "updated_at", None) if latest is not None else None


def _worker_latest_summary(worker_inventory, *, session_key: str):
    summaries = _worker_latest_summaries(worker_inventory, session_key=session_key)
    return summaries[0][1] if summaries else None


def _worker_latest_summaries(worker_inventory, *, session_key: str) -> list[tuple[str, Any]]:
    workers = list(getattr(worker_inventory, "workers", []) or [])
    summaries: list[tuple[str, Any]] = []
    for worker in workers:
        latest = getattr(worker, "latest_task_summary", None)
        if latest is None:
            continue
        metadata = getattr(latest, "metadata", {}) or {}
        latest_session_key = str(metadata.get("session_key") or "").strip()
        if latest_session_key and latest_session_key != session_key:
            continue
        summaries.append((str(getattr(worker, "worker_id", "worker")), latest))
    return sorted(
        summaries,
        key=lambda item: (_datetime_sort_key(getattr(item[1], "updated_at", None)), item[1].run_id),
        reverse=True,
    )


def _agent_run_shadowed_by_worker_success(run: Any, worker_latest_at: Any) -> bool:
    if worker_latest_at is None:
        return False
    status = getattr(getattr(run, "status", None), "value", getattr(run, "status", ""))
    if status != "failed":
        return False
    task_name = str(getattr(run, "task_name", "") or "").strip().lower()
    if "hermes recovery" not in task_name and task_name != "telegram_hermes":
        return False
    return _datetime_lte(getattr(run, "updated_at", None), worker_latest_at)


def _latest_agent_updated_at(runs: list[Any]):
    values = [getattr(run, "updated_at", None) for run in runs if getattr(run, "updated_at", None) is not None]
    if not values:
        return None
    return max(values)


def _datetime_lt(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    try:
        return left < right
    except TypeError:
        if isinstance(left, datetime) and isinstance(right, datetime):
            return left.replace(tzinfo=None) < right.replace(tzinfo=None)
        return False


def _datetime_lte(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return False
    try:
        return left <= right
    except TypeError:
        if isinstance(left, datetime) and isinstance(right, datetime):
            return left.replace(tzinfo=None) <= right.replace(tzinfo=None)
        return False


def _datetime_sort_key(value: Any) -> float:
    if isinstance(value, datetime):
        normalized = value
        if value.tzinfo is None:
            normalized = value.replace(tzinfo=timezone.utc)
        return normalized.timestamp()
    return 0.0


def _append_worker_summary_lines(lines: list[str], workers: list[Any]) -> None:
    online_workers = [
        worker
        for worker in workers
        if not getattr(worker, "is_stale", False)
        and getattr(getattr(worker, "mode", None), "value", getattr(worker, "mode", None)) != WorkerMode.OFFLINE.value
    ]
    lines.append(f"workers_online: {len(online_workers)}")
    for worker in online_workers[:3]:
        metadata = getattr(worker, "metadata", {}) or {}
        host = getattr(worker, "host", None) or str(metadata.get("runtime_host_short") or metadata.get("runtime_host") or "unknown")
        worker_type = getattr(getattr(worker, "worker_type", None), "value", getattr(worker, "worker_type", "unknown"))
        mode = getattr(getattr(worker, "mode", None), "value", getattr(worker, "mode", "unknown"))
        health = getattr(getattr(worker, "health", None), "value", getattr(worker, "health", "unknown"))
        lines.append(f"- worker {worker.worker_id} | {worker_type}/{mode} | {host} | {health}")


def _append_worker_inventory_lines(lines: list[str], inventory) -> None:
    summary = getattr(inventory, "summary", None)
    workers = list(getattr(inventory, "workers", []) or [])
    if summary is None:
        return
    lines.append(
        "Worker："
        f"{summary.online_workers} 在线，{summary.busy_workers} 忙碌，"
        f"{summary.degraded_workers} 异常，{summary.offline_workers} 离线"
        " / "
        f"{summary.online_workers} online, {summary.busy_workers} busy, "
        f"{summary.degraded_workers} degraded, {summary.offline_workers} offline"
    )
    nonactive_agents = []
    summary_metadata = getattr(summary, "metadata", {}) or {}
    if isinstance(summary_metadata, dict):
        raw_nonactive = summary_metadata.get("butler_agents_nonactive") or []
        if isinstance(raw_nonactive, list):
            nonactive_agents = [item for item in raw_nonactive if isinstance(item, dict)]
    if nonactive_agents:
        lines.append("暂停 agents / Paused agents:")
        for agent in nonactive_agents[:8]:
            name = str(agent.get("agent_name") or "").strip() or "unknown"
            state = str(agent.get("status") or "").strip() or "unknown"
            reason = str(agent.get("reason") or "").strip()
            suffix = f"，原因 {reason}" if reason else ""
            lines.append(f"- {name}：{state}{suffix}")
    if not workers:
        lines.append("- 当前没有已注册 worker / no registered workers")
        return
    notable = [
        worker
        for worker in workers
        if worker.display_status != "online" or int(getattr(worker, "active_tasks", 0) or 0) > 0
    ]
    for worker in notable[:3]:
        lines.append(
            f"- {worker.worker_id}：{worker.display_status}，队列 {worker.queue_depth}，活跃 {worker.active_tasks}"
        )


def _compact_task_name(latest: Any) -> str:
    metadata = latest.metadata if isinstance(getattr(latest, "metadata", None), dict) else {}
    for key in ("display_task_name", "telegram_original_text"):
        text = " ".join(str(metadata.get(key) or "").split())
        if text:
            return _truncate_inline(text, limit=52)
    text = " ".join(str(getattr(latest, "task_name", "") or "").split())
    marker = "追问 / Follow-up:"
    index = text.rfind(marker)
    if index >= 0:
        followup = " ".join(text[index + len(marker) :].split())
        if followup:
            text = followup
    return _truncate_inline(text or "未命名任务", limit=52)


def _worker_delivery_suffix(latest: Any) -> str:
    status = getattr(getattr(latest, "status", None), "value", getattr(latest, "status", ""))
    if status != JobStatus.COMPLETED.value:
        return ""
    metadata = latest.metadata if isinstance(getattr(latest, "metadata", None), dict) else {}
    metrics = latest.metrics if isinstance(getattr(latest, "metrics", None), dict) else {}
    notify_state = str(metrics.get("telegram_notify_status") or "").strip().lower()
    if metadata.get("telegram_butler_primary_sent") or metadata.get("telegram_butler_fallback_sent"):
        return ""
    if notify_state in {"sent", "edited", "delivered"}:
        return ""
    if notify_state == "deferred":
        return "（等待下游结果 / waiting for downstream result）"
    return "（结果投递未确认 / delivery unconfirmed）"


def _status_text(status: str) -> str:
    normalized = str(status or "").strip().lower()
    return {
        "queued": "已入队",
        "running": "运行中",
        "completed": "已完成",
        "succeeded": "已完成",
        "failed": "失败",
        "interrupted": "中断",
        "cancelled": "已取消",
        "canceled": "已取消",
        "cancel_requested": "取消中",
    }.get(normalized, normalized or "未知")


def _truncate_inline(text: str, *, limit: int) -> str:
    normalized = " ".join(str(text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(1, limit - 1)].rstrip() + "…"


def _status_diag_value(
    latest: Any,
    keys: tuple[str, ...],
    *,
    default: str,
) -> str:
    metrics = latest.metrics if isinstance(getattr(latest, "metrics", None), dict) else {}
    metadata = latest.metadata if isinstance(getattr(latest, "metadata", None), dict) else {}
    result = latest.result if isinstance(getattr(latest, "result", None), dict) else {}
    for key in keys:
        for bag in (metrics, metadata, result):
            value = bag.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
    return default


def _list_skill_providers(
    capability_registry: CapabilityProviderRegistry,
) -> list[tuple[str, SkillProvider]]:
    providers: list[tuple[str, SkillProvider]] = []
    for descriptor in capability_registry.list_descriptors(domain=CapabilityDomain.SKILL):
        provider = capability_registry.get(descriptor.provider_id)
        if provider is not None and isinstance(provider, SkillProvider):
            providers.append((descriptor.provider_id, provider))
    return providers


def _find_skill_detail(
    *,
    skill_query: str,
    skill_providers: list[tuple[str, SkillProvider]],
):
    normalized = skill_query.strip().lower()
    if not normalized:
        return None
    for provider_id, provider in skill_providers:
        detail = provider.get_skill(skill_query)
        if detail is not None:
            return provider_id, detail
        catalog = provider.list_skills()
        for skill in catalog.skills:
            if skill.skill_key.lower() == normalized or skill.name.lower() == normalized:
                detail = provider.get_skill(skill.skill_key) or provider.get_skill(skill.name)
                if detail is not None:
                    return provider_id, detail
    return None


def _build_skills_catalog_message(catalogs: list[tuple[str, Any]]) -> str:
    skill_lines: list[str] = []
    total_skills = 0
    for provider_id, catalog in catalogs:
        skill_count = len(catalog.skills)
        total_skills += skill_count
        skill_lines.append(f"[{provider_id}] {skill_count} skills")
        for skill in catalog.skills[:8]:
            skill_lines.append(f"- {skill.skill_key} | {skill.name}")
    if not skill_lines:
        return "当前没有可用 skills。"
    lines = [
        "[Skills]",
        f"providers: {len(catalogs)}",
        f"total_skills: {total_skills}",
        "",
        *skill_lines[:30],
        "",
        "发送 /skills <skill_key> 查看详情。",
    ]
    return "\n".join(lines).strip()


def _build_skill_detail_message(*, provider_id: str, skill: Any) -> str:
    lines = [
        "[Skill Detail]",
        f"provider: {provider_id}",
        f"name: {skill.name}",
        f"skill_key: {skill.skill_key}",
        f"source: {skill.source}",
        f"file: {skill.file_path}",
    ]
    if skill.description:
        lines.append(f"description: {skill.description}")
    content = (getattr(skill, "content", "") or "").strip()
    if content:
        preview = content[:1200]
        if len(content) > 1200:
            preview += "\n...[truncated]"
        lines.extend(["", preview])
    return "\n".join(lines).strip()


def _build_memory_summary_lines(bundle: OpenClawMemoryBundleRead) -> list[str]:
    lines = [
        f"session: {bundle.session_id}",
        f"scope: {bundle.session_scope.value}",
        f"session_events: {len(bundle.session_events)}",
        f"personal_memories: {len(bundle.personal_memories)}",
        f"shared_memories: {len(bundle.shared_memories)}",
    ]
    if bundle.personal_memories:
        lines.append("最近 personal:")
        for item in bundle.personal_memories[:3]:
            lines.append(f"- {item.content[:80]}")
    if bundle.shared_memories:
        lines.append("最近 shared:")
        for item in bundle.shared_memories[:3]:
            lines.append(f"- {item.content[:80]}")
    return lines


def _build_approval_list_message(approvals: list[Any]) -> str:
    if not approvals:
        return "当前没有待审批事项。"
    lines = [
        "[Pending Approvals]",
        f"count: {len(approvals)}",
        "",
    ]
    for item in approvals[:10]:
        if isinstance(item, dict) and item.get("kind") == "control_plane_v2":
            task = item["task"]
            approval = item["approval"]
            risk_tags = ", ".join(task.risk_tags) if task.risk_tags else "-"
            lines.append(f"- {approval.approval_id} | v2 | {task.capability_id} | {risk_tags} | {task.name}")
        else:
            lines.append(f"- {item.approval_id} | {item.risk.value} | {item.title}")
    lines.extend(
        [
            "",
            "发送 /approve <approval_id> 查看详情。",
            "发送 /approve <approval_id> approve [备注] 或 /approve <approval_id> reject [备注] 执行决策。",
        ]
    )
    return "\n".join(lines).strip()


def _build_v2_approval_detail_message(
    approval: ControlPlaneApprovalRead,
    task: ControlPlaneTaskRead,
) -> str:
    risk_tags = ", ".join(task.risk_tags) if task.risk_tags else "-"
    lines = [
        "[Control Plane v2 Approval]",
        f"approval: {approval.approval_id}",
        f"task: {task.task_id}",
        f"capability: {task.capability_id}",
        f"risk_tags: {risk_tags}",
        f"status: {task.status.value}",
        "console: /control-plane",
    ]
    if task.name:
        lines.append(f"name: {task.name}")
    if task.intent:
        lines.append(f"intent: {task.intent}")
    if approval.note:
        lines.append(f"note: {approval.note}")
    if approval.status == ControlPlaneApprovalStatus.PENDING and task.status == ControlPlaneTaskStatus.AWAITING_APPROVAL:
        lines.extend(
            [
                "",
                f"/approve {approval.approval_id} approve [备注]",
                f"/approve {approval.approval_id} reject [备注]",
            ]
        )
    return "\n".join(lines).strip()


def _build_v2_approval_reply_markup(approval_id: str | None) -> dict[str, Any] | None:
    normalized = str(approval_id or "").strip()
    if not normalized:
        return None
    return {
        "inline_keyboard": [
            [
                {
                    "text": "批准 / Approve",
                    "callback_data": f"/approve {normalized} approve",
                },
                {
                    "text": "拒绝 / Reject",
                    "callback_data": f"/approve {normalized} reject",
                },
                {
                    "text": "授权一年 / Approve 1 year",
                    "callback_data": f"/approve {normalized} approve annual",
                },
            ],
            [
                {
                    "text": "详情 / Details",
                    "callback_data": f"/approve {normalized}",
                }
            ],
        ]
    }


def _build_approval_detail_message(approval: Any) -> str:
    lines = [
        "[Approval Detail]",
        f"id: {approval.approval_id}",
        f"status: {approval.status.value}",
        f"risk: {approval.risk.value}",
        f"title: {approval.title}",
        f"source: {approval.source}",
    ]
    if approval.summary:
        lines.append(f"summary: {approval.summary}")
    if approval.session_id:
        lines.append(f"session: {approval.session_id}")
    if approval.agent_run_id:
        lines.append(f"agent_run: {approval.agent_run_id}")
    if approval.expires_at is not None:
        lines.append(f"expires_at: {approval.expires_at.isoformat()}")
    if approval.status == ApprovalStatus.PENDING:
        lines.extend(
            [
                "",
                f"/approve {approval.approval_id} approve [备注]",
                f"/approve {approval.approval_id} reject [备注]",
            ]
        )
    return "\n".join(lines).strip()


def _build_v2_approval_decision_message(task: ControlPlaneTaskRead) -> str:
    lines = [
        "[Control Plane v2 Approval Decision]",
        f"task: {task.task_id}",
        f"capability: {task.capability_id}",
        f"status: {task.status.value}",
        f"run: {task.run_id or '-'}",
    ]
    if task.approval_id:
        lines.append(f"approval: {task.approval_id}")
    if task.error:
        lines.append(f"note: {task.error}")
    lines.append("console: /control-plane")
    return "\n".join(lines).strip()


def _build_approval_decision_message(approval: Any) -> str:
    lines = [
        "[Approval Decision]",
        f"id: {approval.approval_id}",
        f"status: {approval.status.value}",
        f"title: {approval.title}",
    ]
    if approval.decided_by:
        lines.append(f"decided_by: {approval.decided_by}")
    if approval.decision_note:
        lines.append(f"note: {approval.decision_note}")
    return "\n".join(lines).strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
