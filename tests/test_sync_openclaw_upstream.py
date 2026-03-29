from __future__ import annotations

import os
from pathlib import Path
import subprocess


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


def test_sync_openclaw_upstream_script_cleans_temp_worktree(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    upstream_repo = tmp_path / "upstream"
    _git(tmp_path, "init", "-b", "main", str(upstream_repo), cwd=tmp_path)
    _commit(upstream_repo, "README.md", "# upstream\n", "docs: bootstrap repo")
    _commit(upstream_repo, "extensions/line/src/channel.ts", "export const ok = true;\n", "fix: line health check")

    workspace_root = tmp_path / "workspace"
    env = os.environ.copy()
    env.update(
        {
            "OPENCLAW_UPSTREAM_URL": upstream_repo.resolve().as_uri(),
            "OPENCLAW_SYNC_WORKSPACE_ROOT": str(workspace_root),
            "OPENCLAW_SYNC_MAX_COMMITS": "2",
        }
    )

    completed = subprocess.run(
        ["bash", str(repo_root / "scripts" / "sync_openclaw_upstream.sh")],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert "[sync] latest commit" in completed.stdout
    assert "fix: line health check" in completed.stdout
    assert "analysis complete; cleaning" in completed.stdout
    assert not list(workspace_root.glob("openclaw-upstream.*"))
