from __future__ import annotations

from github_admin.contracts import (
    GitHubAdminPostActions,
    GitHubAdminProfileRead,
    GitHubAdminReadiness,
    GitHubAdminRepositoryRead,
)
from github_admin.transfer import build_preflight_report, build_transfer_decisions, render_transfer_plan_markdown


def _repo(full_name: str, *, source_owner: str = "Lisa", **overrides) -> GitHubAdminRepositoryRead:
    name = full_name.split("/", 1)[1]
    payload = {
        "source_owner": source_owner,
        "name": name,
        "full_name": full_name,
        "source_profile_id": f"github_{source_owner.lower()}",
        "collaborator_check": "ok",
    }
    payload.update(overrides)
    return GitHubAdminRepositoryRead(**payload)


def _profiles() -> list[GitHubAdminProfileRead]:
    return [
        GitHubAdminProfileRead(
            profile_id="github_lisa",
            owner="Lisa",
            github_host="github.com",
            can_transfer=True,
            has_token=True,
            source_path="/tmp/github_lisa.env",
            token="ghp_lisa",
        ),
        GitHubAdminProfileRead(
            profile_id="github_dd",
            owner="dd",
            github_host="github.com",
            can_transfer=True,
            has_token=True,
            source_path="/tmp/github_dd.env",
            token="ghp_dd",
        ),
        GitHubAdminProfileRead(
            profile_id="github_project_admin",
            owner="project",
            github_host="github.com",
            can_transfer=True,
            has_token=True,
            source_path="/tmp/github_project.env",
            token="ghp_project",
        ),
    ]


class _Gateway:
    def list_repositories(self, *, owner: str, visibility: str):
        return []

    def list_collaborators(self, *, owner: str, repo: str):
        return [owner]


def test_transfer_decisions_and_preflight_split_ready_blocked_unknown() -> None:
    repositories = [
        _repo("Lisa/repo-ready"),
        _repo(
            "Lisa/demo-playground",
            suggested_exclude=True,
            suggested_exclude_reasons=["heuristic: name or description suggests demo/test/playground usage"],
        ),
        _repo(
            "dd/old-repo",
            source_owner="dd",
            source_profile_id="github_dd",
            suggested_exclude=True,
            suggested_exclude_reasons=["archived repo excluded by request"],
        ),
    ]
    preflight = build_preflight_report(
        repositories=repositories,
        source_owners=["Lisa", "dd"],
        target_owner="project",
        profiles=_profiles(),
        post_actions=GitHubAdminPostActions(),
        gateway_factory=lambda profile: _Gateway(),
    )

    indexed_preflight = {item.full_name: item for item in preflight.repositories}
    assert indexed_preflight["Lisa/repo-ready"].readiness == GitHubAdminReadiness.READY
    assert indexed_preflight["Lisa/demo-playground"].readiness == GitHubAdminReadiness.UNKNOWN
    assert indexed_preflight["dd/old-repo"].readiness == GitHubAdminReadiness.BLOCKED

    decisions = build_transfer_decisions(
        repositories=repositories,
        source_owners=["Lisa", "dd"],
        target_owner="project",
        profiles=_profiles(),
        post_actions=GitHubAdminPostActions(),
        preflight=preflight,
    )
    indexed = {decision.full_name: decision for decision in decisions}
    assert indexed["Lisa/repo-ready"].action == "plan_transfer"
    assert indexed["Lisa/repo-ready"].readiness == GitHubAdminReadiness.READY
    assert indexed["Lisa/demo-playground"].action == "review"
    assert indexed["Lisa/demo-playground"].readiness == GitHubAdminReadiness.UNKNOWN
    assert indexed["dd/old-repo"].action == "skip"
    assert indexed["dd/old-repo"].readiness == GitHubAdminReadiness.BLOCKED


def test_transfer_plan_markdown_lists_preflight_sections() -> None:
    preflight = build_preflight_report(
        repositories=[_repo("Lisa/repo-a")],
        source_owners=["Lisa"],
        target_owner="project",
        profiles=_profiles(),
        post_actions=GitHubAdminPostActions(),
        gateway_factory=lambda profile: _Gateway(),
    )
    markdown = render_transfer_plan_markdown(
        run_id="ghplan_001",
        source_owners=["Lisa"],
        target_owner="project",
        decisions=[
            build_transfer_decisions(
                repositories=[_repo("Lisa/repo-a")],
                source_owners=["Lisa"],
                target_owner="project",
                profiles=_profiles(),
                post_actions=GitHubAdminPostActions(),
                preflight=preflight,
            )[0]
        ],
        preflight=preflight,
    )

    assert "# GitHub Admin Dry-Run Transfer Plan" in markdown
    assert "## preflight" in markdown
    assert "## ready_to_execute" in markdown
    assert "## blocked" in markdown
    assert "## unknown" in markdown
    assert "`Lisa/repo-a`" in markdown


def test_preflight_blocks_when_target_owner_profile_missing() -> None:
    preflight = build_preflight_report(
        repositories=[_repo("Lisa/repo-a")],
        source_owners=["Lisa"],
        target_owner="project",
        profiles=[profile for profile in _profiles() if profile.owner != "project"],
        post_actions=GitHubAdminPostActions(),
        gateway_factory=lambda profile: _Gateway(),
    )

    assert preflight.target_owner_probe is not None
    assert preflight.target_owner_probe.readiness == GitHubAdminReadiness.BLOCKED
    assert "missing target-owner profile" in preflight.target_owner_probe.reason
    assert preflight.repositories[0].readiness == GitHubAdminReadiness.BLOCKED

