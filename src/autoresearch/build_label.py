"""Single-line build stamp for logs (no manual "did I run the right code?" checks)."""

from __future__ import annotations

import functools
import os
import subprocess
from pathlib import Path

from autoresearch import __version__


@functools.lru_cache(maxsize=1)
def get_build_label() -> str:
    """Return a short string suitable for startup logs.

    Resolution order:
    1. ``AUTORESEARCH_BUILD_LABEL`` if set (CI / release pipelines).
    2. ``{package_version}+{git_short_sha}`` when ``git rev-parse`` works inside the repo.
    3. ``{package_version}`` only.

    Cached for the process lifetime so repeated calls are cheap.
    """
    explicit = (os.getenv("AUTORESEARCH_BUILD_LABEL") or "").strip()
    if explicit:
        return explicit
    sha = _git_short_sha()
    if sha:
        return f"{__version__}+{sha}"
    return str(__version__)


def _repo_root() -> Path:
    # .../src/autoresearch/build_label.py -> repo root is parents[2]
    return Path(__file__).resolve().parents[2]


def _git_short_sha() -> str:
    root = _repo_root()
    if not (root / ".git").exists():
        return ""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ""
