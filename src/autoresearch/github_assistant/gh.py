from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
import re

from autoresearch.github_assistant.models import (
    GitHubIssue,
    GitHubIssueComment,
    GitHubMergedPullRequest,
    GitHubPullRequest,
    GitHubPullRequestFile,
)

_AUTH_LOGIN_RE = re.compile(
    r"(?:Logged in to|Failed to log in to) github\.com account (?P<login>[A-Za-z0-9_.-]+)"
)


class GhCliGateway:
    def __init__(
        self,
        *,
        repo_root: Path,
        gh_binary: str | None = None,
        env: dict[str, str] | None = None,
        github_host: str = "github.com",
    ) -> None:
        self._repo_root = repo_root
        self._gh_binary = gh_binary or shutil.which("gh") or "gh"
        self._env = dict(env or {})
        self._github_host = github_host.strip() or "github.com"

    def is_installed(self) -> bool:
        return shutil.which(self._gh_binary) is not None if self._gh_binary != "gh" else shutil.which("gh") is not None

    def auth_status(self) -> bool:
        completed = self._run(self._auth_args("status"), check=False)
        return completed.returncode == 0

    def auth_probe(self) -> tuple[bool, str]:
        completed = self._run(self._auth_args("status"), check=False)
        detail = (completed.stderr or completed.stdout or "").strip() or "gh auth status failed"
        return completed.returncode == 0, detail

    def current_login(self) -> str | None:
        completed = self._run(self._auth_args("status"), check=False)
        matched = _AUTH_LOGIN_RE.search((completed.stdout or "") + "\n" + (completed.stderr or ""))
        if not matched:
            return None
        return matched.group("login")

    def build_auth_command(self, command: str) -> list[str]:
        return [self._gh_binary, *self._auth_args(command)]

    def repo_accessible(self, repo: str) -> bool:
        completed = self._run(
            ["repo", "view", repo, "--json", "nameWithOwner"],
            check=False,
        )
        return completed.returncode == 0

    def repo_probe(self, repo: str) -> tuple[bool, str]:
        completed = self._run(
            ["repo", "view", repo, "--json", "nameWithOwner"],
            check=False,
        )
        detail = (completed.stderr or completed.stdout or "").strip() or "gh repo view failed"
        return completed.returncode == 0, detail

    def fetch_issue(self, repo: str, issue_number: int) -> GitHubIssue:
        payload = self._run_json(
            [
                "issue",
                "view",
                str(issue_number),
                "--repo",
                repo,
                "--json",
                "number,title,body,url,state,author,labels,comments,assignees",
            ]
        )
        return GitHubIssue(
            repo=repo,
            number=int(payload.get("number") or issue_number),
            title=str(payload.get("title") or "").strip(),
            body=str(payload.get("body") or ""),
            url=str(payload.get("url") or "").strip(),
            state=str(payload.get("state") or "UNKNOWN").strip(),
            author=str((payload.get("author") or {}).get("login") or "unknown"),
            labels=[
                str(item.get("name") or "").strip()
                for item in payload.get("labels", [])
                if str(item.get("name") or "").strip()
            ],
            assignees=[
                str(item.get("login") or "").strip()
                for item in payload.get("assignees", [])
                if str(item.get("login") or "").strip()
            ],
            comments=[
                GitHubIssueComment(
                    author=str((item.get("author") or {}).get("login") or "unknown"),
                    body=str(item.get("body") or ""),
                    created_at=str(item.get("createdAt") or "") or None,
                )
                for item in payload.get("comments", [])
            ],
        )

    def fetch_pull_request(self, repo: str, pr_number: int) -> GitHubPullRequest:
        payload = self._run_json(
            [
                "pr",
                "view",
                str(pr_number),
                "--repo",
                repo,
                "--json",
                "number,title,body,url,state,author,labels,baseRefName,headRefName,files",
            ]
        )
        return GitHubPullRequest(
            repo=repo,
            number=int(payload.get("number") or pr_number),
            title=str(payload.get("title") or "").strip(),
            body=str(payload.get("body") or ""),
            url=str(payload.get("url") or "").strip(),
            state=str(payload.get("state") or "UNKNOWN").strip(),
            author=str((payload.get("author") or {}).get("login") or "unknown"),
            base_ref=str(payload.get("baseRefName") or "main").strip(),
            head_ref=str(payload.get("headRefName") or "").strip(),
            labels=[
                str(item.get("name") or "").strip()
                for item in payload.get("labels", [])
                if str(item.get("name") or "").strip()
            ],
            files=[
                GitHubPullRequestFile(
                    path=str(item.get("path") or "").strip(),
                    additions=int(item.get("additions") or 0),
                    deletions=int(item.get("deletions") or 0),
                )
                for item in payload.get("files", [])
                if str(item.get("path") or "").strip()
            ],
        )

    def list_merged_pull_requests(self, repo: str, *, limit: int = 10) -> list[GitHubMergedPullRequest]:
        payload = self._run_json(
            [
                "pr",
                "list",
                "--repo",
                repo,
                "--state",
                "merged",
                "--limit",
                str(limit),
                "--json",
                "number,title,url,author,mergedAt,labels",
            ],
            expect_list=True,
        )
        return [
            GitHubMergedPullRequest(
                repo=repo,
                number=int(item.get("number") or 0),
                title=str(item.get("title") or "").strip(),
                url=str(item.get("url") or "").strip(),
                author=str((item.get("author") or {}).get("login") or "unknown"),
                merged_at=str(item.get("mergedAt") or "") or None,
                labels=[
                    str(label.get("name") or "").strip()
                    for label in item.get("labels", [])
                    if str(label.get("name") or "").strip()
                ],
            )
            for item in payload
            if item.get("number") is not None
        ]

    def list_open_issues(self, repo: str, *, label: str | None = None, limit: int = 10) -> list[int]:
        args = [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number",
        ]
        if label:
            args.extend(["--label", label])
        payload = self._run_json(args, expect_list=True)
        return [int(item.get("number")) for item in payload if item.get("number") is not None]

    def add_labels(self, repo: str, issue_number: int, labels: list[str]) -> None:
        if not labels:
            return
        args = ["issue", "edit", str(issue_number), "--repo", repo]
        for label in labels:
            args.extend(["--add-label", label])
        self._run(args)

    def add_assignees(self, repo: str, issue_number: int, assignees: list[str]) -> None:
        if not assignees:
            return
        args = ["issue", "edit", str(issue_number), "--repo", repo]
        for assignee in assignees:
            args.extend(["--add-assignee", assignee])
        self._run(args)

    def comment_issue(self, repo: str, issue_number: int, body: str) -> None:
        self._run(
            [
                "issue",
                "comment",
                str(issue_number),
                "--repo",
                repo,
                "--body",
                body.strip(),
            ]
        )

    def comment_pr(self, repo: str, pr_number: int, body: str) -> None:
        self._run(
            [
                "pr",
                "comment",
                str(pr_number),
                "--repo",
                repo,
                "--body",
                body.strip(),
            ]
        )

    def clone_repo(self, repo: str, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        completed = self._run(
            ["repo", "clone", repo, str(destination)],
            check=False,
        )
        if completed.returncode == 0:
            return
        fallback = subprocess.run(
            ["git", "clone", f"https://{self._github_host}/{repo}.git", str(destination)],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if fallback.returncode != 0:
            detail = (completed.stderr or completed.stdout or fallback.stderr or fallback.stdout or "clone failed").strip()
            raise RuntimeError(detail)

    def _run_json(self, args: list[str], *, expect_list: bool = False) -> dict[str, object] | list[dict[str, object]]:
        completed = self._run(args)
        try:
            payload = json.loads((completed.stdout or "").strip() or "[]")
        except json.JSONDecodeError as exc:
            raise RuntimeError("gh returned invalid JSON") from exc
        if expect_list:
            if not isinstance(payload, list):
                raise RuntimeError("gh returned unexpected JSON payload")
            return payload
        if not isinstance(payload, dict):
            raise RuntimeError("gh returned unexpected JSON payload")
        return payload

    def _run(
        self,
        args: list[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        completed = subprocess.run(
            [self._gh_binary, *args],
            cwd=self._repo_root,
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, **self._env},
        )
        if check and completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "gh command failed").strip()
            raise RuntimeError(detail)
        return completed

    def _auth_args(self, command: str) -> list[str]:
        args = ["auth", command]
        if self._github_host:
            args.extend(["--hostname", self._github_host])
        return args
