from __future__ import annotations

from pathlib import Path

from autoresearch.core.services.github_issue_service import (
    GitHubIssueCommentRead,
    GitHubIssueRead,
    GitHubIssueReference,
    GitHubIssueService,
)


def test_resolve_issue_reference_supports_url_and_shorthand(tmp_path: Path) -> None:
    service = GitHubIssueService(repo_root=tmp_path)

    from_url = service.resolve_issue_reference("https://github.com/openai/example/issues/42")
    assert from_url.owner == "openai"
    assert from_url.repo == "example"
    assert from_url.number == 42

    from_ref = service.resolve_issue_reference("openai/example#43")
    assert from_ref.owner == "openai"
    assert from_ref.repo == "example"
    assert from_ref.number == 43


def test_resolve_issue_reference_supports_current_repo_issue_numbers(tmp_path: Path) -> None:
    service = GitHubIssueService(repo_root=tmp_path)
    service._resolve_current_repo = lambda: ("owner", "repo")  # type: ignore[method-assign]

    reference = service.resolve_issue_reference("#44")
    assert reference.owner == "owner"
    assert reference.repo == "repo"
    assert reference.number == 44


def test_build_manager_prompt_includes_issue_context_and_note(tmp_path: Path) -> None:
    service = GitHubIssueService(repo_root=tmp_path)
    issue = GitHubIssueRead(
        reference=GitHubIssueReference(owner="owner", repo="repo", number=45),
        title="Telegram task dispatch should create approvals",
        body="Expected behavior: issue tasks should ask before replying externally.",
        url="https://github.com/owner/repo/issues/45",
        state="OPEN",
        author="founder",
        labels=("bug", "telegram"),
        comments=(
            GitHubIssueCommentRead(author="reviewer", body="Please keep the fix narrow."),
        ),
    )

    prompt = service.build_manager_prompt(issue, operator_note="先保证审批链别断。")
    assert "owner/repo#45" in prompt
    assert "先保证审批链别断。" in prompt
    assert "Please keep the fix narrow." in prompt
    assert "prepare a draft PR when possible" in prompt
