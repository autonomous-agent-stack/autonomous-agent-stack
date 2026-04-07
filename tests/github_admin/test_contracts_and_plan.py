"""Tests for github_admin contracts and transfer plan builder."""
from __future__ import annotations

import pytest

from github_admin.contracts import RepoInfo, TransferPlan
from github_admin.transfer import build_transfer_plan


def _repo(name: str = "test-repo", owner: str = "lisa", **kw):
    return RepoInfo(name=name, owner=owner, **kw)


class TestTransferPlan:
    def test_dry_run_includes_all_non_archived(self) -> None:
        repos = [
            _repo("repo-a", owner="lisa"),
            _repo("repo-b", owner="lisa", archived=True),
            _repo("repo-c", owner="dd"),
        ]
        plan = build_transfer_plan(repos, target_owner="project", dry_run=True)
        assert "lisa/repo-a" in plan.repos_to_transfer
        assert "dd/repo-c" in plan.repos_to_transfer
        assert plan.dry_run is True

    def test_skip_archived(self) -> None:
        repos = [_repo("old", archived=True)]
        plan = build_transfer_plan(repos, target_owner="project")
        assert len(plan.repos_to_transfer) == 0
        assert len(plan.repos_to_skip) == 1
        assert "archived" in plan.repos_to_skip[0].skip_reason

    def test_filter_by_source_owners(self) -> None:
        repos = [_repo("a", owner="lisa"), _repo("b", owner="dd")]
        plan = build_transfer_plan(repos, target_owner="project", source_owners=["lisa"])
        assert len(plan.repos_to_transfer) == 1
        assert "lisa/a" in plan.repos_to_transfer

    def test_skip_flagged_repos(self) -> None:
        repos = [_repo("skip-me", transfer_candidate=False, skip_reason="personal experiment")]
        plan = build_transfer_plan(repos, target_owner="project")
        assert len(plan.repos_to_transfer) == 0
        assert len(plan.repos_to_skip) == 1
