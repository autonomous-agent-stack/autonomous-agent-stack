from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient

from autoresearch.api.dependencies import get_capability_provider_registry
from autoresearch.api.main import app
from autoresearch.core.adapters import CapabilityDomain, CapabilityProviderDescriptorRead, CapabilityProviderRegistry
from autoresearch.core.adapters.contracts import (
    CalendarQuery,
    CalendarQueryResultRead,
    GitHubRepositoryCandidateRead,
    GitHubRepositorySearchResultRead,
    MCPToolDescriptorRead,
    SkillCatalogRead,
)
from autoresearch.shared.models import OpenClawSkillDetailRead, OpenClawSkillRead


class _StubCapabilityProvider:
    def __init__(
        self,
        *,
        provider_id: str,
        domain: CapabilityDomain,
        display_name: str,
        capabilities: list[str],
    ) -> None:
        self._descriptor = CapabilityProviderDescriptorRead(
            provider_id=provider_id,
            domain=domain,
            display_name=display_name,
            capabilities=capabilities,
            metadata={"stub": True},
        )

    def describe(self) -> CapabilityProviderDescriptorRead:
        return self._descriptor


class _StubSkillProvider(_StubCapabilityProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_id="openclaw-skills",
            domain=CapabilityDomain.SKILL,
            display_name="OpenClaw Skills",
            capabilities=["list_skills", "get_skill"],
        )
        self._summary = OpenClawSkillRead(
            name="Daily Brief",
            skill_key="daily_brief",
            description="Generate a concise daily brief",
            source="workspace",
            base_dir="/tmp/skills/daily_brief",
            file_path="/tmp/skills/daily_brief/SKILL.md",
            metadata={"stub": True},
        )

    def list_skills(self) -> SkillCatalogRead:
        return SkillCatalogRead(provider_id="openclaw-skills", status="available", skills=[self._summary])

    def get_skill(self, skill_name: str) -> OpenClawSkillDetailRead | None:
        if skill_name.strip().lower() not in {"daily brief", "daily_brief"}:
            return None
        return OpenClawSkillDetailRead(**self._summary.model_dump(), content="# Daily Brief\nUse this skill.\n")


class _StubMCPProvider(_StubCapabilityProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_id="mcp-context",
            domain=CapabilityDomain.MCP,
            display_name="MCP Context",
            capabilities=["list_tools"],
        )

    def list_tools(self) -> list[MCPToolDescriptorRead]:
        return [
            MCPToolDescriptorRead(
                name="echo_tool",
                description="Echo payload",
                metadata={"stub": True},
            )
        ]

    async def call_tool(self, tool_name: str, params: dict[str, object]) -> dict[str, object]:
        return {"tool_name": tool_name, "params": params}


class _StubCalendarProvider(_StubCapabilityProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_id="apple-calendar",
            domain=CapabilityDomain.CALENDAR,
            display_name="Apple Calendar",
            capabilities=["read_today", "read_range"],
        )

    def query_events(self, query: CalendarQuery) -> CalendarQueryResultRead:
        return CalendarQueryResultRead(
            provider_id="apple-calendar",
            status="available",
            events=[
                {
                    "summary": "Design Review",
                    "start_at": "2026-03-28T10:00:00+08:00",
                    "end_at": "2026-03-28T11:00:00+08:00",
                    "location": "Meeting Room A",
                    "metadata": {"calendar_name": query.calendar_name or "Work"},
                }
            ],
            raw_count=1,
            metadata={"window": query.window},
        )


class _StubGitHubProvider(_StubCapabilityProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_id="github-search",
            domain=CapabilityDomain.GITHUB,
            display_name="GitHub Search",
            capabilities=["search_repositories"],
        )

    async def search_repositories(self, request) -> GitHubRepositorySearchResultRead:
        return GitHubRepositorySearchResultRead(
            provider_id="github-search",
            status="available",
            query=request.query,
            total_count=1,
            repositories=[
                GitHubRepositoryCandidateRead(
                    name="openclaw",
                    full_name="openclaw/openclaw",
                    stars=12345,
                    language=request.language,
                    description="Telegram-first assistant",
                    url="https://github.com/openclaw/openclaw",
                    license="MIT",
                    metadata={"last_update": datetime(2026, 3, 20).isoformat()},
                )
            ],
        )


def _stub_registry() -> CapabilityProviderRegistry:
    registry = CapabilityProviderRegistry()
    registry.register(_StubCalendarProvider())
    registry.register(_StubGitHubProvider())
    registry.register(_StubSkillProvider())
    registry.register(_StubMCPProvider())
    return registry


def test_capability_health_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/capabilities/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_capability_providers_and_filter_by_domain() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            listed = client.get("/api/v1/capabilities/providers")
            filtered = client.get("/api/v1/capabilities/providers?domain=github")
    finally:
        app.dependency_overrides.clear()

    assert listed.status_code == 200
    assert [item["provider_id"] for item in listed.json()] == [
        "apple-calendar",
        "github-search",
        "mcp-context",
        "openclaw-skills",
    ]
    assert filtered.status_code == 200
    assert filtered.json() == [
        {
            "provider_id": "github-search",
            "domain": "github",
            "display_name": "GitHub Search",
            "status": "available",
            "capabilities": ["search_repositories"],
            "metadata": {"stub": True},
        }
    ]


def test_get_capability_provider_descriptor() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/capabilities/providers/github-search")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["provider_id"] == "github-search"
    assert response.json()["domain"] == "github"


def test_get_capability_provider_404_for_unknown_provider() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/capabilities/providers/missing-provider")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Capability provider not found"


def test_list_provider_skills_returns_catalog() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/capabilities/providers/openclaw-skills/skills")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_id"] == "openclaw-skills"
    assert payload["skills"][0]["skill_key"] == "daily_brief"


def test_get_provider_skill_returns_detail() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/capabilities/providers/openclaw-skills/skills/daily_brief")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "Daily Brief"
    assert "Use this skill" in payload["content"]


def test_list_provider_tools_returns_mcp_catalog() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/capabilities/providers/mcp-context/tools")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "echo_tool",
            "description": "Echo payload",
            "metadata": {"stub": True},
        }
    ]


def test_skill_endpoint_rejects_non_skill_provider() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/capabilities/providers/github-search/skills")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Capability provider has no skill catalog"


def test_tool_endpoint_rejects_non_mcp_provider() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/capabilities/providers/openclaw-skills/tools")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Capability provider has no tool catalog"


def test_query_provider_calendar_events_returns_normalized_payload() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/capabilities/providers/apple-calendar/calendar/events?window=today&calendar_name=Work"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_id"] == "apple-calendar"
    assert payload["events"][0]["summary"] == "Design Review"
    assert payload["metadata"]["window"] == "today"


def test_search_provider_github_repositories_returns_normalized_payload() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/capabilities/providers/github-search/github/search?query=telegram+assistant&language=python&limit=5"
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider_id"] == "github-search"
    assert payload["query"] == "telegram assistant"
    assert payload["repositories"][0]["full_name"] == "openclaw/openclaw"


def test_calendar_endpoint_rejects_non_calendar_provider() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/capabilities/providers/openclaw-skills/calendar/events")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Capability provider has no calendar query"


def test_github_endpoint_rejects_non_github_provider() -> None:
    app.dependency_overrides[get_capability_provider_registry] = _stub_registry

    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/capabilities/providers/mcp-context/github/search?query=abc")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Capability provider has no github search"
