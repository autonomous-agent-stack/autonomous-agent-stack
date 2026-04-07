from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from autoresearch.api.main import app
from autoresearch.api.routers.github_assistant import (
    get_github_assistant_service,
    get_github_assistant_service_registry,
)
from autoresearch.github_assistant.config import resolve_profile
from autoresearch.github_assistant.service import GitHubAssistantService
from tests.test_github_assistant import (
    FakeGitHubGateway,
    FakeGitPromotionProvider,
    FakeWorkspaceManager,
    _init_demo_repo,
    _issue,
    _repo_config,
    _write_profile_root,
    _write_profiles_catalog,
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


def test_github_assistant_health_route_reflects_degraded_auth_state(tmp_path: Path) -> None:
    _write_template_root(tmp_path, repos=[_repo_config()])
    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=FakeGitHubGateway(installed=True, authenticated=False, accessible_repos=set()),
        executor_runner=lambda **_: None,
    )
    app.dependency_overrides[get_github_assistant_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/github-assistant/health")
            assert response.status_code == 200
            payload = response.json()

        assert payload["status"] == "degraded"
        assert payload["doctor_ok"] is False
        assert payload["gh_auth_ok"] is False
        assert payload["expected_github_login"] == "demo-bot"
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
        assert payload["profile_id"] == "default"
        assert payload["profile_display_name"] == "Default"
        assert "patch.diff" in payload["artifacts"]
        assert payload["run_dir"].endswith("/issue-21")
    finally:
        app.dependency_overrides.clear()


def test_github_assistant_publish_youtube_route_returns_artifacts_and_summary(tmp_path: Path) -> None:
    source_repo = tmp_path / "source-repo"
    source_repo.mkdir()
    _init_demo_repo(source_repo)
    _write_template_root(
        tmp_path,
        repos=[
            _repo_config(
                allowed_paths=["src/**", "tests/**", "docs/youtube-ingest/**"],
                youtube_ingest={
                    "enabled": True,
                    "output_dir": "docs/youtube-ingest",
                    "keywords": ["desktop agent"],
                },
            )
        ],
    )

    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=FakeGitHubGateway(accessible_repos={"acme/demo"}),
        workspace_manager=FakeWorkspaceManager(source_repo, tmp_path / "sandboxes"),
        promotion_provider=FakeGitPromotionProvider(),
        now_factory=lambda: datetime(2026, 4, 7, 0, 45, tzinfo=timezone.utc),
    )
    app.dependency_overrides[get_github_assistant_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/github-assistant/publish-youtube",
                json={
                    "video_id": "video-001",
                    "source_url": "https://www.youtube.com/watch?v=video-001",
                    "title": "Desktop agent notes",
                    "digest_id": "ytdigest_001",
                    "digest_content": "Digest content.",
                },
            )
            assert response.status_code == 200
            payload = response.json()

        assert payload["publish"]["repo"] == "acme/demo"
        assert payload["publish"]["pr_url"] == "https://github.com/acme/demo/pull/7"
        assert payload["summary"]["status"] == "draft_pr_opened"
        assert payload["profile_id"] == "default"
        assert "patch.diff" in payload["artifacts"]
    finally:
        app.dependency_overrides.clear()


def test_github_assistant_execute_route_surfaces_auth_remediation(tmp_path: Path) -> None:
    _write_template_root(tmp_path, repos=[_repo_config()])

    class AuthFailingGitHubGateway(FakeGitHubGateway):
        def fetch_issue(self, repo: str, issue_number: int):  # type: ignore[override]
            raise RuntimeError("gh auth status failed: token invalid")

    service = GitHubAssistantService(
        repo_root=tmp_path,
        github=AuthFailingGitHubGateway(authenticated=False),
        executor_runner=lambda **_: None,
    )
    app.dependency_overrides[get_github_assistant_service] = lambda: service

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/github-assistant/execute",
                json={"repo": "acme/demo", "issue_number": 21},
            )
            assert response.status_code == 503
            detail = response.json()["detail"]

        assert "GitHub auth unavailable." in detail
        assert "gh auth login" in detail
        assert "./assistant doctor" in detail
    finally:
        app.dependency_overrides.clear()


def test_github_assistant_health_route_uses_profile_query_param(tmp_path: Path) -> None:
    _write_template_root(
        tmp_path,
        repos=[_repo_config(repo="acme/root")],
        assistant_overrides={"github_login": "root-bot"},
    )
    _write_profile_root(
        tmp_path,
        "ops",
        repos=[_repo_config(repo="acme/ops")],
        assistant_overrides={"github_login": "ops-bot"},
    )
    _write_profiles_catalog(
        tmp_path,
        profiles=[
            {
                "id": "default",
                "display_name": "Default",
                "root": ".",
                "github_host": "github.com",
                "gh_config_dir": ".gh-profiles/default",
            },
            {
                "id": "ops",
                "display_name": "Ops",
                "root": "profiles/ops",
                "github_host": "github.com",
                "gh_config_dir": ".gh-profiles/ops",
            },
        ],
    )
    services = {
        "default": GitHubAssistantService(
            repo_root=tmp_path,
            profile=resolve_profile(tmp_path, "default"),
            github=FakeGitHubGateway(installed=True, authenticated=False, accessible_repos=set()),
            executor_runner=lambda **_: None,
        ),
        "ops": GitHubAssistantService(
            repo_root=tmp_path,
            profile=resolve_profile(tmp_path, "ops"),
            github=FakeGitHubGateway(accessible_repos={"acme/ops"}),
            executor_runner=lambda **_: None,
        ),
    }

    def override_service(profile: str | None = None) -> GitHubAssistantService:
        return services[profile or "default"]

    app.dependency_overrides[get_github_assistant_service] = override_service

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/github-assistant/health", params={"profile": "ops"})
            assert response.status_code == 200
            payload = response.json()

        assert payload["profile_id"] == "ops"
        assert payload["profile_display_name"] == "Ops"
        assert payload["expected_github_login"] == "ops-bot"
        assert payload["managed_repo_count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_github_assistant_profiles_route_returns_all_profiles(tmp_path: Path) -> None:
    _write_template_root(
        tmp_path,
        repos=[_repo_config(repo="acme/root")],
        assistant_overrides={"github_login": "root-bot"},
    )
    _write_profile_root(
        tmp_path,
        "ops",
        repos=[_repo_config(repo="acme/ops")],
        assistant_overrides={"github_login": "ops-bot"},
    )
    _write_profiles_catalog(
        tmp_path,
        profiles=[
            {
                "id": "default",
                "display_name": "Default",
                "root": ".",
                "github_host": "github.com",
                "gh_config_dir": ".gh-profiles/default",
            },
            {
                "id": "ops",
                "display_name": "Ops",
                "root": "profiles/ops",
                "github_host": "github.com",
                "gh_config_dir": ".gh-profiles/ops",
            },
        ],
    )
    services = {
        "default": GitHubAssistantService(
            repo_root=tmp_path,
            profile=resolve_profile(tmp_path, "default"),
            github=FakeGitHubGateway(installed=True, authenticated=False, accessible_repos=set()),
            executor_runner=lambda **_: None,
        ),
        "ops": GitHubAssistantService(
            repo_root=tmp_path,
            profile=resolve_profile(tmp_path, "ops"),
            github=FakeGitHubGateway(accessible_repos={"acme/ops"}),
            executor_runner=lambda **_: None,
        ),
    }

    class FakeRegistry:
        def default_profile_id(self) -> str:
            return "default"

        def list_profiles(self):
            return [services["default"].profile, services["ops"].profile]

        def get(self, profile_id: str | None = None) -> GitHubAssistantService:
            return services[profile_id or "default"]

    app.dependency_overrides[get_github_assistant_service_registry] = lambda: FakeRegistry()

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/github-assistant/profiles")
            assert response.status_code == 200
            payload = response.json()

        assert payload["default_profile"] == "default"
        assert {item["profile_id"] for item in payload["profiles"]} == {"default", "ops"}
        ops_profile = next(item for item in payload["profiles"] if item["profile_id"] == "ops")
        assert ops_profile["profile_display_name"] == "Ops"
        assert ops_profile["managed_repo_count"] == 1
        assert ops_profile["doctor_ok"] is True
    finally:
        app.dependency_overrides.clear()
