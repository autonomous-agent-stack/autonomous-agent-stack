from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autoresearch.core.adapters import CapabilityDomain, CapabilityProviderRegistry, SkillProvider
from autoresearch.core.services.telegram_identity import TelegramSessionIdentityRead
from autoresearch.shared.manager_agent_contract import ManagerDispatchRead
from autoresearch.shared.models import (
    ApprovalStatus,
    ChatType,
    JobStatus,
    OpenClawMemoryBundleRead,
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
        "/cancel [run_id] 取消最近或指定任务 / cancel latest or selected task",
        "/retry [run_id] 重试最近或指定失败任务 / retry latest or selected failed task",
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
) -> str:
    brand = (worker_brand or "").strip()
    opener = f"收到，任务已进队（由【{brand}】执行）。" if brand else "收到，任务已进队。"
    tail = (
        f"完成后由【{brand}】在此会话回复；要看 worker / 队列发 /status。"
        if brand
        else "Worker 接单即跑；要看 worker / 队列发 /status。"
    )
    table = _telegram_two_column_table(
        [
            ("任务", task_name),
            ("run_id", run_id),
            ("执行面 | Runtime", (runtime_id or "claude").strip().lower() or "claude"),
            ("Agent 名称 | Agent name", (agent_name or "").strip() or "（未命名）| (unnamed)"),
        ]
    )
    runtime_hint = (runtime_id or "claude").strip().lower() or "claude"
    agent_hint = (agent_name or "").strip() or "（未命名）| (unnamed)"
    body = "\n".join(
        [
            opener,
            "",
            f"执行面 | Runtime: {runtime_hint}",
            f"Agent 名称 | Agent name: {agent_hint}",
            "",
            *table,
            "",
            tail,
        ]
    )
    return _truncate_telegram_text(body)


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
    from autoresearch.shared.models import OpenClawSessionRead as _SessionRead

    descriptors = capability_registry.list_descriptors()
    skill_provider_count = len([item for item in descriptors if item.domain == CapabilityDomain.SKILL])
    runtime_display = runtime_identity["runtime_display"]
    runtime_host = runtime_identity["runtime_host"]
    runtime_platform = runtime_identity["runtime_platform"]
    if session is None:
        lines = [
            f"chat_id: {chat_id}",
            f"runtime: {runtime_display}",
            f"runtime_host: {runtime_host}",
            f"runtime_platform: {runtime_platform}",
            f"scope: {session_identity.scope.value}",
            f"session_key: {session_identity.session_key}",
            f"providers: {len(descriptors)}",
            f"skill_providers: {skill_provider_count}",
            "当前没有历史会话。",
            "发送任务文本后系统会自动创建会话并执行。",
        ]
        _append_worker_summary_lines(lines, workers)
        _append_worker_inventory_lines(lines, worker_inventory)
        return lines

    runtime_display = str(session.metadata.get("runtime_display") or runtime_display)
    runtime_host = str(session.metadata.get("runtime_host") or runtime_host)
    runtime_platform = str(session.metadata.get("runtime_platform") or runtime_platform)
    lines = [
        f"chat_id: {chat_id}",
        f"runtime: {runtime_display}",
        f"runtime_host: {runtime_host}",
        f"runtime_platform: {runtime_platform}",
        f"scope: {session.scope.value}",
        f"session_key: {session.session_key or session_identity.session_key}",
        f"session: {session.session_id}",
        f"session_status: {session.status.value}",
        f"active_runs: {sum(1 for run in runs if run.status.value in {'queued', 'running'})}",
        f"providers: {len(descriptors)}",
        f"skill_providers: {skill_provider_count}",
    ]
    previous_runtime = str(session.metadata.get("runtime_previous_display") or "").strip()
    switched_at = str(session.metadata.get("runtime_switched_at") or "").strip()
    if previous_runtime and switched_at:
        lines.append(f"runtime_switched: {previous_runtime} -> {runtime_display} @ {switched_at}")
    if memory_bundle is not None:
        lines.append(f"personal_memories: {len(memory_bundle.personal_memories)}")
        lines.append(f"shared_memories: {len(memory_bundle.shared_memories)}")
    if session.actor is not None:
        lines.append(f"actor_role: {session.actor.role.value}")
    _append_worker_summary_lines(lines, workers)
    _append_worker_inventory_lines(lines, worker_inventory)
    if not runs:
        lines.append("最近任务: 暂无")
        return lines

    lines.append("最近任务:")
    for run in runs[:3]:
        lines.append(f"- {run.agent_run_id} | {run.status.value} | {run.task_name}")
    return lines


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
    lines.extend(
        [
            "当前 Worker 概况",
            f"- 共 {summary.total_workers} 个 worker",
            f"- 在线 {summary.online_workers} 个，忙碌 {summary.busy_workers} 个，异常 {summary.degraded_workers} 个，离线 {summary.offline_workers} 个",
        ]
    )
    if not workers:
        lines.append("- 当前没有已注册 worker")
        return
    lines.append("Worker 列表")
    for worker in workers[:4]:
        latest = worker.latest_task_summary
        last_task = latest.task_name if latest is not None else "当前空闲"
        lines.append(
            f"- {worker.worker_id}：{worker.display_status}，队列 {worker.queue_depth}，活跃任务 {worker.active_tasks}，最近任务 {last_task}"
        )
        if latest is None:
            continue
        runtime_hint = _status_diag_value(latest, ("dispatch_runtime", "runtime_id"), default="unknown")
        phase_hint = _status_diag_value(latest, ("telegram_live_phase", "status"), default=latest.status.value)
        exit_hint = _status_diag_value(latest, ("exit_reason", "error_kind"), default="n/a")
        lines.append(
            f"  诊断: runtime={runtime_hint}, phase={phase_hint}, exit={exit_hint}"
        )


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
        lines.append(f"- {item.approval_id} | {item.risk.value} | {item.title}")
    lines.extend(
        [
            "",
            "发送 /approve <approval_id> 查看详情。",
            "发送 /approve <approval_id> approve [备注] 或 /approve <approval_id> reject [备注] 执行决策。",
        ]
    )
    return "\n".join(lines).strip()


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
