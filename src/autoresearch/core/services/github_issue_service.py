from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import shutil
import subprocess


_ISSUE_URL_RE = re.compile(
    r"^https://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)/issues/(?P<number>\d+)(?:[/?#].*)?$"
)
_ISSUE_REF_RE = re.compile(r"^(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)#(?P<number>\d+)$")
_ISSUE_NUMBER_RE = re.compile(r"^#?(?P<number>\d+)$")
_REMOTE_RE = re.compile(
    r"^(?:https://github\.com/|git@github\.com:)(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?$"
)


@dataclass(frozen=True, slots=True)
class GitHubIssueCommentRead:
    author: str
    body: str
    created_at: str | None = None


@dataclass(frozen=True, slots=True)
class GitHubIssueReference:
    owner: str
    repo: str
    number: int

    @property
    def repo_full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def display(self) -> str:
        return f"{self.repo_full_name}#{self.number}"

    @property
    def url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}/issues/{self.number}"


@dataclass(frozen=True, slots=True)
class GitHubIssueRead:
    reference: GitHubIssueReference
    title: str
    body: str
    url: str
    state: str
    author: str
    labels: tuple[str, ...] = ()
    comments: tuple[GitHubIssueCommentRead, ...] = ()


class GitHubIssueService:
    """Thin wrapper around `gh issue` for Telegram intake and safe comment back."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        gh_binary: str | None = None,
    ) -> None:
        self._repo_root = (repo_root or Path(__file__).resolve().parents[3]).resolve()
        self._gh_binary = gh_binary or shutil.which("gh") or "gh"

    def resolve_issue_reference(self, raw_value: str) -> GitHubIssueReference:
        value = raw_value.strip()
        if not value:
            raise ValueError("missing GitHub issue reference")

        matched = _ISSUE_URL_RE.match(value)
        if matched:
            return GitHubIssueReference(
                owner=matched.group("owner"),
                repo=matched.group("repo"),
                number=int(matched.group("number")),
            )

        matched = _ISSUE_REF_RE.match(value)
        if matched:
            return GitHubIssueReference(
                owner=matched.group("owner"),
                repo=matched.group("repo"),
                number=int(matched.group("number")),
            )

        matched = _ISSUE_NUMBER_RE.match(value)
        if matched:
            owner, repo = self._resolve_current_repo()
            return GitHubIssueReference(
                owner=owner,
                repo=repo,
                number=int(matched.group("number")),
            )

        raise ValueError("unsupported GitHub issue reference; use URL, owner/repo#123, or #123")

    def fetch_issue(self, raw_reference: str) -> GitHubIssueRead:
        reference = self.resolve_issue_reference(raw_reference)
        payload = self._run_gh_json(
            [
                "issue",
                "view",
                str(reference.number),
                "--repo",
                reference.repo_full_name,
                "--json",
                "number,title,body,url,state,author,labels,comments",
            ]
        )
        comments = tuple(
            GitHubIssueCommentRead(
                author=str((item.get("author") or {}).get("login") or "unknown"),
                body=str(item.get("body") or ""),
                created_at=str(item.get("createdAt") or "") or None,
            )
            for item in payload.get("comments", [])
        )
        labels = tuple(
            str(item.get("name") or "").strip()
            for item in payload.get("labels", [])
            if str(item.get("name") or "").strip()
        )
        return GitHubIssueRead(
            reference=reference,
            title=str(payload.get("title") or "").strip(),
            body=str(payload.get("body") or ""),
            url=str(payload.get("url") or reference.url).strip(),
            state=str(payload.get("state") or "UNKNOWN").strip(),
            author=str((payload.get("author") or {}).get("login") or "unknown"),
            labels=labels,
            comments=comments,
        )

    def build_manager_prompt(self, issue: GitHubIssueRead, *, operator_note: str | None = None) -> str:
        lines = [
            "Resolve the following GitHub issue in the current repository through the existing patch-only manager pipeline.",
            "",
            f"Issue: {issue.reference.display}",
            f"URL: {issue.url}",
            f"Title: {issue.title or '(untitled)'}",
            f"State: {issue.state}",
            f"Author: {issue.author}",
        ]
        if issue.labels:
            lines.append(f"Labels: {', '.join(issue.labels)}")
        if operator_note:
            lines.extend(["", "Operator note:", operator_note.strip()])
        lines.extend(["", "Issue body:", issue.body.strip() or "(empty)"])

        recent_comments = [item for item in issue.comments if item.body.strip()][-3:]
        if recent_comments:
            lines.extend(["", "Recent comments:"])
            for item in recent_comments:
                lines.append(f"- {item.author}: {item.body.strip()}")

        lines.extend(
            [
                "",
                "Deliver the smallest useful fix, stay within scoped files, update tests when needed, and prepare a draft PR when possible.",
            ]
        )
        return "\n".join(lines).strip()

    def post_comment(self, raw_reference: str, body: str) -> str:
        reference = self.resolve_issue_reference(raw_reference)
        completed = self._run_gh(
            [
                "issue",
                "comment",
                str(reference.number),
                "--repo",
                reference.repo_full_name,
                "--body",
                body.strip(),
            ]
        )
        return (completed.stdout or "").strip()

    def _resolve_current_repo(self) -> tuple[str, str]:
        completed = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise ValueError("cannot resolve current GitHub repo from git origin")
        remote = (completed.stdout or "").strip()
        matched = _REMOTE_RE.match(remote)
        if not matched:
            raise ValueError("current git origin is not a supported GitHub remote")
        return matched.group("owner"), matched.group("repo")

    def _run_gh_json(self, args: list[str]) -> dict[str, object]:
        completed = self._run_gh(args)
        try:
            payload = json.loads((completed.stdout or "").strip() or "{}")
        except json.JSONDecodeError as exc:
            raise RuntimeError("gh returned invalid JSON for issue query") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("gh returned an unexpected payload for issue query")
        return payload

    def _run_gh(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [self._gh_binary, *args],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "gh command failed").strip()
            raise RuntimeError(detail)
        return completed
