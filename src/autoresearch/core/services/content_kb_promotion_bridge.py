"""Bridge service: content_kb_ingest result → draft PR creation.

Reads the structured result of a CONTENT_KB_INGEST worker task and,
when draft_pr_requested is true, orchestrates branch/commit/PR via
the existing GitPromotionProvider protocol.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from autoresearch.shared.models import JobStatus

logger = logging.getLogger(__name__)


class ContentKBPromotionProvider(Protocol):
    """Minimal interface for creating a draft PR from content_kb artifacts."""

    def open_draft_pr(
        self,
        *,
        repo: str,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
        files: dict[str, str],
    ) -> str:
        """Create a draft PR and return the PR URL."""
        ...


@dataclass(slots=True)
class ContentKBPromotionResult:
    """Result of the content_kb → draft PR bridge."""

    pr_requested: bool
    pr_attempted: bool
    pr_url: str | None = None
    branch_name: str | None = None
    failure_reason: str | None = None
    promotion_id: str | None = None


@dataclass
class ContentKBPromotionBridge:
    """Orchestration bridge: ingest result → draft PR.

    This is the Phase 2 orchestrator that runs after CONTENT_KB_INGEST
    completes. It reads the ingest result for draft_pr_hint metadata
    and delegates to a ContentKBPromotionProvider for actual PR creation.
    """

    _provider: ContentKBPromotionProvider | None = None
    _base_branch: str = "main"

    def maybe_promote(
        self,
        *,
        task_type: str,
        result: dict[str, Any] | None,
    ) -> ContentKBPromotionResult:
        """Check ingest result and trigger PR creation if requested.

        This is the main entry point. Call after worker task completes.
        """
        if task_type != "content_kb_ingest":
            return ContentKBPromotionResult(
                pr_requested=False,
                pr_attempted=False,
            )

        if result is None:
            return ContentKBPromotionResult(
                pr_requested=False,
                pr_attempted=False,
            )

        hint = result.get("draft_pr_hint")
        if not hint or not result.get("draft_pr_requested"):
            return ContentKBPromotionResult(
                pr_requested=False,
                pr_attempted=False,
            )

        return self._create_draft_pr(hint, result)

    def _create_draft_pr(
        self,
        hint: dict[str, Any],
        ingest_result: dict[str, Any],
    ) -> ContentKBPromotionResult:
        promotion_id = f"ckb-pr-{uuid.uuid4().hex[:8]}"

        if self._provider is None:
            logger.warning(
                "content_kb draft PR requested (promotion_id=%s) but no provider configured",
                promotion_id,
            )
            return ContentKBPromotionResult(
                pr_requested=True,
                pr_attempted=False,
                promotion_id=promotion_id,
                failure_reason="no ContentKBPromotionProvider configured",
            )

        repo = hint.get("repo", "unknown/unknown")
        branch_prefix = hint.get("branch_prefix", "content-kb/ingest")
        title_prefix = hint.get("title_prefix", "docs(content-kb): ingest")

        # Build branch name
        slug = ingest_result.get("topic", "untitled")
        branch_name = f"{branch_prefix}/{slug}-{promotion_id}"

        # Build PR body from ingest result
        body_lines = [
            f"## Content KB Ingest",
            "",
            f"- **Topic:** {ingest_result.get('topic', 'unknown')}",
            f"- **Title:** {ingest_result.get('job_id', 'unknown')}",
            f"- **Repo:** {repo}",
            f"- **Directory:** {ingest_result.get('directory', 'unknown')}",
        ]
        files_written = ingest_result.get("files_written", [])
        if files_written:
            body_lines.append(f"- **Files:** {', '.join(files_written)}")
        body_lines.extend(["", "---", f"Promotion ID: {promotion_id}"])
        body = "\n".join(body_lines)

        # Build files dict for the provider
        files: dict[str, str] = {}
        indexes = ingest_result.get("indexes", {})
        for index_name, index_data in indexes.items():
            files[f"indexes/{index_name}.json"] = json.dumps(
                index_data, indent=2, ensure_ascii=False
            )

        try:
            pr_url = self._provider.open_draft_pr(
                repo=repo,
                branch_name=branch_name,
                base_branch=self._base_branch,
                title=title_prefix,
                body=body,
                files=files,
            )
            return ContentKBPromotionResult(
                pr_requested=True,
                pr_attempted=True,
                pr_url=pr_url,
                branch_name=branch_name,
                promotion_id=promotion_id,
            )
        except Exception as exc:
            logger.exception("content_kb draft PR failed (promotion_id=%s)", promotion_id)
            return ContentKBPromotionResult(
                pr_requested=True,
                pr_attempted=True,
                promotion_id=promotion_id,
                failure_reason=str(exc),
            )


class CliContentKBPromotionProvider:
    """Production provider: writes files to a worktree, commits, opens draft PR via gh CLI.

    Reuses the same git worktree + commit + push + gh pr create pattern
    as CliGitPromotionProvider from git_promotion_gate.py.
    """

    def __init__(
        self,
        *,
        repos_root: Path,
        env: dict[str, str] | None = None,
        github_host: str = "github.com",
    ) -> None:
        self._repos_root = repos_root
        self._env = dict(env or {})
        self._github_host = github_host.strip() or "github.com"

    def open_draft_pr(
        self,
        *,
        repo: str,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
        files: dict[str, str],
    ) -> str:
        """Create a draft PR with the given files.

        Steps:
        1. Locate or clone the target repo under repos_root
        2. Create a git worktree for the branch
        3. Write files into the worktree
        4. git add + commit + push
        5. gh pr create --draft
        6. Clean up worktree
        """
        repo_dir = self._repos_root / repo.replace("/", "--")

        # Ensure repo checkout exists
        if not (repo_dir / ".git").exists():
            repo_dir.parent.mkdir(parents=True, exist_ok=True)
            self._run(
                ["git", "clone", f"https://github.com/{repo}.git", str(repo_dir)],
                cwd=self._repos_root,
            )

        # Fetch latest
        self._run_git(repo_dir, ["fetch", "origin"])

        # Create worktree
        worktree_dir = repo_dir / ".worktrees" / branch_name.replace("/", "-")
        if worktree_dir.exists():
            self._run_git(repo_dir, ["worktree", "remove", "--force", str(worktree_dir)], check=False)
        self._run_git(
            repo_dir,
            ["worktree", "add", "-B", branch_name, str(worktree_dir), f"origin/{base_branch}"],
        )

        try:
            # Write files
            for relative_path, content in files.items():
                target = worktree_dir / relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            # Stage all changes
            self._run_git(worktree_dir, ["add", "."])

            # Check there are changes to commit
            status_output = self._run_git(worktree_dir, ["status", "--porcelain"])
            if not status_output.stdout.strip():
                raise RuntimeError("no changes to commit — files may already match target state")

            # Commit
            self._run_git(
                worktree_dir,
                [
                    "-c", "user.name=Content KB Bot",
                    "-c", "user.email=content-kb-bot@users.noreply.github.com",
                    "commit", "-m", title,
                ],
            )

            # Push
            self._run_git(worktree_dir, ["push", "-u", "origin", branch_name])

            # Open draft PR
            gh_path = shutil.which("gh")
            if gh_path is None:
                raise RuntimeError("gh CLI is not available")

            body_file = worktree_dir / ".pr-body.md"
            body_file.write_text(body, encoding="utf-8")

            completed = subprocess.run(
                [
                    gh_path, "pr", "create",
                    "--draft",
                    "--base", base_branch,
                    "--head", branch_name,
                    "--title", title,
                    "--body-file", str(body_file),
                ],
                cwd=worktree_dir,
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, **self._env},
            )
            if completed.returncode != 0:
                raise RuntimeError((completed.stderr or completed.stdout or "gh pr create failed").strip())

            lines = (completed.stdout or "").strip().splitlines()
            if not lines:
                raise RuntimeError("gh pr create returned empty output")
            pr_url = lines[-1].strip()
            logger.info("content_kb draft PR created: %s", pr_url)
            return pr_url

        finally:
            # Clean up worktree
            self._run_git(repo_dir, ["worktree", "remove", "--force", str(worktree_dir)], check=False)

    def _run_git(
        self,
        cwd: Path,
        args: list[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return self._run(["git", *args], cwd=cwd, check=check)

    def _run(
        self,
        cmd: list[str],
        *,
        cwd: Path,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, **self._env},
        )
        if check and completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout or f"command failed: {' '.join(cmd)}").strip())
        return completed


def build_content_kb_promotion_bridge(
    *,
    repos_root: Path | None = None,
    base_branch: str = "main",
) -> ContentKBPromotionBridge | None:
    """Build a ContentKBPromotionBridge with the CLI provider if available.

    Returns None if prerequisites (repos_root, gh CLI) are not met,
    allowing the daemon to degrade gracefully.
    """
    gh_path = shutil.which("gh")
    if gh_path is None:
        logger.info("gh CLI not found, content_kb draft PR promotion disabled")
        return None

    if repos_root is None:
        logger.info("no repos_root configured, content_kb draft PR promotion disabled")
        return None

    if not repos_root.exists():
        try:
            repos_root.mkdir(parents=True, exist_ok=True)
        except OSError:
            logger.warning("cannot create repos_root %s, promotion disabled", repos_root)
            return None

    provider = CliContentKBPromotionProvider(repos_root=repos_root)
    return ContentKBPromotionBridge(_provider=provider, _base_branch=base_branch)
