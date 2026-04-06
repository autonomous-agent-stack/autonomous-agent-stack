from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from autoresearch.api.main import app
from autoresearch.api.routers.github_assistant import get_github_assistant_service
from autoresearch.github_assistant.service import GitHubAssistantService
from tests.test_github_assistant import (
    FakeGitHubGateway,
    FakeGitPromotionProvider,
    FakeWorkspaceManager,
    _init_demo_repo,
    _issue,
    _repo_config,
    _write_template_root,
)


def test_github_assistant_doctor_route_surfaces_auth_failure(tmp_path: Path) -> None:
    _write_template_root(tmp_path, repos=[_repo_config()])
    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=FakeGitHubGateway(installed=True, authenticated=False, accessible_repos=set()),
        executor_runner=lambda **_: None,
    )
    app.dependency_overrides[get_github_assistant_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/github-assistant/doctor")
            assert response.status_code == 200
            payload = response.json()

        assert payload["ok"] is False
        checks = {item["name"]: item for item in payload["checks"]}
        assert checks["gh auth"]["status"] == "FAIL"
        assert checks["repo:acme/demo"]["status"] == "WARN"
    finally:
        app.dependency_overrides.clear()


def test_github_assistant_execute_route_returns_artifacts_and_summary(tmp_path: Path) -> None:
    source_repo = tmp_path / "source-repo"
    source_repo.mkdir()
    _init_demo_repo(source_repo)
    _write_template_root(tmp_path, repos=[_repo_config()])

    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=FakeGitHubGateway(
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
        ),
        workspace_manager=FakeWorkspaceManager(source_repo, tmp_path / "sandboxes"),
        promotion_provider=FakeGitPromotionProvider(),
        executor_runner=lambda *, workspace, **_: (workspace / "src" / "app.py").write_text("VALUE = 2\n", encoding="utf-8"),
        now_factory=lambda: datetime(2026, 4, 7, 0, 30, tzinfo=timezone.utc),
    )
    app.dependency_overrides[get_github_assistant_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/github-assistant/execute",
                json={"repo": "acme/demo", "issue_number": 21},
            )
            assert response.status_code == 200
            payload = response.json()

        assert payload["summary"]["status"] == "draft_pr_opened"
        assert payload["summary"]["pr_url"] == "https://github.com/acme/demo/pull/7"
        assert "patch.diff" in payload["artifacts"]
        assert payload["run_dir"].endswith("/issue-21")
    finally:
        app.dependency_overrides.clear()
