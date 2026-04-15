from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from github_admin.contracts import GitHubAdminInventoryRequest, GitHubAdminReadiness, GitHubAdminTransferPlanRequest
from autoresearch.core.services.github_admin import GitHubAdminService
from autoresearch.shared.store import InMemoryRepository


class FakeGateway:
    def __init__(self, *, owner_probe_mode: str = "ready") -> None:
        self._owner_probe_mode = owner_probe_mode
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
            "project": [],
        }
        self._collaborators = {
            ("Lisa", "client-portal"): ["Lisa", "dd"],
            ("Lisa", "demo-playground"): ["Lisa"],
        }

    def list_repositories(self, *, owner: str, visibility: str):
        assert visibility in {"public", "all"}
        if owner == "project" and self._owner_probe_mode == "missing":
            raise RuntimeError("GitHub API 404 for /orgs/project/repos: Not Found")
        return list(self._repos.get(owner, []))

    def list_collaborators(self, *, owner: str, repo: str):
        if (owner, repo) == ("dd", "ops-scripts"):
            raise RuntimeError("403 collaborator scope missing")
        return list(self._collaborators.get((owner, repo), [owner]))


def _write_profiles(root: Path, *, include_project: bool = True, dd_can_transfer: bool = True) -> None:
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
                f"CAN_TRANSFER={'true' if dd_can_transfer else 'false'}",
            ]
        ),
        encoding="utf-8",
    )
    if include_project:
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
    assert run.dry_run is True
    assert run.summary.repo_count == 3
    assert run.summary.excluded_repo_count == 2
    assert run.summary.failure_count == 1
    assert "inventory.json" in run.artifacts
    inventory_payload = json.loads((Path(run.run_dir) / "inventory.json").read_text(encoding="utf-8"))
    assert inventory_payload["dry_run"] is True
    assert inventory_payload["summary"]["repo_count"] == 3
    transfer_results = json.loads((Path(run.run_dir) / "transfer_results.json").read_text(encoding="utf-8"))
    invitation_results = json.loads((Path(run.run_dir) / "invitation_results.json").read_text(encoding="utf-8"))
    assert transfer_results["mode"] == "dry_run"
    assert transfer_results["executed"] is False
    assert transfer_results["reason"] == "real transfer not enabled"
    assert invitation_results["mode"] == "dry_run"
    assert invitation_results["executed"] is False
    repos = {item["full_name"]: item for item in inventory_payload["repositories"]}
    assert repos["Lisa/client-portal"]["other_collaborators"] == ["dd"]
    assert repos["Lisa/demo-playground"]["suggested_exclude"] is True
    assert repos["dd/ops-scripts"]["collaborator_check"] == "unavailable"


def test_transfer_plan_marks_ready_blocked_unknown_and_writes_plan_markdown(tmp_path: Path) -> None:
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
    assert run.dry_run is True
    assert run.summary.ready_to_execute_count == 1
    assert run.summary.blocked_count == 1
    assert run.summary.unknown_count == 1
    decisions = {item.full_name: item for item in run.decisions}
    assert decisions["Lisa/client-portal"].action == "plan_transfer"
    assert decisions["Lisa/client-portal"].readiness == GitHubAdminReadiness.READY
    assert decisions["Lisa/client-portal"].confirmation_profile_id == "github_project_admin"
    assert decisions["Lisa/client-portal"].planned_collaborators == ["dd"]
    assert decisions["Lisa/demo-playground"].action == "review"
    assert decisions["Lisa/demo-playground"].readiness == GitHubAdminReadiness.UNKNOWN
    assert decisions["dd/ops-scripts"].action == "skip"
    assert decisions["dd/ops-scripts"].readiness == GitHubAdminReadiness.BLOCKED
    assert run.preflight.target_owner_probe is not None
    assert run.preflight.target_owner_probe.readiness == GitHubAdminReadiness.READY
    transfer_results = json.loads((Path(run.run_dir) / "transfer_results.json").read_text(encoding="utf-8"))
    invitation_results = json.loads((Path(run.run_dir) / "invitation_results.json").read_text(encoding="utf-8"))
    assert transfer_results["mode"] == "dry_run"
    assert transfer_results["executed"] is False
    assert invitation_results["mode"] == "dry_run"
    assert invitation_results["executed"] is False
    plan_md = (Path(run.run_dir) / "plan.md").read_text(encoding="utf-8")
    assert "recommended_to_transfer" in plan_md
    assert "not_recommended_to_transfer" in plan_md
    assert "ready_to_execute" in plan_md
    assert "blocked" in plan_md
    assert "unknown" in plan_md


def test_transfer_plan_blocks_when_target_owner_is_unreachable(tmp_path: Path) -> None:
    _write_profiles(tmp_path)
    service = GitHubAdminService(
        repository=InMemoryRepository(),
        repo_root=tmp_path,
        gateway_factory=lambda profile: FakeGateway(owner_probe_mode="missing"),
        now_factory=lambda: datetime(2026, 4, 8, 11, 30, tzinfo=timezone.utc),
    )

    run = service.transfer_plan(
        GitHubAdminTransferPlanRequest(
            source_owners=["Lisa"],
            target_owner="project",
            visibility="public",
            include_archived=False,
            dry_run=True,
        )
    )

    assert run.preflight.target_owner_probe is not None
    assert run.preflight.target_owner_probe.readiness == GitHubAdminReadiness.BLOCKED
    assert "target owner probe failed" in run.preflight.target_owner_probe.reason
    assert run.summary.blocked_count >= 1


def test_transfer_plan_blocks_when_source_profile_is_missing(tmp_path: Path) -> None:
    _write_profiles(tmp_path, include_project=True)
    service = GitHubAdminService(
        repository=InMemoryRepository(),
        repo_root=tmp_path,
        gateway_factory=lambda profile: FakeGateway(),
        now_factory=lambda: datetime(2026, 4, 8, 11, 45, tzinfo=timezone.utc),
    )

    run = service.transfer_plan(
        GitHubAdminTransferPlanRequest(
            source_owners=["missing-owner"],
            target_owner="project",
            visibility="public",
            include_archived=False,
            dry_run=True,
        )
    )

    source_checks = [item for item in run.preflight.profile_isolation if item.role == "source"]
    assert source_checks[0].readiness == GitHubAdminReadiness.BLOCKED
    assert "missing source-owner profile" in source_checks[0].reason


def test_transfer_plan_blocks_when_source_profile_is_not_transfer_capable(tmp_path: Path) -> None:
    _write_profiles(tmp_path, dd_can_transfer=False)
    service = GitHubAdminService(
        repository=InMemoryRepository(),
        repo_root=tmp_path,
        gateway_factory=lambda profile: FakeGateway(),
        now_factory=lambda: datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc),
    )

    run = service.transfer_plan(
        GitHubAdminTransferPlanRequest(
            source_owners=["dd"],
            target_owner="project",
            visibility="public",
            include_archived=False,
            dry_run=True,
        )
    )

    source_checks = [item for item in run.preflight.profile_isolation if item.owner == "dd" and item.role == "source"]
    assert source_checks[0].readiness == GitHubAdminReadiness.BLOCKED
    assert "not transfer-capable" in source_checks[0].reason

