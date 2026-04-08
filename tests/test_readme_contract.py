from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"
_MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _iter_local_markdown_targets(text: str) -> list[str]:
    targets: list[str] = []
    for raw_target in _MARKDOWN_LINK_RE.findall(text):
        target = raw_target.strip().split(maxsplit=1)[0]
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        targets.append(target)
    return targets


def test_readme_local_links_resolve() -> None:
    text = README_PATH.read_text(encoding="utf-8")

    missing_targets: list[str] = []
    for target in _iter_local_markdown_targets(text):
        path_text = target.split("#", 1)[0]
        if not path_text:
            continue
        resolved = (README_PATH.parent / path_text).resolve()
        if not resolved.exists():
            missing_targets.append(target)

    assert missing_targets == [], f"README contains missing local links: {missing_targets}"


def test_readme_documents_current_core_paths_and_commands() -> None:
    text = README_PATH.read_text(encoding="utf-8")
    expected_snippets = [
        "requirements.lock",
        "make test-core",
        "/api/v1/worker-runs/youtube-autoflow",
        "/api/v1/gateway/telegram/webhook",
        "src/autoresearch/workers/mac/daemon.py",
        "src/autoresearch/core/services/standby_youtube_autoflow.py",
    ]

    missing = [snippet for snippet in expected_snippets if snippet not in text]
    assert missing == [], f"README is missing current core-path references: {missing}"
