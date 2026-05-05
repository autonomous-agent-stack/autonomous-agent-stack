"""Telegram Butler message formatting and MarkdownV2 escaping."""

from __future__ import annotations

import re
from typing import Any


TELEGRAM_MARKDOWN_V2_PARSE_MODE = "MarkdownV2"
_MARKDOWN_V2_SPECIALS = set(r"_*[]()~`>#+-=|{}.!")


def markdown_v2_escape(value: Any) -> str:
    """Escape arbitrary user/agent text for Telegram MarkdownV2."""
    text = "" if value is None else str(value)
    out: list[str] = []
    for char in text:
        if char == "\\":
            out.append("\\\\")
        elif char in _MARKDOWN_V2_SPECIALS:
            out.append(f"\\{char}")
        else:
            out.append(char)
    return "".join(out)


def telegram_runtime_attribution_row(runtime_id: str | None) -> tuple[str, str]:
    """Bilingual table key + normalized runtime value for Telegram butler cards."""
    key = "执行面 | Runtime"
    rid = (runtime_id or "claude").strip().lower()
    return key, rid if rid else "claude"


def telegram_agent_attribution_row(agent_name: str | None) -> tuple[str, str]:
    """Bilingual table key + agent display value (placeholder when unset)."""
    key = "Agent 名称 | Agent name"
    name = (agent_name or "").strip()
    if not name:
        return key, "（未命名）| (unnamed)"
    return key, name[:200]


def resolve_telegram_agent_attribution(
    *sources: dict[str, Any],
    default_agent: str = "butler_orchestrator",
) -> tuple[str, list[str]]:
    """Return primary agent + participant agents from payload/metadata/result bags."""
    primary = ""
    participant_names: list[str] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        if not primary:
            for key in (
                "telegram_display_primary_agent",
                "telegram_display_agent_name",
                "primary_agent",
                "target_agent",
                "agent_name",
                "responsible_agent",
            ):
                candidate = str(source.get(key) or "").strip()
                if candidate:
                    primary = candidate
                    break
        for key in (
            "telegram_display_agent_names",
            "telegram_display_agent_name",
            "target_agents",
            "agent_names",
            "agents",
            "target_agent",
            "agent_name",
        ):
            participant_names.extend(_agent_names_from_value(source.get(key)))

    names = _dedupe_agent_names(participant_names)
    if not primary:
        primary = names[0] if names else default_agent
    if not names:
        names = [primary]
    elif primary not in names:
        names.insert(0, primary)
    return primary[:200], [name[:200] for name in names[:8]]


def format_butler_queue_ack_message(
    *,
    task_name: str,
    run_id: str,
    worker_brand: str,
    runtime_id: str | None = None,
    capability_id: str | None = None,
    primary_agent: str | None = None,
    agent_names: list[str] | tuple[str, ...] | None = None,
    max_chars: int = 3900,
) -> str:
    primary, agents = resolve_telegram_agent_attribution(
        {
            "telegram_display_primary_agent": primary_agent,
            "telegram_display_agent_names": list(agent_names or []),
        }
    )
    runtime = _clean_value(runtime_id or "claude")
    capability = _clean_value(capability_id or runtime)
    brand = _clean_value(worker_brand)
    status = "已入队 / queued"
    tail = (
        f"完成后由 {brand} 在此会话回复；发送 /status 查看 worker 与队列 / {brand} will reply here when done; send /status for worker and queue state"
        if brand
        else "Worker 接单即跑；发送 /status 查看 worker 与队列 / The worker starts after claiming the task; send /status for worker and queue state"
    )
    lines = [
        _mdv2_title("管家已接单 | Butler queued"),
        _mdv2_field("状态 | Status", status),
        "",
        *_mdv2_section(
            "归属 | Attribution",
            [
                ("负责 agent | Primary agent", primary),
                ("参与 agents | Agents", _agent_list_text(agents)),
                ("执行面 | Runtime", runtime),
                ("能力 | Capability", capability),
            ],
        ),
        "",
        *_mdv2_section(
            "任务 | Task",
            [
                ("名称 | Name", task_name),
                ("run id", run_id),
            ],
        ),
        "",
        markdown_v2_escape(tail),
    ]
    return _truncate_markdown_v2("\n".join(lines), max_chars=max_chars)


def format_butler_completion_message(
    *,
    brand: str,
    task_name: str,
    run_id: str,
    status_label: str,
    body: str,
    runtime_id: str | None = None,
    capability_id: str | None = None,
    primary_agent: str | None = None,
    agent_names: list[str] | tuple[str, ...] | None = None,
    phase: str | None = None,
    diagnostics: str | None = None,
    summary: str | None = None,
    notify_state: str | None = None,
    error: str | None = None,
    max_chars: int = 3900,
) -> str:
    primary, agents = resolve_telegram_agent_attribution(
        {
            "telegram_display_primary_agent": primary_agent,
            "telegram_display_agent_names": list(agent_names or []),
        }
    )
    status = _clean_value(status_label) or "completed"
    title = _completion_title_for_status(status)
    clean_brand = _clean_value(brand)
    if clean_brand:
        title = f"{clean_brand} · {title}"

    runtime = _clean_value(runtime_id or "claude")
    capability = _clean_value(capability_id or runtime)
    task_rows: list[tuple[str, str]] = [
        ("名称 | Name", task_name),
        ("run id", run_id),
        ("状态 | Status", status),
    ]
    if phase:
        task_rows.append(("阶段 | Phase", phase))
    attribution_rows = [
        ("负责 agent | Primary agent", primary),
        ("参与 agents | Agents", _agent_list_text(agents)),
        ("执行面 | Runtime", runtime),
        ("能力 | Capability", capability),
    ]
    detail_rows: list[tuple[str, str]] = []
    if diagnostics:
        detail_rows.append(("诊断 | Diagnostics", diagnostics))
    if notify_state:
        detail_rows.append(("worker 投递 | Worker delivery", notify_state))
    if summary:
        detail_rows.append(("摘要 | Summary", summary))

    clean_body = _clean_value(body) or "（无文本输出）| (no text output)"
    lines = [
        _mdv2_title(title),
        _mdv2_field("状态 | Status", status),
        "",
        *_mdv2_section("归属 | Attribution", attribution_rows),
        "",
        *_mdv2_section("任务 | Task", task_rows),
    ]
    if detail_rows:
        lines.extend(["", *_mdv2_section("详情 | Details", detail_rows)])
    lines.extend(["", _mdv2_title("结果 | Result"), markdown_v2_escape(clean_body)])
    if error:
        lines.extend(["", _mdv2_title("错误 | Error"), markdown_v2_escape(error[:1200])])
    return _truncate_markdown_v2("\n".join(lines), max_chars=max_chars)


def strip_trailing_eof_marker(text: str) -> str:
    """Remove a final line that is only ``EOF`` (Hermes soft end marker)."""
    lines = (text or "").replace("\r\n", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and lines[-1].strip() in {"EOF", "`EOF`", "```EOF```"}:
        lines.pop()
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()


def format_butler_live_status_message(
    *,
    brand: str,
    message: str | None,
    metrics: dict[str, Any],
    max_chars: int = 3800,
) -> str:
    """Short running card for editMessageText while a worker reports RUNNING.

    Hermes ticks use the default title. Other tasks (e.g. YouTube autoflow) may set
    ``metrics["telegram_live_card_title"]`` so the bubble does not read like a Hermes run.
    """
    m = metrics or {}
    elapsed = m.get("telegram_live_elapsed_s")
    hs = str(m.get("hermes_status") or "").strip()
    rid = str(m.get("hermes_runtime_run_id") or "").strip()
    tail = str(m.get("telegram_live_stdout_tail") or "").strip()
    msg = (message or "").strip()

    b = (brand or "").strip()
    custom_title = str(m.get("telegram_live_card_title") or "").strip()
    title = custom_title or "管家运行中 | Butler running"
    if b:
        title = f"{b} · {title}"
    primary, agents = resolve_telegram_agent_attribution(m)
    r_disp = str(m.get("telegram_display_runtime_id") or m.get("runtime_id") or "hermes").strip().lower()
    capability = str(m.get("capability_id") or r_disp or "hermes").strip()
    progress_rows: list[tuple[str, str]] = [("状态 | Status", hs or "running")]
    if elapsed is not None:
        progress_rows.append(("耗时 | Elapsed", f"{elapsed}s"))
    if rid:
        progress_rows.append(("runtime run", rid))
    if msg:
        progress_rows.append(("worker", msg[:200]))

    parts: list[str] = [
        _mdv2_title(title),
        "",
        *_mdv2_section(
            "归属 | Attribution",
            [
                ("负责 agent | Primary agent", primary),
                ("参与 agents | Agents", _agent_list_text(agents)),
                ("执行面 | Runtime", r_disp or "?"),
                ("能力 | Capability", capability),
            ],
        ),
        "",
        *_mdv2_section("进度 | Progress", progress_rows),
    ]
    if tail:
        parts.extend(["", _mdv2_title("最近输出 | Recent output"), markdown_v2_escape(tail[:2800])])
    body = "\n".join(parts).strip()
    return _truncate_markdown_v2(body, max_chars=max_chars)


def polish_butler_completion_card(text: str, *, max_chars: int = 3900) -> str:
    """Normalize whitespace and cap length for a single Telegram bubble.

    Telegram hard limit is 4096; we stay under ``max_chars`` to leave margin for
    later small edits without hitting ``message is too long``.
    """
    t = strip_trailing_eof_marker((text or "").replace("\r\n", "\n"))
    t = t.strip()
    if not t:
        return t
    # Collapse runs of 4+ blank lines to three (keeps section breaks readable).
    t = re.sub(r"\n{4,}", "\n\n\n", t)
    # Trim trailing whitespace on each line (Telegram renders oddly otherwise).
    t = "\n".join(line.rstrip() for line in t.split("\n"))
    if len(t) <= max_chars:
        return t
    head = t[: max_chars - 120].rstrip()
    return (
        f"{head}\n\n"
        "…（正文过长，已在此处截断；完整输出可在控制面/日志中按 run id 查看） / Output truncated here; full output is available by run id"
    )


def _agent_names_from_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, dict):
        for key in ("name", "agent_name", "agent_id", "id"):
            candidate = str(value.get(key) or "").strip()
            if candidate:
                return [candidate]
        return []
    if isinstance(value, (list, tuple, set)):
        names: list[str] = []
        for item in value:
            names.extend(_agent_names_from_value(item))
        return names
    text = str(value).strip()
    if not text:
        return []
    if "," in text:
        return [item.strip() for item in text.split(",") if item.strip()]
    return [text]


def _dedupe_agent_names(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        name = str(raw or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out


def _clean_value(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _agent_list_text(names: list[str]) -> str:
    return ", ".join(name for name in names if str(name).strip()) or "（未命名）| (unnamed)"


def _mdv2_title(text: str) -> str:
    return f"*{markdown_v2_escape(text)}*"


def _mdv2_field(label: str, value: Any) -> str:
    return f"*{markdown_v2_escape(label)}*：{markdown_v2_escape(value)}"


def _mdv2_section(title: str, rows: list[tuple[str, Any]]) -> list[str]:
    lines = [_mdv2_title(title)]
    for label, value in rows:
        clean = _clean_value(value)
        if clean:
            lines.append(_mdv2_field(label, clean))
    return lines


def _completion_title_for_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "completed":
        return "管家已完成 | Butler completed"
    if normalized in {"cancelled", "canceled", "cancel_requested"}:
        return "管家取消中 | Butler cancellation"
    if normalized in {"failed", "interrupted"}:
        return "管家执行失败 | Butler failed"
    return "管家任务结束 | Butler finished"


def _truncate_markdown_v2(text: str, *, max_chars: int) -> str:
    body = text.strip()
    if len(body) <= max_chars:
        return body
    suffix = "\n\n…正文过长，已截断；请用 run id 查看完整日志 / Text truncated, use run id for full logs"
    head = body[: max(1, max_chars - len(suffix))].rstrip()
    while head.endswith("\\"):
        head = head[:-1].rstrip()
    return f"{head}{suffix}"
