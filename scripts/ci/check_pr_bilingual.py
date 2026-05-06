#!/usr/bin/env python3
"""Documentation i18n and portability gate.

The filename is kept for CI compatibility with older workflows. The check no
longer enforces mixed-language PR bodies. It validates the current documentation
policy instead:

- maintained English docs have Simplified Chinese mirrors,
- active public docs do not use inline bilingual marker blocks,
- active public docs do not contain developer-machine absolute paths.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys

MACHINE_PATH_RE = re.compile(r"/Volumes/(?:AI_LAB|PS1008)\b|/Users/(?:iCloud_GZ|ai_lab)\b")
INLINE_BILINGUAL_RE = re.compile(r"\*\*(?:中文：|English:)\*\*")
TODO_TRANSLATE_RE = re.compile(r"(?:TODO\s+translate|todo\s+translate|待翻译|待譯)", re.IGNORECASE)

REQUIRED_PAIRS = (
    ("README.md", "README.zh-CN.md"),
    ("CONTRIBUTING.md", "CONTRIBUTING.zh-CN.md"),
    ("WHY_AAS.md", "WHY_AAS.zh-CN.md"),
    ("ARCHITECTURE.md", "ARCHITECTURE.zh-CN.md"),
    ("docs/README.md", "docs/README.zh-CN.md"),
    ("docs/architecture.md", "docs/architecture.zh-CN.md"),
    ("docs/agent-execution-protocol.md", "docs/agent-execution-protocol.zh-CN.md"),
    ("docs/github-assistant-quickstart.md", "docs/github-assistant-quickstart.zh-CN.md"),
    ("docs/linux-remote-worker.md", "docs/linux-remote-worker.zh-CN.md"),
    ("docs/openhands-cli-integration.md", "docs/openhands-cli-integration.zh-CN.md"),
    ("docs/rfc/README.md", "docs/rfc/README.zh-CN.md"),
)

ROOT_ACTIVE_DOCS = {
    "README.md",
    "README.en.md",
    "README.zh-CN.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.zh-CN.md",
    "WHY_AAS.md",
    "WHY_AAS.zh-CN.md",
    "ARCHITECTURE.md",
    "ARCHITECTURE.zh-CN.md",
}

EXCLUDED_DOC_PARTS = {
    ".git",
    ".claude",
    "archive",
    "memory",
}

EXCLUDED_DOC_PREFIXES = (
    "docs/archive/",
    "tests/",
    "prompts/",
    "agents/",
    "profiles/",
)


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    line: int
    message: str

    def render(self) -> str:
        location = self.path if self.line <= 0 else f"{self.path}:{self.line}"
        return f"{location}: {self.code}: {self.message}"


def should_skip() -> bool:
    return os.environ.get("SKIP_CHECK", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def repo_root_from_cwd() -> Path:
    return Path.cwd()


def is_active_public_doc(path: Path, root: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    parts = set(path.relative_to(root).parts)
    if parts & EXCLUDED_DOC_PARTS:
        return False
    if any(rel.startswith(prefix) for prefix in EXCLUDED_DOC_PREFIXES):
        return False
    if path.parent == root:
        return path.name in ROOT_ACTIVE_DOCS
    return rel.startswith("docs/") and path.suffix == ".md"


def iter_active_public_docs(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*.md") if path.is_file() and is_active_public_doc(path, root)
    )


def check_required_pairs(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for english, chinese in REQUIRED_PAIRS:
        english_path = root / english
        chinese_path = root / chinese
        if not english_path.exists():
            issues.append(
                Issue(
                    code="missing-english-doc",
                    path=english,
                    line=0,
                    message=f"Expected canonical English doc for {chinese}.",
                )
            )
        if not chinese_path.exists():
            issues.append(
                Issue(
                    code="missing-zh-cn-doc",
                    path=chinese,
                    line=0,
                    message=f"Expected Simplified Chinese mirror for {english}.",
                )
            )
    return issues


def check_file(path: Path, root: Path) -> list[Issue]:
    rel = path.relative_to(root).as_posix()
    issues: list[Issue] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if MACHINE_PATH_RE.search(line):
            issues.append(
                Issue(
                    code="machine-path",
                    path=rel,
                    line=line_no,
                    message=(
                        "Use repo-relative links or AAS_* environment variables "
                        "instead of developer-machine absolute paths."
                    ),
                )
            )
        if INLINE_BILINGUAL_RE.search(line):
            issues.append(
                Issue(
                    code="inline-bilingual-marker",
                    path=rel,
                    line=line_no,
                    message=(
                        "Active docs should be language-separated; do not use "
                        "inline Chinese/English marker blocks."
                    ),
                )
            )
        if TODO_TRANSLATE_RE.search(line):
            issues.append(
                Issue(
                    code="translation-placeholder",
                    path=rel,
                    line=line_no,
                    message="Do not leave translation placeholders in active docs.",
                )
            )
    return issues


def check_repository(root: Path) -> list[Issue]:
    issues = check_required_pairs(root)
    for path in iter_active_public_docs(root):
        issues.extend(check_file(path, root))
    return issues


def main() -> int:
    if should_skip():
        print("docs-i18n-check: SKIP_CHECK set, skipping.")
        return 0

    root = repo_root_from_cwd()
    issues = check_repository(root)
    if not issues:
        print("docs-i18n-check: ok")
        return 0

    print("docs-i18n-check: failed", file=sys.stderr)
    for issue in issues:
        print(issue.render(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
