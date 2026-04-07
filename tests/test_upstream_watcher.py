from __future__ import annotations

import os
from pathlib import Path
import subprocess

from autoresearch.core.services.upstream_watcher import UpstreamWatcherService
from autoresearch.shared.autoresearch_planner_contract import UpstreamWatchDecision


def _git(repo: Path, *args: str, cwd: Path | None = None) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Codex Tests",
            "GIT_AUTHOR_EMAIL": "codex-tests@example.com",
            "GIT_COMMITTER_NAME": "Codex Tests",
            "GIT_COMMITTER_EMAIL": "codex-tests@example.com",
        }
    )
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd or repo),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    return completed.stdout.strip()


def _commit(repo: Path, rel_path: str, content: str, message: str) -> None:
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    _git(repo, "add", rel_path)
    _git(repo, "commit", "-m", message)


def _init_upstream_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "upstream"
    _git(tmp_path, "init", "-b", "main", str(repo), cwd=tmp_path)
    _commit(repo, "README.md", "# upstream\n", "docs: bootstrap repo")
    return repo


def test_upstream_watcher_skips_channel_only_updates_and_cleans_workspace(tmp_path: Path) -> None:
    upstream_repo = _init_upstream_repo(tmp_path)
    _commit(upstream_repo, "extensions/line/src/channel.ts", "export const ok = true;\n", "fix: line health check")
    _commit(
        upstream_repo,
        "test/helpers/extensions/zalo-lifecycle.ts",
        "export const helper = true;\n",
        "test: harden zalo lifecycle",
    )
    _commit(upstream_repo, "CHANGELOG.md", "- line and zalo hardening\n", "docs: changelog refresh")

    workspace_root = tmp_path / "workspace"
    service = UpstreamWatcherService(
        upstream_url=upstream_repo.resolve().as_uri(),
        workspace_root=workspace_root,
        max_commits=3,
    )

    result = service.inspect()

    assert result.decision is UpstreamWatchDecision.SKIP
    assert result.cleaned_up is True
    assert result.latest_commit_title == "docs: changelog refresh"
    assert "extension:line" in result.focus_areas
    assert "extension:zalo-lifecycle.ts" not in result.focus_areas
    assert result.relevant_paths == []
    assert not list(workspace_root.glob("openclaw-upstream.*"))


def test_upstream_watcher_flags_review_when_core_paths_change(tmp_path: Path) -> None:
    upstream_repo = _init_upstream_repo(tmp_path)
    _commit(upstream_repo, "src/runtime/core.py", "def boot() -> str:\n    return 'ok'\n", "feat: tweak runtime core")
    _commit(upstream_repo, "extensions/line/src/channel.ts", "export const ok = true;\n", "fix: line health check")

    workspace_root = tmp_path / "workspace"
    service = UpstreamWatcherService(
        upstream_url=upstream_repo.resolve().as_uri(),
        workspace_root=workspace_root,
        max_commits=2,
    )

    result = service.inspect()

    assert result.decision is UpstreamWatchDecision.REVIEW
    assert "src/runtime/core.py" in result.relevant_paths
    assert result.cleaned_up is True
    assert not list(workspace_root.glob("openclaw-upstream.*"))
