from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from github_admin.contracts import GitHubAdminInventoryRequest, GitHubAdminTransferPlanRequest
from autoresearch.core.services.github_admin import GitHubAdminService
from autoresearch.shared.store import InMemoryRepository


class FakeGateway:
    def __init__(self) -> None:
        self._repos = {
            "Lisa": [
                {
                    "name": "client-portal",
                    "full_name": "Lisa/client-portal",
                    "visibility": "public",
                    "archived": False,
                    "fork": False,
                    "description": "Production app",
                    "html_url": "https://github.com/Lisa/client-portal",
                    "default_branch": "main",
                    "language": "Python",
                    "stargazers_count": 12,
                    "forks_count": 2,
                },
                {
                    "name": "demo-playground",
                    "full_name": "Lisa/demo-playground",
                    "visibility": "public",
                    "archived": False,
                    "fork": False,
                    "description": "Demo repo",
                    "html_url": "https://github.com/Lisa/demo-playground",
                    "default_branch": "main",
                    "language": "Python",
                    "stargazers_count": 0,
                    "forks_count": 0,
                },
            ],
            "dd": [
                {
                    "name": "ops-scripts",
                    "full_name": "dd/ops-scripts",
                    "visibility": "public",
                    "archived": True,
                    "fork": False,
                    "description": "Ops utilities",
                    "html_url": "https://github.com/dd/ops-scripts",
                    "default_branch": "main",
                    "language": "Shell",
                    "stargazers_count": 1,
                    "forks_count": 0,
                }
            ],
        }
        self._collaborators = {
            ("Lisa", "client-portal"): ["Lisa", "dd"],
            ("Lisa", "demo-playground"): ["Lisa"],
        }

    def list_repositories(self, *, owner: str, visibility: str):
        assert visibility == "public"
        return list(self._repos.get(owner, []))

    def list_collaborators(self, *, owner: str, repo: str):
        if (owner, repo) == ("dd", "ops-scripts"):
            raise RuntimeError("403 collaborator scope missing")
        return list(self._collaborators.get((owner, repo), [owner]))


def _write_profiles(root: Path) -> None:
    config_dir = root / "configs" / "github_profiles"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "lisa.env").write_text(
        "\n".join(
            [
                "PROFILE_ID=github_lisa",
                "OWNER=Lisa",
                "GH_HOST=github.com",
                "GH_TOKEN=ghp_lisa",
                "CAN_TRANSFER=true",
            ]
        ),
        encoding="utf-8",
    )
    (config_dir / "dd.env").write_text(
        "\n".join(
            [
                "PROFILE_ID=github_dd",
                "OWNER=dd",
                "GH_HOST=github.com",
                "GH_TOKEN=ghp_dd",
                "CAN_TRANSFER=true",
            ]
        ),
        encoding="utf-8",
    )
    (config_dir / "project.env").write_text(
        "\n".join(
            [
                "PROFILE_ID=github_project_admin",
                "OWNER=project",
                "GH_HOST=github.com",
                "GH_TOKEN=ghp_project",
                "CAN_TRANSFER=true",
            ]
        ),
        encoding="utf-8",
    )


def test_inventory_run_writes_artifacts_and_annotations_repos(tmp_path: Path) -> None:
    _write_profiles(tmp_path)
    service = GitHubAdminService(
        repository=InMemoryRepository(),
        repo_root=tmp_path,
        gateway_factory=lambda profile: FakeGateway(),
        now_factory=lambda: datetime(2026, 4, 8, 10, 0, tzinfo=timezone.utc),
    )

    run = service.inventory(
        GitHubAdminInventoryRequest(
            owners=["Lisa", "dd"],
            visibility="public",
            target_owner="project",
            include_archived=False,
        )
    )

    assert run.run_type.value == "inventory"
    assert run.summary.repo_count == 3
    assert run.summary.excluded_repo_count == 2
    assert run.summary.failure_count == 1
    assert "inventory.json" in run.artifacts
    inventory_payload = json.loads((Path(run.run_dir) / "inventory.json").read_text(encoding="utf-8"))
    assert inventory_payload["summary"]["repo_count"] == 3
    repos = {item["full_name"]: item for item in inventory_payload["repositories"]}
    assert repos["Lisa/client-portal"]["other_collaborators"] == ["dd"]
    assert repos["Lisa/demo-playground"]["suggested_exclude"] is True
    assert repos["dd/ops-scripts"]["collaborator_check"] == "unavailable"


def test_transfer_plan_marks_review_and_writes_plan_markdown(tmp_path: Path) -> None:
    _write_profiles(tmp_path)
    service = GitHubAdminService(
        repository=InMemoryRepository(),
        repo_root=tmp_path,
        gateway_factory=lambda profile: FakeGateway(),
        now_factory=lambda: datetime(2026, 4, 8, 11, 0, tzinfo=timezone.utc),
    )

    run = service.transfer_plan(
        GitHubAdminTransferPlanRequest(
            source_owners=["Lisa", "dd"],
            target_owner="project",
            visibility="public",
            include_archived=False,
            dry_run=True,
        )
    )

    assert run.run_type.value == "transfer_plan"
    decisions = {item.full_name: item for item in run.decisions}
    assert decisions["Lisa/client-portal"].action == "plan_transfer"
    assert decisions["Lisa/client-portal"].confirmation_profile_id == "github_project_admin"
    assert decisions["Lisa/client-portal"].planned_collaborators == ["dd"]
    assert decisions["Lisa/demo-playground"].action == "review"
    assert decisions["dd/ops-scripts"].action == "skip"
    plan_md = (Path(run.run_dir) / "plan.md").read_text(encoding="utf-8")
    assert "Planned Transfers" in plan_md
    assert "`Lisa/client-portal`" in plan_md
    assert "Manual Review" in plan_md
