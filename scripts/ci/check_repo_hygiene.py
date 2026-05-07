#!/usr/bin/env python3
"""Repository release-health hygiene checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys

MACHINE_PATH_RE = re.compile(r"/Volumes/(?:AI_LAB|PS1008)\b|/Users/(?:iCloud_GZ|ai_lab)\b")
INLINE_BILINGUAL_RE = re.compile(r"^\s*(?:\*\*)?(?:中文：|English:)(?:\*\*)?")
RUNTIME_DB_SUFFIXES = (".sqlite", ".sqlite3", ".db")

SCAN_PREFIXES = ("src/", "tests/")
SCANNED_SUFFIXES = (".py", ".md", ".sh", ".yaml", ".yml", ".toml")
MACHINE_PATH_ALLOWLIST = {
    "tests/test_agent_runner_outcomes.py",
    "tests/test_check_pr_bilingual.py",
    "tests/ga/test_runtime_isolation.py",
}
ACTIVE_DOCS = {
    "README.md",
    "README.zh-CN.md",
    "CONTRIBUTING.md",
    "CONTRIBUTING.zh-CN.md",
    "WHY_AAS.md",
    "WHY_AAS.zh-CN.md",
    "ARCHITECTURE.md",
    "ARCHITECTURE.zh-CN.md",
    "docs/README.md",
    "docs/README.zh-CN.md",
    "docs/architecture.md",
    "docs/architecture.zh-CN.md",
    "docs/project-health.md",
    "docs/project-health.zh-CN.md",
}


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    line: int
    message: str

    def render(self) -> str:
        location = self.path if self.line <= 0 else f"{self.path}:{self.line}"
        return f"{location}: {self.code}: {self.message}"


def _git_ls_files(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def check_tracked_runtime_databases(root: Path, tracked_files: list[str] | None = None) -> list[Issue]:
    files = tracked_files if tracked_files is not None else _git_ls_files(root)
    return [
        Issue(
            code="tracked-runtime-db",
            path=path,
            line=0,
            message="Runtime database files must stay out of source tracking.",
        )
        for path in files
        if path.endswith(RUNTIME_DB_SUFFIXES)
    ]


def _iter_scanned_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for prefix in SCAN_PREFIXES:
        base = root / prefix
        if not base.exists():
            continue
        paths.extend(path for path in base.rglob("*") if path.is_file() and path.suffix in SCANNED_SUFFIXES)
    return sorted(paths)


def check_machine_paths(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for path in _iter_scanned_files(root):
        rel = path.relative_to(root).as_posix()
        if rel in MACHINE_PATH_ALLOWLIST:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if MACHINE_PATH_RE.search(line):
                issues.append(
                    Issue(
                        code="developer-machine-path",
                        path=rel,
                        line=line_no,
                        message="Use repo-relative paths or AAS_* environment variables.",
                    )
                )
    return issues


def check_active_doc_markers(root: Path) -> list[Issue]:
    issues: list[Issue] = []
    for rel in sorted(ACTIVE_DOCS):
        path = root / rel
        if not path.exists():
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if INLINE_BILINGUAL_RE.search(line):
                issues.append(
                    Issue(
                        code="inline-bilingual-marker",
                        path=rel,
                        line=line_no,
                        message="Keep active public docs language-separated.",
                    )
                )
    return issues


def check_repository(root: Path) -> list[Issue]:
    return [
        *check_tracked_runtime_databases(root),
        *check_machine_paths(root),
        *check_active_doc_markers(root),
    ]


def main() -> int:
    root = Path.cwd()
    issues = check_repository(root)
    if not issues:
        print("repo-hygiene-check: ok")
        return 0

    print("repo-hygiene-check: failed", file=sys.stderr)
    for issue in issues:
        print(issue.render(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
