from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from autoresearch.github_assistant.config import load_assistant_config
from autoresearch.github_assistant.models import GitHubIssue, GitHubIssueComment, PreparedWorkspace
from autoresearch.github_assistant.service import GitHubAssistantService
from autoresearch.shared.models import GitRemoteProbe


class FakeGitHubGateway:
    def __init__(
        self,
        *,
        installed: bool = True,
        authenticated: bool = True,
        accessible_repos: set[str] | None = None,
        issues: dict[tuple[str, int], GitHubIssue] | None = None,
    ) -> None:
        self.installed = installed
        self.authenticated = authenticated
        self.accessible_repos = accessible_repos or set()
        self.issues = issues or {}
        self.added_labels: list[tuple[str, int, tuple[str, ...]]] = []
        self.issue_comments: list[tuple[str, int, str]] = []
        self.pr_comments: list[tuple[str, int, str]] = []
        self.pull_requests: dict[tuple[str, int], dict[str, object]] = {}
        self.merged_prs: dict[str, list[dict[str, object]]] = {}

    def is_installed(self) -> bool:
        return self.installed

    def auth_status(self) -> bool:
        return self.authenticated

    def current_login(self) -> str | None:
        return "demo-bot" if self.authenticated else None

    def repo_accessible(self, repo: str) -> bool:
        return repo in self.accessible_repos

    def fetch_issue(self, repo: str, issue_number: int) -> GitHubIssue:
        return self.issues[(repo, issue_number)]

    def list_open_issues(self, repo: str, *, label: str | None = None, limit: int = 10) -> list[int]:
        _ = label, limit
        return [
            issue.number
            for (issue_repo, _), issue in self.issues.items()
            if issue_repo == repo and issue.state.upper() == "OPEN"
        ]

    def add_labels(self, repo: str, issue_number: int, labels: list[str]) -> None:
        self.added_labels.append((repo, issue_number, tuple(labels)))

    def add_assignees(self, repo: str, issue_number: int, assignees: list[str]) -> None:
        _ = repo, issue_number, assignees

    def comment_issue(self, repo: str, issue_number: int, body: str) -> None:
        self.issue_comments.append((repo, issue_number, body))

    def comment_pr(self, repo: str, pr_number: int, body: str) -> None:
        self.pr_comments.append((repo, pr_number, body))

    def fetch_pull_request(self, repo: str, pr_number: int) -> dict[str, object]:
        payload = self.pull_requests[(repo, pr_number)]
        from autoresearch.github_assistant.models import GitHubPullRequest

        return GitHubPullRequest.model_validate(payload)

    def list_merged_pull_requests(self, repo: str, *, limit: int = 10) -> list[dict[str, object]]:
        from autoresearch.github_assistant.models import GitHubMergedPullRequest

        return [
            GitHubMergedPullRequest.model_validate(item)
            for item in self.merged_prs.get(repo, [])[:limit]
        ]


class FakeWorkspaceManager:
    def __init__(self, source_repo: Path, sandbox_root: Path) -> None:
        self._source_repo = source_repo
        self._sandbox_root = sandbox_root

    def prepare(self, *, repo: str, run_id: str) -> PreparedWorkspace:
        _ = repo
        source_repo_dir = self._sandbox_root / run_id / "source"
        execution_workspace_dir = self._sandbox_root / run_id / "workspace"
        shutil.copytree(self._source_repo, source_repo_dir, symlinks=True)
        shutil.copytree(self._source_repo, execution_workspace_dir, symlinks=True)
        return PreparedWorkspace(
            source_repo_dir=source_repo_dir,
            execution_workspace_dir=execution_workspace_dir,
        )

    def cleanup(self, prepared: PreparedWorkspace) -> None:
        shutil.rmtree(prepared.source_repo_dir.parent, ignore_errors=True)


class FakeGitPromotionProvider:
    def __init__(self) -> None:
        self.branch_calls: list[tuple[str, str]] = []
        self.commit_calls: list[tuple[str, str, tuple[str, ...]]] = []
        self.pr_calls: list[tuple[str, str, str]] = []

    def probe_remote_health(self, repo_root: Path, *, base_branch: str) -> GitRemoteProbe:
        _ = repo_root, base_branch
        return GitRemoteProbe(
            remote_name="origin",
            remote_url="git@example.invalid/demo.git",
            healthy=True,
            credentials_available=True,
            base_branch_exists=True,
        )

    def create_branch(
        self,
        repo_root: Path,
        *,
        branch_name: str,
        base_branch: str,
        workspace_dir: Path,
    ) -> None:
        _ = repo_root
        workspace_dir.mkdir(parents=True, exist_ok=True)
        self.branch_calls.append((branch_name, base_branch))

    def commit_changes(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        patch_uri: Path,
        changed_files: list[str],
        commit_message: str,
        validator_commands: list[str] | None = None,
        validator_log_dir: Path | None = None,
    ) -> str:
        _ = repo_root, workspace_dir, patch_uri, changed_files, validator_log_dir
        validators = tuple(validator_commands or [])
        self.commit_calls.append((branch_name, commit_message, validators))
        if any(command == "fail-validator" for command in validators):
            raise RuntimeError("validator failed: fail-validator")
        return "deadbeef"

    def push_branch(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
    ) -> None:
        _ = repo_root, workspace_dir, branch_name

    def open_draft_pr(
        self,
        repo_root: Path,
        *,
        workspace_dir: Path,
        branch_name: str,
        base_branch: str,
        title: str,
        body: str,
    ) -> str:
        _ = repo_root, workspace_dir, body
        self.pr_calls.append((branch_name, base_branch, title))
        return "https://github.com/acme/demo/pull/7"


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
    return completed.stdout


def _init_demo_repo(repo_root: Path) -> None:
    (repo_root / "src").mkdir(parents=True, exist_ok=True)
    (repo_root / "tests").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo_root / "tests" / "test_app.py").write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")
    _git(repo_root, "init", "-b", "main")
    _git(repo_root, "config", "user.email", "tests@example.com")
    _git(repo_root, "config", "user.name", "Tests")
    _git(repo_root, "add", ".")
    _git(repo_root, "commit", "-m", "initial")


def _write_template_root(
    root: Path,
    *,
    repos: list[dict[str, object]],
    assistant_overrides: dict[str, object] | None = None,
) -> None:
    (root / "policies").mkdir(parents=True, exist_ok=True)
    (root / "prompts").mkdir(parents=True, exist_ok=True)
    assistant_payload: dict[str, object] = {
        "bot_account": "demo-bot",
        "branch_prefix": "assistant/issue",
        "draft_pr_only": True,
        "manual_trigger_enabled": True,
        "scheduled_trigger_enabled": False,
        "issue_autoclose": False,
        "max_changed_files": 10,
        "max_patch_lines": 120,
        "runs_dir": "runs",
        "workspace_root": "/tmp/github-assistant-tests",
        "prompts_dir": "prompts",
        "policy_path": "policies/default-policy.yaml",
        "executor": {"adapter": "codex", "binary": "codex", "command": [], "timeout_seconds": 120, "env": {}},
        "schedule": {"issue_label": "assistant:auto", "max_issues_per_repo": 5},
    }
    if assistant_overrides:
        assistant_payload.update(assistant_overrides)
    (root / "assistant.yaml").write_text(json.dumps(assistant_payload, indent=2), encoding="utf-8")
    (root / "repos.yaml").write_text(json.dumps({"repos": repos}, indent=2), encoding="utf-8")
    (root / "policies" / "default-policy.yaml").write_text(
        json.dumps(
            {
                "forbidden_paths": ["runs/**", "memory/**", "logs/**", ".git/**"],
                "allow_comment": True,
                "allow_label": True,
                "allow_assign": True,
                "allow_branch": True,
                "allow_commit": True,
                "allow_push": True,
                "allow_draft_pr": True,
                "allow_autoclose": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "prompts" / "issue-triage.md").write_text(
        "type=${issue_type}\npriority=${priority}\nauto=${auto_executable}\n${reasons}\n",
        encoding="utf-8",
    )
    (root / "prompts" / "issue-execution-plan.md").write_text(
        "branch=${branch_name}\ncommit=${commit_message}\nallowed=${allowed_paths}\n",
        encoding="utf-8",
    )
    (root / "prompts" / "draft-pr-summary.md").write_text(
        "Issue ${issue_number}\n${issue_url}\n${summary}\n",
        encoding="utf-8",
    )
    (root / "prompts" / "pr-review.md").write_text(
        "PR ${pr_number}\n${risk_level}\n${changed_files}\n",
        encoding="utf-8",
    )
    (root / "prompts" / "release-ops.md").write_text(
        "Release ${target_version}\n${merged_prs}\n${suggested_actions}\n",
        encoding="utf-8",
    )


def _issue(
    *,
    repo: str,
    number: int,
    title: str,
    body: str,
    labels: list[str] | None = None,
    state: str = "OPEN",
) -> GitHubIssue:
    return GitHubIssue(
        repo=repo,
        number=number,
        title=title,
        body=body,
        url=f"https://github.com/{repo}/issues/{number}",
        state=state,
        author="founder",
        labels=labels or [],
        assignees=[],
        comments=[GitHubIssueComment(author="reviewer", body="keep the fix narrow")],
    )


def _repo_config(*, repo: str = "acme/demo", test_command: str = "pytest -q", allowed_paths: list[str] | None = None) -> dict[str, object]:
    return {
        "repo": repo,
        "default_branch": "main",
        "language": "python",
        "workspace_mode": "temp",
        "allowed_paths": allowed_paths or ["src/**", "tests/**"],
        "test_command": test_command,
        "lint_command": "ruff check .",
        "reviewers": ["alice"],
        "labels_map": {
            "bug": ["type:bug"],
            "feature": ["type:feature"],
            "duplicate": ["status:duplicate"],
            "info_needed": ["status:needs-info"],
            "auto_execute": ["assistant:auto-execute"],
        },
    }


def _read_summary(run_dir: Path) -> dict[str, object]:
    return json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))


def test_doctor_reports_missing_configs(tmp_path: Path) -> None:
    gateway = FakeGitHubGateway()
    service = GitHubAssistantService(repo_root=tmp_path, github=gateway, executor_runner=lambda **_: None)

    checks, ok = service.doctor()

    assert ok is False
    assert any(check.name == "assistant.yaml" and check.status.value == "FAIL" for check in checks)
    assert any(check.name == "repos.yaml" and check.status.value == "FAIL" for check in checks)


def test_doctor_reports_gh_auth_and_repo_access_failures(tmp_path: Path) -> None:
    _write_template_root(tmp_path, repos=[_repo_config()])
    gateway = FakeGitHubGateway(installed=True, authenticated=False, accessible_repos=set())
    service = GitHubAssistantService(repo_root=tmp_path, github=gateway, executor_runner=lambda **_: None)

    checks, ok = service.doctor()
    check_map = {check.name: check for check in checks}

    assert ok is False
    assert check_map["gh auth"].status.value == "FAIL"
    assert check_map["repo:acme/demo"].status.value == "WARN"


def test_doctor_reports_executor_and_directory_failures(tmp_path: Path) -> None:
    bad_runs = tmp_path / "runs.txt"
    bad_workspace = tmp_path / "workspace.txt"
    bad_runs.write_text("not a directory\n", encoding="utf-8")
    bad_workspace.write_text("not a directory\n", encoding="utf-8")
    _write_template_root(
        tmp_path,
        repos=[_repo_config()],
        assistant_overrides={
            "runs_dir": bad_runs.name,
            "workspace_root": str(bad_workspace),
            "executor": {"adapter": "codex", "binary": "missing-codex", "command": [], "timeout_seconds": 120, "env": {}},
        },
    )
    gateway = FakeGitHubGateway(accessible_repos={"acme/demo"})
    service = GitHubAssistantService(repo_root=tmp_path, github=gateway)

    checks, ok = service.doctor()
    check_map = {check.name: check for check in checks}

    assert ok is False
    assert check_map["runs dir"].status.value == "FAIL"
    assert check_map["workspace root"].status.value == "FAIL"
    assert check_map["executor"].status.value == "FAIL"


def test_load_assistant_config_applies_environment_overrides(tmp_path: Path, monkeypatch) -> None:
    _write_template_root(
        tmp_path,
        repos=[_repo_config()],
        assistant_overrides={
            "bot_account": "file-bot",
            "workspace_root": "/tmp/file-workspace",
            "executor": {"adapter": "shell", "command": [], "timeout_seconds": 120, "env": {}},
        },
    )
    monkeypatch.setenv("GH_ASSISTANT_BOT_ACCOUNT", "env-bot")
    monkeypatch.setenv("GH_ASSISTANT_WORKSPACE_ROOT", str(tmp_path / "env-workspace"))
    monkeypatch.setenv("GH_ASSISTANT_EXECUTOR_ADAPTER", "custom")
    monkeypatch.setenv("GH_ASSISTANT_EXECUTOR", "python3 -m demo.executor")

    config = load_assistant_config(tmp_path)

    assert config.bot_account == "env-bot"
    assert config.workspace_root == str(tmp_path / "env-workspace")
    assert config.executor.adapter == "custom"
    assert config.executor.command == ["python3", "-m", "demo.executor"]


def test_triage_classifies_bug_issue(tmp_path: Path) -> None:
    _write_template_root(tmp_path, repos=[_repo_config()])
    issue = _issue(
        repo="acme/demo",
        number=11,
        title="Crash when saving settings",
        body="Steps to repro:\n1. Open settings\n2. Save\nExpected: success\nActual: traceback on save.",
        labels=["bug"],
    )
    gateway = FakeGitHubGateway(
        accessible_repos={"acme/demo"},
        issues={("acme/demo", 11): issue},
    )
    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=gateway,
        executor_runner=lambda **_: None,
    )

    run_dir, triage = service.triage("acme/demo", 11)

    assert triage.issue_type.value == "bug"
    assert triage.priority.value == "medium"
    assert triage.auto_executable is True
    assert (run_dir / "triage.json").exists()


def test_triage_classifies_feature_and_duplicate_and_info_needed(tmp_path: Path) -> None:
    _write_template_root(tmp_path, repos=[_repo_config()])
    gateway = FakeGitHubGateway(
        accessible_repos={"acme/demo"},
        issues={
            ("acme/demo", 12): _issue(
                repo="acme/demo",
                number=12,
                title="Add CSV export support",
                body="Users should be able to export orders. Acceptance: CSV has headers and UTF-8.",
                labels=["enhancement"],
            ),
            ("acme/demo", 13): _issue(
                repo="acme/demo",
                number=13,
                title="Duplicate of #9",
                body="duplicate of #9",
                labels=["duplicate"],
            ),
            ("acme/demo", 14): _issue(
                repo="acme/demo",
                number=14,
                title="Feature request",
                body="please add it",
                labels=["feature"],
            ),
        },
    )
    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=gateway,
        executor_runner=lambda **_: None,
    )

    _, feature = service.triage("acme/demo", 12)
    _, duplicate = service.triage("acme/demo", 13)
    _, info_needed = service.triage("acme/demo", 14)

    assert feature.issue_type.value == "feature"
    assert feature.auto_executable is True
    assert duplicate.issue_type.value == "duplicate"
    assert duplicate.auto_executable is False
    assert info_needed.issue_type.value == "feature"
    assert info_needed.auto_executable is False
    assert any("acceptance detail" in reason for reason in info_needed.reasons)


def test_execute_creates_patch_and_draft_pr(tmp_path: Path) -> None:
    source_repo = tmp_path / "source-repo"
    source_repo.mkdir()
    _init_demo_repo(source_repo)
    _write_template_root(tmp_path, repos=[_repo_config()])
    gateway = FakeGitHubGateway(
        accessible_repos={"acme/demo"},
        issues={
            ("acme/demo", 21): _issue(
                repo="acme/demo",
                number=21,
                title="Fix settings save regression",
                body="Steps to repro:\n1. Save settings\nExpected: success\nActual: error",
                labels=["bug"],
            )
        },
    )
    workspace_manager = FakeWorkspaceManager(source_repo, tmp_path / "sandboxes")
    provider = FakeGitPromotionProvider()

    def executor_runner(*, workspace: Path, **_: object) -> None:
        (workspace / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=gateway,
        workspace_manager=workspace_manager,
        promotion_provider=provider,
        executor_runner=executor_runner,
        now_factory=lambda: datetime(2026, 4, 6, 3, 4, 5, tzinfo=timezone.utc),
    )

    run_dir = service.execute("acme/demo", 21)
    summary = _read_summary(run_dir)
    pr_payload = json.loads((run_dir / "pr_payload.json").read_text(encoding="utf-8"))

    assert summary["status"] == "draft_pr_opened"
    assert (run_dir / "patch.diff").exists()
    assert summary["pr_url"] == "https://github.com/acme/demo/pull/7"
    assert provider.branch_calls[0][0] != "main"
    assert pr_payload["base_branch"] == "main"
    assert pr_payload["head_branch"].startswith("assistant/issue/")
    assert "https://github.com/acme/demo/issues/21" in pr_payload["body"]
    assert gateway.issue_comments
    assert gateway.pr_comments


def test_execute_keeps_audit_when_validator_fails(tmp_path: Path) -> None:
    source_repo = tmp_path / "source-repo"
    source_repo.mkdir()
    _init_demo_repo(source_repo)
    _write_template_root(tmp_path, repos=[_repo_config(test_command="fail-validator")])
    gateway = FakeGitHubGateway(
        accessible_repos={"acme/demo"},
        issues={
            ("acme/demo", 22): _issue(
                repo="acme/demo",
                number=22,
                title="Fix broken import",
                body="Steps to repro:\n1. Import module\nExpected: works\nActual: crash",
                labels=["bug"],
            )
        },
    )
    provider = FakeGitPromotionProvider()

    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=gateway,
        workspace_manager=FakeWorkspaceManager(source_repo, tmp_path / "sandboxes"),
        promotion_provider=provider,
        executor_runner=lambda *, workspace, **_: (workspace / "src" / "app.py").write_text("VALUE = 3\n", encoding="utf-8"),
    )

    run_dir = service.execute("acme/demo", 22)
    summary = _read_summary(run_dir)

    assert summary["status"] == "promotion_failed"
    assert summary["pr_url"] is None
    assert (run_dir / "plan.md").exists()
    assert (run_dir / "patch.diff").exists()


def test_execute_blocks_forbidden_paths_outside_allowed_scope(tmp_path: Path) -> None:
    source_repo = tmp_path / "source-repo"
    source_repo.mkdir()
    _init_demo_repo(source_repo)
    _write_template_root(tmp_path, repos=[_repo_config(allowed_paths=["src/**"])])
    gateway = FakeGitHubGateway(
        accessible_repos={"acme/demo"},
        issues={
            ("acme/demo", 23): _issue(
                repo="acme/demo",
                number=23,
                title="Update docs from issue",
                body="Users should see updated docs. Acceptance: rewrite the README with the new content details.",
                labels=["feature"],
            )
        },
    )

    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=gateway,
        workspace_manager=FakeWorkspaceManager(source_repo, tmp_path / "sandboxes"),
        promotion_provider=FakeGitPromotionProvider(),
        executor_runner=lambda *, workspace, **_: (workspace / "README.md").write_text("changed\n", encoding="utf-8"),
    )

    run_dir = service.execute("acme/demo", 23)
    summary = _read_summary(run_dir)

    assert summary["status"] == "blocked"
    assert any("outside allowed_paths" in item for item in summary["warnings"])
    assert not (run_dir / "patch.diff").exists()


def test_execute_blocks_patch_when_it_is_too_large(tmp_path: Path) -> None:
    source_repo = tmp_path / "source-repo"
    source_repo.mkdir()
    _init_demo_repo(source_repo)
    _write_template_root(
        tmp_path,
        repos=[_repo_config()],
        assistant_overrides={"max_patch_lines": 5},
    )
    gateway = FakeGitHubGateway(
        accessible_repos={"acme/demo"},
        issues={
            ("acme/demo", 24): _issue(
                repo="acme/demo",
                number=24,
                title="Refactor config builder",
                body="Steps to repro:\n1. Run builder\nExpected: same output\nActual: needs patch",
                labels=["bug"],
            )
        },
    )

    def executor_runner(*, workspace: Path, **_: object) -> None:
        content = "\n".join(f"LINE_{index} = {index}" for index in range(20)) + "\n"
        (workspace / "src" / "app.py").write_text(content, encoding="utf-8")

    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=gateway,
        workspace_manager=FakeWorkspaceManager(source_repo, tmp_path / "sandboxes"),
        promotion_provider=FakeGitPromotionProvider(),
        executor_runner=executor_runner,
    )

    run_dir = service.execute("acme/demo", 24)
    summary = _read_summary(run_dir)

    assert summary["status"] == "promotion_failed"
    payload = json.loads((run_dir / "pr_payload.json").read_text(encoding="utf-8"))
    checks = payload["promotion_preflight"]["checks"]
    assert any(check["id"] == "gate.max_patch_lines" and check["passed"] is False for check in checks)


def test_execute_rejects_unmanaged_repo_and_catalog_is_dynamic(tmp_path: Path) -> None:
    _write_template_root(tmp_path, repos=[_repo_config(repo="acme/demo")])
    gateway = FakeGitHubGateway(
        accessible_repos={"acme/demo", "acme/demo-two"},
        issues={
            ("acme/demo-two", 31): _issue(
                repo="acme/demo-two",
                number=31,
                title="Fix API response casing",
                body="Steps to repro:\n1. Call API\nExpected: camelCase\nActual: snake_case",
                labels=["bug"],
            )
        },
    )
    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=gateway,
        executor_runner=lambda **_: None,
    )

    try:
        service.triage("acme/demo-two", 31)
    except KeyError:
        pass
    else:  # pragma: no cover - defensive
        raise AssertionError("triage should reject unmanaged repos")

    _write_template_root(tmp_path, repos=[_repo_config(repo="acme/demo"), _repo_config(repo="acme/demo-two")])
    run_dir, triage = service.triage("acme/demo-two", 31)

    assert triage.repo == "acme/demo-two"
    assert (run_dir / "triage.json").exists()


def test_codex_adapter_is_treated_as_configured_without_explicit_command(tmp_path: Path) -> None:
    _write_template_root(
        tmp_path,
        repos=[_repo_config()],
        assistant_overrides={"executor": {"adapter": "codex", "binary": "codex", "command": [], "timeout_seconds": 120, "env": {}}},
    )
    issue = _issue(
        repo="acme/demo",
        number=40,
        title="Fix adapter config",
        body="Steps to repro:\n1. Run it\nExpected: works\nActual: broken",
        labels=["bug"],
    )
    gateway = FakeGitHubGateway(
        accessible_repos={"acme/demo"},
        issues={("acme/demo", 40): issue},
    )
    service = GitHubAssistantService(repo_root=tmp_path, github=gateway)

    _, triage = service.triage("acme/demo", 40)

    assert triage.auto_executable is True


def test_review_pr_writes_review_artifacts(tmp_path: Path) -> None:
    _write_template_root(tmp_path, repos=[_repo_config()])
    gateway = FakeGitHubGateway(accessible_repos={"acme/demo"})
    gateway.pull_requests[("acme/demo", 9)] = {
        "repo": "acme/demo",
        "number": 9,
        "title": "Harden GitHub assistant policy checks",
        "body": "This PR adds new safety checks for the assistant.",
        "url": "https://github.com/acme/demo/pull/9",
        "state": "OPEN",
        "author": "alice",
        "base_ref": "main",
        "head_ref": "assistant/issue/9-harden",
        "labels": ["assistant:auto-execute"],
        "files": [
            {"path": "src/app.py", "additions": 10, "deletions": 2},
            {"path": "tests/test_app.py", "additions": 5, "deletions": 0},
        ],
    }
    service = GitHubAssistantService(repo_root=tmp_path, github=gateway)

    run_dir, review = service.review_pr("acme/demo", 9)

    assert review.risk_level in {"low", "medium"}
    assert (run_dir / "review.md").exists()
    assert (run_dir / "review.json").exists()
    summary = _read_summary(run_dir)
    assert summary["status"] == "reviewed_pr"


def test_release_plan_writes_release_artifacts(tmp_path: Path) -> None:
    _write_template_root(tmp_path, repos=[_repo_config()])
    gateway = FakeGitHubGateway(accessible_repos={"acme/demo"})
    gateway.merged_prs["acme/demo"] = [
        {
            "repo": "acme/demo",
            "number": 1,
            "title": "Fix settings save regression",
            "url": "https://github.com/acme/demo/pull/1",
            "author": "alice",
            "merged_at": "2026-04-05T10:00:00Z",
            "labels": ["bug"],
        },
        {
            "repo": "acme/demo",
            "number": 2,
            "title": "Add release notes template",
            "url": "https://github.com/acme/demo/pull/2",
            "author": "bob",
            "merged_at": "2026-04-05T11:00:00Z",
            "labels": ["feature"],
        },
    ]
    service = GitHubAssistantService(repo_root=tmp_path, github=gateway)

    run_dir, release_plan = service.release_plan("acme/demo", version="v1.2.0", limit=2)

    assert release_plan.target_version == "v1.2.0"
    assert len(release_plan.merged_prs) == 2
    assert (run_dir / "release-plan.md").exists()
    assert (run_dir / "release-plan.json").exists()
    summary = _read_summary(run_dir)
    assert summary["status"] == "release_planned"
