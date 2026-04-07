from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from autoresearch.api.main import app
from autoresearch.api.routers.github_admin import get_github_admin_service
from autoresearch.core.services.github_admin import GitHubAdminService
from autoresearch.shared.store import InMemoryRepository


class FakeGateway:
    def list_repositories(self, *, owner: str, visibility: str):
        return [
            {
                "name": "client-portal",
                "full_name": f"{owner}/client-portal",
                "visibility": visibility,
                "archived": False,
                "fork": False,
                "description": "Production app",
                "html_url": f"https://github.com/{owner}/client-portal",
                "default_branch": "main",
                "language": "Python",
                "stargazers_count": 12,
                "forks_count": 2,
            }
        ]

    def list_collaborators(self, *, owner: str, repo: str):
        return [owner]


def _write_profiles(root: Path) -> None:
    config_dir = root / "configs" / "github_profiles"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "lisa.env").write_text(
        "PROFILE_ID=github_lisa\nOWNER=Lisa\nGH_HOST=github.com\nGH_TOKEN=ghp_lisa\nCAN_TRANSFER=true\n",
        encoding="utf-8",
    )
    (config_dir / "project.env").write_text(
        "PROFILE_ID=github_project_admin\nOWNER=project\nGH_HOST=github.com\nGH_TOKEN=ghp_project\nCAN_TRANSFER=true\n",
        encoding="utf-8",
    )


def test_github_admin_routes_return_dry_run_payloads(tmp_path: Path) -> None:
    _write_profiles(tmp_path)
    service = GitHubAdminService(
        repository=InMemoryRepository(),
        repo_root=tmp_path,
        gateway_factory=lambda profile: FakeGateway(),
        now_factory=lambda: datetime(2026, 4, 8, 12, 0, tzinfo=timezone.utc),
    )
    app.dependency_overrides[get_github_admin_service] = lambda: service

    try:
        with TestClient(app) as client:
            inventory = client.post(
                "/api/jobs/github-admin/inventory",
                json={
                    "owners": ["Lisa"],
                    "visibility": "public",
                    "target_owner": "project",
                    "include_archived": False,
                },
            )
            assert inventory.status_code == 200
            inventory_payload = inventory.json()
            assert inventory_payload["run_type"] == "inventory"
            assert inventory_payload["dry_run"] is True
            assert inventory_payload["summary"]["repo_count"] == 1

            plan = client.post(
                "/api/jobs/github-admin/transfer-plan",
                json={
                    "source_owners": ["Lisa"],
                    "target_owner": "project",
                    "visibility": "public",
                    "include_archived": False,
                    "dry_run": True,
                },
            )
            assert plan.status_code == 200
            plan_payload = plan.json()
            assert plan_payload["run_type"] == "transfer_plan"
            assert plan_payload["dry_run"] is True
            assert plan_payload["decisions"][0]["action"] == "plan_transfer"

            execute = client.post("/api/jobs/github-admin/execute-transfer")
            assert execute.status_code == 501
            assert "dry-run only" in execute.json()["detail"].lower()
            assert "not implemented yet" in execute.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()
