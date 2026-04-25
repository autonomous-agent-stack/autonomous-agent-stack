"""Tests for github_assistant.models — Pydantic model validation and serialization."""
from __future__ import annotations

import pytest

from autoresearch.github_assistant.models import (
    AssistantPolicy,
    GitHubAssistantProfileConfig,
    GitHubAssistantProfilesConfig,
    GitHubIssue,
    GitHubIssueComment,
    GitHubMergedPullRequest,
    GitHubPullRequest,
    GitHubPullRequestFile,
    ManagedRepoConfig,
    RepoCatalog,
    TriageIssueType,
    TriagePriority,
    TriageResult,
    YouTubeIngestRouteConfig,
)


class TestYouTubeIngestRouteConfig:
    def test_defaults(self) -> None:
        cfg = YouTubeIngestRouteConfig()
        assert cfg.channel_ids == []
        assert cfg.channel_titles == []
        assert cfg.keywords == []
        assert cfg.enabled is False

    def test_normalize_none_to_empty_list(self) -> None:
        cfg = YouTubeIngestRouteConfig(channel_ids=None, keywords=None)
        assert cfg.channel_ids == []
        assert cfg.keywords == []

    def test_normalize_string_to_list(self) -> None:
        cfg = YouTubeIngestRouteConfig(channel_ids="  UCabc123  ")
        assert cfg.channel_ids == ["UCabc123"]

    def test_normalize_string_with_whitespace(self) -> None:
        cfg = YouTubeIngestRouteConfig(channel_ids="  ")
        assert cfg.channel_ids == []

    def test_normalize_list_of_strings(self) -> None:
        cfg = YouTubeIngestRouteConfig(channel_ids=["a", " b ", "c"])
        assert cfg.channel_ids == ["a", "b", "c"]


class TestManagedRepoConfig:
    def test_minimal(self) -> None:
        cfg = ManagedRepoConfig(repo="owner/repo")
        assert cfg.repo == "owner/repo"
        assert cfg.default_branch == "main"
        assert cfg.workspace_mode == "temp"

    def test_normalize_allowed_paths_none(self) -> None:
        cfg = ManagedRepoConfig(repo="owner/repo", allowed_paths=None)
        assert cfg.allowed_paths == []

    def test_normalize_reviewers_string(self) -> None:
        cfg = ManagedRepoConfig(repo="owner/repo", reviewers="  alice  ")
        assert cfg.reviewers == ["alice"]

    def test_normalize_labels_map(self) -> None:
        cfg = ManagedRepoConfig(
            repo="owner/repo",
            labels_map={"bug": ["priority-high", "needs-triage"]},
        )
        assert cfg.labels_map == {"bug": ["priority-high", "needs-triage"]}

    def test_normalize_labels_map_non_dict(self) -> None:
        cfg = ManagedRepoConfig(repo="owner/repo", labels_map="not a dict")
        assert cfg.labels_map == {}

    def test_normalize_labels_map_string_values(self) -> None:
        cfg = ManagedRepoConfig(
            repo="owner/repo",
            labels_map={"feature": "  enhancement  "},
        )
        assert cfg.labels_map == {"feature": ["enhancement"]}

    def test_normalize_labels_map_empty_key_skipped(self) -> None:
        cfg = ManagedRepoConfig(repo="owner/repo", labels_map={"": ["a"]})
        assert cfg.labels_map == {}


class TestRepoCatalog:
    def test_empty(self) -> None:
        cat = RepoCatalog()
        assert cat.repos == []

    def test_with_repos(self) -> None:
        cat = RepoCatalog(repos=[ManagedRepoConfig(repo="a/b"), ManagedRepoConfig(repo="c/d")])
        assert len(cat.repos) == 2


class TestGitHubAssistantProfileConfig:
    def test_minimal(self) -> None:
        cfg = GitHubAssistantProfileConfig(id="default")
        assert cfg.id == "default"
        assert cfg.github_host == "github.com"

    def test_normalize_strips_whitespace(self) -> None:
        cfg = GitHubAssistantProfileConfig(id="  my-profile  ")
        assert cfg.id == "my-profile"

    def test_normalize_display_name_none(self) -> None:
        cfg = GitHubAssistantProfileConfig(id="x", display_name=None)
        assert cfg.display_name is None

    def test_normalize_display_name_empty_string(self) -> None:
        cfg = GitHubAssistantProfileConfig(id="x", display_name="   ")
        assert cfg.display_name is None

    def test_normalize_display_name_with_value(self) -> None:
        cfg = GitHubAssistantProfileConfig(id="x", display_name="  My Profile  ")
        assert cfg.display_name == "My Profile"


class TestGitHubAssistantProfilesConfig:
    def test_default_profile_none(self) -> None:
        cfg = GitHubAssistantProfilesConfig()
        assert cfg.default_profile is None

    def test_normalize_default_profile_whitespace(self) -> None:
        cfg = GitHubAssistantProfilesConfig(default_profile="  prod  ")
        assert cfg.default_profile == "prod"

    def test_normalize_default_profile_empty(self) -> None:
        cfg = GitHubAssistantProfilesConfig(default_profile="   ")
        assert cfg.default_profile is None


class TestAssistantPolicy:
    def test_defaults(self) -> None:
        policy = AssistantPolicy()
        assert policy.forbidden_paths == []
        assert policy.allow_comment is True
        assert policy.allow_autoclose is False

    def test_normalize_forbidden_paths_none(self) -> None:
        policy = AssistantPolicy(forbidden_paths=None)
        assert policy.forbidden_paths == []

    def test_normalize_forbidden_paths_string(self) -> None:
        policy = AssistantPolicy(forbidden_paths="  /etc/passwd  ")
        assert policy.forbidden_paths == ["/etc/passwd"]


class TestGitHubModels:
    def test_github_issue_comment(self) -> None:
        c = GitHubIssueComment(author="alice", body="Looks good")
        assert c.author == "alice"
        assert c.created_at is None

    def test_github_issue(self) -> None:
        issue = GitHubIssue(
            repo="owner/repo", number=42, title="Bug", body="desc",
            url="https://github.com/owner/repo/issues/42",
            state="open", author="bob",
        )
        assert issue.number == 42
        assert issue.comments == []

    def test_github_pr_file(self) -> None:
        f = GitHubPullRequestFile(path="src/main.py", additions=10, deletions=2)
        assert f.path == "src/main.py"

    def test_github_pull_request(self) -> None:
        pr = GitHubPullRequest(
            repo="owner/repo", number=7, title="Fix", body="",
            url="https://github.com/owner/repo/pull/7",
            state="open", author="alice", base_ref="main", head_ref="fix-branch",
        )
        assert pr.files == []

    def test_github_merged_pr(self) -> None:
        mpr = GitHubMergedPullRequest(
            repo="owner/repo", number=3, title="Merge",
            url="https://github.com/owner/repo/pull/3",
            author="bob", merged_at="2026-01-01T00:00:00Z",
        )
        assert mpr.merged_at is not None

    def test_triage_issue_type_enum(self) -> None:
        assert TriageIssueType.BUG == "bug"
        assert TriageIssueType.FEATURE == "feature"

    def test_triage_priority_enum(self) -> None:
        assert TriagePriority.CRITICAL == "critical"
        assert TriagePriority.MEDIUM == "medium"

    def test_triage_result(self) -> None:
        result = TriageResult(
            repo="owner/repo",
            issue_number=42,
            issue_url="https://github.com/owner/repo/issues/42",
            issue_type=TriageIssueType.BUG,
            priority=TriagePriority.HIGH,
            summary="Crash on login",
            suggested_labels=["bug", "priority-high"],
        )
        assert result.issue_type == TriageIssueType.BUG
        assert result.priority == TriagePriority.HIGH
        assert result.suggested_labels == ["bug", "priority-high"]
