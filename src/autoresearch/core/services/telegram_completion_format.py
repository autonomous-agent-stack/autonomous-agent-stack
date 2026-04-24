"""Light layout polish for Telegram completion cards (butler editMessageText path)."""

from __future__ import annotations

import re
from typing import Any


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
    """Short running card for editMessageText while Hermes is in-flight."""
    m = metrics or {}
    elapsed = m.get("telegram_live_elapsed_s")
    hs = str(m.get("hermes_status") or "").strip()
    rid = str(m.get("hermes_runtime_run_id") or "").strip()
    tail = str(m.get("telegram_live_stdout_tail") or "").strip()
    msg = (message or "").strip()

    parts: list[str] = []
    b = (brand or "").strip()
    if b:
        parts.append(f"【{b}】")
    parts.append("Hermes 运行中… / still running")
    if elapsed is not None:
        parts.append(f"- elapsed: {elapsed}s")
    if hs:
        parts.append(f"- status: {hs}")
    if rid:
        parts.append(f"- runtime_run: `{rid}`")
    if msg:
        parts.append(f"- worker: {msg[:200]}")
    if tail:
        parts.append("")
        parts.append("```")
        parts.append(tail[:2800])
        parts.append("```")
    body = "\n".join(parts).strip()
    if len(body) <= max_chars:
        return body
    return body[: max_chars - 40] + "\n…[truncated]"


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
        "…（正文过长，已在此处截断；完整输出可在控制面/日志中按 run_id 查看）"
    )
