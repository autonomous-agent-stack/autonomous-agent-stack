#!/usr/bin/env python3
"""Coarse bilingual check for GitHub PR title/body (AGENTS.md policy).

Requires both Chinese (CJK) and English (Latin letters) in the body for non-draft PRs.
Skipped via env SKIP_CHECK=1, or when body/title indicate skip (see main).
"""

from __future__ import annotations

import os
import re
import sys

# At least this many Han characters (excluding pure punctuation-only "Chinese").
MIN_CJK = 2
# At least this many Latin letters (rough proxy for an English paragraph).
MIN_LATIN = 24
MIN_BODY_LEN = 40

SKIP_TITLE_MARKERS = (
    "[skip i18n]",
    "[skip-bilingual]",
    "[skip bilingual]",
)


def has_cjk(text: str) -> bool:
    if not text:
        return False
    han = re.findall(r"[\u4e00-\u9fff]", text)
    return len(han) >= MIN_CJK


def has_english_prose(text: str) -> bool:
    if not text:
        return False
    latin = re.findall(r"[A-Za-z]", text)
    return len(latin) >= MIN_LATIN


def should_skip(*, title: str, body: str | None) -> tuple[bool, str]:
    t = (title or "").strip()
    b = body or ""
    low = t.lower()
    for m in SKIP_TITLE_MARKERS:
        if m.lower() in low:
            return True, f"title contains {m!r}"
    if "[skip i18n]" in b.lower() or "[skip-bilingual]" in b.lower():
        return True, "body contains skip marker"
    return False, ""


def check_pr_body(body: str) -> tuple[bool, str]:
    b = (body or "").strip()
    if len(b) < MIN_BODY_LEN:
        return False, (
            f"PR 正文过短（<{MIN_BODY_LEN} 字符）。请使用仓库 PR 模板，填写中英摘要。\n"
            f"PR body too short (<{MIN_BODY_LEN} chars). Use the PR template and fill ZH + EN."
        )
    if not has_cjk(b):
        return False, (
            "PR 正文未检测到足够中文（至少 2 个汉字）。请按 AGENTS.md 补充中文说明。\n"
            "Not enough Chinese (Han) in PR body; add ZH per AGENTS.md."
        )
    if not has_english_prose(b):
        return False, (
            "PR 正文未检测到足够英文（拉丁字母）。请按 AGENTS.md 补充英文说明。\n"
            "Not enough English (Latin letters) in PR body; add EN per AGENTS.md."
        )
    return True, "ok"


def main() -> int:
    if os.environ.get("SKIP_CHECK", "").strip() in ("1", "true", "yes"):
        print("check_pr_bilingual: SKIP_CHECK set, skipping.")
        return 0

    title = os.environ.get("PR_TITLE", "")
    body = os.environ.get("PR_BODY")

    skip, reason = should_skip(title=title, body=body)
    if skip:
        print(f"check_pr_bilingual: skipped ({reason}).")
        return 0

    ok, msg = check_pr_body(body or "")
    if ok:
        print(msg)
        return 0
    print(msg, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
