"""Light layout polish for Telegram completion cards (butler editMessageText path)."""

from __future__ import annotations

import re


def polish_butler_completion_card(text: str, *, max_chars: int = 3900) -> str:
    """Normalize whitespace and cap length for a single Telegram bubble.

    Telegram hard limit is 4096; we stay under ``max_chars`` to leave margin for
    later small edits without hitting ``message is too long``.
    """
    t = (text or "").replace("\r\n", "\n").strip()
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
