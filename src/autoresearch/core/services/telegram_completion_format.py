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
    """Normalized runtime value for legacy Telegram butler table callers."""
    key = "执行面"
    rid = (runtime_id or "claude").strip().lower()
    return key, rid if rid else "claude"


def telegram_agent_attribution_row(agent_name: str | None) -> tuple[str, str]:
    """Agent display value for legacy Telegram butler table callers."""
    key = "Agent"
    name = (agent_name or "").strip()
    if not name:
        return key, "（未命名）"
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
    execution = _execution_line_text(runtime, capability, primary=primary, agents=agents)
    tail = f"{brand} 会在这里回复；查进度发 /status。" if brand else "接单后开始执行；查进度发 /status。"
    lines = [
        _mdv2_title("管家已接单"),
        _mdv2_field("任务", task_name),
        _mdv2_field("状态", "已入队"),
        _mdv2_field("Agent", _agent_line_text(primary, agents)),
    ]
    if execution:
        lines.append(_mdv2_field("执行面", execution))
    lines.extend(
        [
            _mdv2_field("run id", run_id),
            "",
            markdown_v2_escape(tail),
        ]
    )
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
    execution = _execution_line_text(runtime, capability, primary=primary, agents=agents)
    task_rows: list[tuple[str, str]] = [
        ("任务", task_name),
        ("状态", _status_display_text(status)),
        ("Agent", _agent_line_text(primary, agents)),
        ("run id", run_id),
    ]
    if execution:
        task_rows.append(("执行面", execution))
    if phase:
        task_rows.append(("阶段", phase))
    detail_rows: list[tuple[str, str]] = []
    if diagnostics:
        detail_rows.append(("诊断", diagnostics))
    if notify_state:
        detail_rows.append(("投递", notify_state))
    if summary:
        detail_rows.append(("摘要", summary))

    clean_body = _clean_value(body) or "（无文本输出）"
    lines = [
        _mdv2_title(title),
        "",
        *_mdv2_fields(task_rows),
    ]
    if detail_rows:
        lines.extend(["", *_mdv2_fields(detail_rows)])
    lines.extend(["", _mdv2_title("结果"), markdown_v2_escape(clean_body)])
    if error:
        lines.extend(["", _mdv2_title("错误"), markdown_v2_escape(error[:1200])])
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
    title = custom_title or "管家运行中"
    if b:
        title = f"{b} · {title}"
    primary, agents = resolve_telegram_agent_attribution(m)
    r_disp = str(m.get("telegram_display_runtime_id") or m.get("runtime_id") or "hermes").strip().lower()
    capability = str(m.get("capability_id") or r_disp or "hermes").strip()
    execution = _execution_line_text(r_disp, capability, primary=primary, agents=agents)
    progress_rows: list[tuple[str, str]] = [
        ("状态", _status_display_text(hs or "running")),
        ("Agent", _agent_line_text(primary, agents)),
    ]
    if execution:
        progress_rows.append(("执行面", execution))
    if elapsed is not None:
        progress_rows.append(("耗时", f"{elapsed}s"))
    if rid:
        progress_rows.append(("运行 id", rid))
    if msg:
        progress_rows.append(("进展", msg[:200]))

    parts: list[str] = [
        _mdv2_title(title),
        "",
        *_mdv2_fields(progress_rows),
    ]
    if tail:
        parts.extend(["", _mdv2_title("最近输出"), markdown_v2_escape(tail[:2800])])
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
        "…（正文过长，已截断；完整输出可按 run id 查看）"
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
    return "、".join(name for name in names if str(name).strip()) or "（未命名）"


def _agent_line_text(primary: str, names: list[str]) -> str:
    main = _clean_value(primary) or "（未命名）"
    collaborators = [name for name in _dedupe_agent_names(names) if name and name != main]
    if not collaborators:
        return main
    return f"{main}（协作：{_agent_list_text(collaborators)}）"


def _execution_line_text(
    runtime: str | None,
    capability: str | None,
    *,
    primary: str,
    agents: list[str],
) -> str:
    runtime_text = _clean_value(runtime)
    capability_text = _clean_value(capability)
    values = _dedupe_agent_names([runtime_text, capability_text])
    if not values:
        return ""
    agent_names = {_clean_value(primary), *[_clean_value(agent) for agent in agents]}
    if all(value in agent_names for value in values):
        return ""
    return " / ".join(values)


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


def _mdv2_fields(rows: list[tuple[str, Any]]) -> list[str]:
    lines: list[str] = []
    for label, value in rows:
        clean = _clean_value(value)
        if clean:
            lines.append(_mdv2_field(label, clean))
    return lines


def _completion_title_for_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "completed":
        return "管家已完成"
    if normalized in {"cancelled", "canceled", "cancel_requested"}:
        return "管家取消中"
    if normalized in {"failed", "interrupted"}:
        return "管家执行失败"
    return "管家任务结束"


def _status_display_text(status: str) -> str:
    normalized = status.strip().lower()
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
    }.get(normalized, status.strip() or "未知")


def _truncate_markdown_v2(text: str, *, max_chars: int) -> str:
    body = text.strip()
    if len(body) <= max_chars:
        return body
    suffix = "\n\n…正文过长，已截断；请用 run id 查看完整日志"
    head = body[: max(1, max_chars - len(suffix))].rstrip()
    while head.endswith("\\"):
        head = head[:-1].rstrip()
    return f"{head}{suffix}"
