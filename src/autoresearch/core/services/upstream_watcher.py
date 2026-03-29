from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import tempfile

from autoresearch.shared.autoresearch_planner_contract import (
    UpstreamWatchCommitRead,
    UpstreamWatchDecision,
    UpstreamWatchRead,
)


_DEFAULT_UPSTREAM_URL = "https://github.com/openclaw/openclaw.git"
_DEFAULT_WORKSPACE_ROOT = Path("/Volumes/AI_LAB/ai_lab/workspace")
_NON_CORE_PATH_PREFIXES = (
    "extensions/",
    "test/helpers/extensions/",
    "docs/",
)
_NON_CORE_PATHS = {
    "CHANGELOG.md",
    ".gitignore",
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
}


class UpstreamWatcherService:
    """Inspect upstream changes in an isolated temp clone and decide whether to skip them."""

    def __init__(
        self,
        *,
        upstream_url: str = _DEFAULT_UPSTREAM_URL,
        workspace_root: Path | None = None,
        max_commits: int = 5,
    ) -> None:
        self._upstream_url = upstream_url.strip() or _DEFAULT_UPSTREAM_URL
        self._workspace_root = (workspace_root or _DEFAULT_WORKSPACE_ROOT).expanduser().resolve()
        self._max_commits = max(1, min(max_commits, 20))

    def inspect(self) -> UpstreamWatchRead:
        self._workspace_root.mkdir(parents=True, exist_ok=True)
        sync_dir = Path(tempfile.mkdtemp(prefix="openclaw-upstream.", dir=str(self._workspace_root)))
        default_branch = "main"
        try:
            default_branch = self._detect_default_branch()
            self._git(
                "clone",
                "--depth=1",
                "--single-branch",
                "--no-tags",
                "--branch",
                default_branch,
                self._upstream_url,
                str(sync_dir),
            )
            self._git(
                "fetch",
                f"--depth={self._max_commits + 1}",
                "origin",
                default_branch,
                cwd=sync_dir,
            )
            recent_commits = self._load_recent_commits(sync_dir=sync_dir, default_branch=default_branch)
            changed_paths = self._collect_changed_paths(recent_commits)
            focus_areas = self._derive_focus_areas(changed_paths)
            relevant_paths = [path for path in changed_paths if not self._is_non_core_path(path)]
            latest_commit = recent_commits[0] if recent_commits else None
            decision = UpstreamWatchDecision.SKIP if not relevant_paths else UpstreamWatchDecision.REVIEW
            result = UpstreamWatchRead(
                upstream_url=self._upstream_url,
                default_branch=default_branch,
                latest_commit_sha=latest_commit.sha if latest_commit else None,
                latest_commit_title=latest_commit.title if latest_commit else None,
                latest_commit_at=latest_commit.committed_at if latest_commit else None,
                recent_commits=recent_commits,
                changed_paths=changed_paths,
                relevant_paths=relevant_paths,
                focus_areas=focus_areas,
                decision=decision,
                summary=self._build_summary(decision=decision, focus_areas=focus_areas, relevant_paths=relevant_paths),
            )
        except Exception as exc:
            result = UpstreamWatchRead(
                upstream_url=self._upstream_url,
                default_branch=default_branch,
                decision=UpstreamWatchDecision.FAILED,
                summary="Upstream watch failed.",
                error=str(exc),
            )

        cleanup_paths = self._cleanup_temp_dirs()
        return result.model_copy(update={"cleaned_up": True, "cleanup_paths": cleanup_paths})

    def _detect_default_branch(self) -> str:
        output = self._git("ls-remote", "--symref", self._upstream_url, "HEAD")
        for line in output.splitlines():
            if not line.startswith("ref: "):
                continue
            parts = line.split()
            if len(parts) < 2 or not parts[1].startswith("refs/heads/"):
                continue
            return parts[1].removeprefix("refs/heads/")
        return "main"

    def _load_recent_commits(self, *, sync_dir: Path, default_branch: str) -> list[UpstreamWatchCommitRead]:
        raw = self._git(
            "log",
            f"origin/{default_branch}",
            f"--max-count={self._max_commits}",
            "--date=iso-strict",
            "--pretty=format:%H%x1f%cI%x1f%s",
            cwd=sync_dir,
        )
        commits: list[UpstreamWatchCommitRead] = []
        for line in raw.splitlines():
            parts = line.split("\x1f", 2)
            sha = parts[0] if len(parts) > 0 else ""
            committed_at_raw = parts[1] if len(parts) > 1 else ""
            title = parts[2] if len(parts) > 2 else ""
            committed_at = None
            if committed_at_raw:
                committed_at = datetime.fromisoformat(committed_at_raw.replace("Z", "+00:00"))
            commits.append(
                UpstreamWatchCommitRead(
                    sha=sha,
                    title=title,
                    committed_at=committed_at,
                    touched_paths=self._load_touched_paths(sync_dir=sync_dir, sha=sha),
                )
            )
        return commits

    def _load_touched_paths(self, *, sync_dir: Path, sha: str) -> list[str]:
        raw = self._git(
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            "-m",
            sha,
            cwd=sync_dir,
        )
        return self._dedupe(line.strip() for line in raw.splitlines() if line.strip())

    def _collect_changed_paths(self, commits: list[UpstreamWatchCommitRead]) -> list[str]:
        return self._dedupe(path for commit in commits for path in commit.touched_paths)

    def _derive_focus_areas(self, changed_paths: list[str]) -> list[str]:
        return self._dedupe(self._classify_focus_area(path) for path in changed_paths if path)

    def _classify_focus_area(self, path: str) -> str:
        normalized = path.strip("/")
        parts = normalized.split("/")
        if len(parts) >= 2 and parts[0] == "extensions":
            return f"extension:{parts[1]}"
        if len(parts) >= 4 and parts[:3] == ["test", "helpers", "extensions"]:
            helper_name = Path(parts[3]).stem.split("-", 1)[0]
            return f"extension:{helper_name}"
        if normalized in _NON_CORE_PATHS:
            return "repo-meta"
        return parts[0] if parts else normalized

    def _build_summary(
        self,
        *,
        decision: UpstreamWatchDecision,
        focus_areas: list[str],
        relevant_paths: list[str],
    ) -> str:
        if decision is UpstreamWatchDecision.SKIP:
            focus_text = ", ".join(self._format_focus_area(item) for item in focus_areas[:3]) or "non-core extensions"
            return f"Recent upstream changes remain in non-core areas ({focus_text}); auto-skipped."
        if decision is UpstreamWatchDecision.REVIEW:
            return f"Recent upstream changes touched review-required paths: {', '.join(relevant_paths[:5])}."
        return "Upstream watch failed."

    def _format_focus_area(self, focus_area: str) -> str:
        if focus_area.startswith("extension:"):
            name = focus_area.split(":", 1)[1]
            if name.lower() == "line":
                return "LINE"
            return name.replace("-", " ").title()
        if focus_area == "repo-meta":
            return "repo meta"
        return focus_area.replace("-", " ")

    def _is_non_core_path(self, path: str) -> bool:
        normalized = path.strip()
        if normalized in _NON_CORE_PATHS:
            return True
        return normalized.startswith(_NON_CORE_PATH_PREFIXES)

    def _cleanup_temp_dirs(self) -> list[str]:
        cleanup_paths: list[str] = []
        for path in sorted(self._workspace_root.glob("openclaw-upstream.*")):
            if not path.is_dir() or path.parent != self._workspace_root:
                continue
            cleanup_paths.append(str(path))
            shutil.rmtree(path, ignore_errors=True)
        return cleanup_paths

    def _git(self, *args: str, cwd: Path | None = None) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode == 0:
            return completed.stdout.strip()
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"git {' '.join(args)} failed: {detail}")

    def _dedupe(self, values: object) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for item in values:
            normalized = str(item).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            ordered.append(normalized)
        return ordered
