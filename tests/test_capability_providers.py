from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from autoresearch.agents.opensource_searcher import OpenSourceLibrary, SearchResult
from autoresearch.core.adapters import (
    AppleCalendarAdapter,
    CapabilityDomain,
    CapabilityProviderRegistry,
    GitHubSearchAdapter,
    MCPContextProviderAdapter,
    OpenClawSkillProviderAdapter,
)
from autoresearch.core.adapters.contracts import CalendarQuery, GitHubRepositorySearchRequest
from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from orchestrator.mcp_context import MCPContextBlock


class _StubCalendarService:
    def read_calendar_today(self, calendar_name: str | None = None) -> dict[str, object]:
        return {
            "status": "success",
            "count": 1,
            "events": [
                {
                    "summary": "Design Review",
                    "start_date": "2026-03-28T10:00:00+08:00",
                    "end_date": "2026-03-28T11:00:00+08:00",
                    "location": "Meeting Room A",
                }
            ],
            "date": "2026-03-28",
            "calendar_name": calendar_name,
        }


class _StubGitHubSearcher:
    async def search_libraries(
        self,
        query: str,
        min_stars: int = 100,
        max_age_days: int = 365,
        language: str | None = "python",
        limit: int = 10,
    ) -> SearchResult:
        return SearchResult(
            query=query,
            total_count=1,
            libraries=[
                OpenSourceLibrary(
                    name="openclaw",
                    full_name="openclaw/openclaw",
                    stars=12345,
                    last_update=datetime(2026, 3, 20, tzinfo=timezone.utc).replace(tzinfo=None),
                    license="MIT",
                    language=language or "Python",
                    description="Telegram-first assistant",
                    url="https://github.com/openclaw/openclaw",
                    security_score=91.0,
                    maturity_score=88.0,
                )
            ],
        )


def test_apple_calendar_adapter_normalizes_events() -> None:
    adapter = AppleCalendarAdapter(service=_StubCalendarService())

    result = adapter.query_events(CalendarQuery(window="today", calendar_name="Work"))

    assert result.provider_id == "apple-calendar"
    assert result.status.value == "available"
    assert result.raw_count == 1
    assert result.events[0].summary == "Design Review"
    assert result.events[0].location == "Meeting Room A"


@pytest.mark.asyncio
async def test_github_search_adapter_normalizes_search_results() -> None:
    adapter = GitHubSearchAdapter(searcher=_StubGitHubSearcher())

    result = await adapter.search_repositories(
        GitHubRepositorySearchRequest(query="telegram assistant", language="python", limit=5)
    )

    assert result.provider_id == "github-search"
    assert result.status.value == "available"
    assert result.total_count == 1
    assert result.repositories[0].full_name == "openclaw/openclaw"
    assert result.repositories[0].metadata["last_update"].startswith("2026-03-20")


def test_openclaw_skill_provider_wraps_skill_service(tmp_path: Path) -> None:
    skill_root = tmp_path / "skills"
    skill_dir = skill_root / "daily_brief"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: Daily Brief\n"
        "description: Generate a concise daily brief\n"
        "---\n"
        "# Daily Brief\n"
        "Use this skill for daily summaries.\n",
        encoding="utf-8",
    )
    service = OpenClawSkillService(repo_root=tmp_path, skill_roots=[skill_root])
    adapter = OpenClawSkillProviderAdapter(service)

    catalog = adapter.list_skills()

    assert catalog.status.value == "available"
    assert catalog.skills[0].name == "Daily Brief"
    detail = adapter.get_skill("daily brief")
    assert detail is not None
    assert "daily summaries" in detail.content.lower()


@pytest.mark.asyncio
async def test_mcp_context_provider_lists_and_calls_tools() -> None:
    context = MCPContextBlock()
    context.register_tool(
        "echo_tool",
        {
            "description": "Echo payload",
            "handler": lambda payload: {"echo": payload},
        },
    )
    adapter = MCPContextProviderAdapter(context)

    tools = adapter.list_tools()
    result = await adapter.call_tool("echo_tool", {"message": "hi"})

    assert any(tool.name == "echo_tool" for tool in tools)
    assert result.status.value == "available"
    assert result.result["echo"]["message"] == "hi"


def test_capability_provider_registry_groups_providers() -> None:
    registry = CapabilityProviderRegistry()
    registry.register(AppleCalendarAdapter(service=_StubCalendarService()))
    registry.register(GitHubSearchAdapter(searcher=_StubGitHubSearcher()))

    descriptors = registry.list_descriptors()
    github_descriptors = registry.list_descriptors(domain=CapabilityDomain.GITHUB)

    assert len(descriptors) == 2
    assert len(github_descriptors) == 1
    assert github_descriptors[0].provider_id == "github-search"
