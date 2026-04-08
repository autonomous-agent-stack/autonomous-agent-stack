from __future__ import annotations

from github_admin.contracts import (
    GitHubAdminPostActions,
    GitHubAdminProfileRead,
    GitHubAdminRepositoryRead,
)
from github_admin.transfer import build_transfer_decisions, render_transfer_plan_markdown


def _repo(full_name: str, *, source_owner: str = "Lisa", **overrides) -> GitHubAdminRepositoryRead:
    name = full_name.split("/", 1)[1]
    payload = {
        "source_owner": source_owner,
        "name": name,
        "full_name": full_name,
        "source_profile_id": f"github_{source_owner.lower()}",
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


def test_transfer_decisions_split_planned_review_and_skip() -> None:
    decisions = build_transfer_decisions(
        repositories=[
            _repo("Lisa/repo-a", other_collaborators=["dd"]),
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
        ],
        source_owners=["Lisa", "dd"],
        target_owner="project",
        profiles=_profiles(),
        post_actions=GitHubAdminPostActions(),
    )

    indexed = {decision.full_name: decision for decision in decisions}
    assert indexed["Lisa/repo-a"].action == "plan_transfer"
    assert indexed["Lisa/repo-a"].planned_collaborators == ["dd"]
    assert indexed["Lisa/demo-playground"].action == "review"
    assert indexed["dd/old-repo"].action == "skip"


def test_transfer_plan_markdown_lists_all_sections() -> None:
    markdown = render_transfer_plan_markdown(
        run_id="ghplan_001",
        source_owners=["Lisa", "dd"],
        target_owner="project",
        decisions=[
            build_transfer_decisions(
                repositories=[_repo("Lisa/repo-a")],
                source_owners=["Lisa", "dd"],
                target_owner="project",
                profiles=_profiles(),
                post_actions=GitHubAdminPostActions(),
            )[0]
        ],
    )

    assert "# GitHub Admin Dry-Run Transfer Plan" in markdown
    assert "## recommended_to_transfer" in markdown
    assert "`Lisa/repo-a`" in markdown
    assert "## not_recommended_to_transfer" in markdown
    assert "## reasons" in markdown
