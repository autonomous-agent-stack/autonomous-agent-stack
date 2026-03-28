from __future__ import annotations

from enum import Enum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from autoresearch.shared.models import OpenClawSkillDetailRead, OpenClawSkillRead, StrictModel


class CapabilityDomain(str, Enum):
    CALENDAR = "calendar"
    GITHUB = "github"
    SKILL = "skill"
    MCP = "mcp"


class ProviderStatus(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class CapabilityProviderDescriptorRead(StrictModel):
    provider_id: str
    domain: CapabilityDomain
    display_name: str
    status: ProviderStatus = ProviderStatus.AVAILABLE
    capabilities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CalendarQuery(StrictModel):
    window: str = "today"
    start_date: str | None = None
    end_date: str | None = None
    calendar_name: str | None = None


class CalendarEventRead(StrictModel):
    summary: str
    start_at: str | None = None
    end_at: str | None = None
    location: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CalendarQueryResultRead(StrictModel):
    provider_id: str
    status: ProviderStatus
    events: list[CalendarEventRead] = Field(default_factory=list)
    raw_count: int = 0
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GitHubRepositorySearchRequest(StrictModel):
    query: str = Field(..., min_length=1)
    min_stars: int = 100
    max_age_days: int = 365
    language: str | None = "python"
    limit: int = 10


class GitHubRepositoryCandidateRead(StrictModel):
    name: str
    full_name: str
    stars: int
    language: str | None = None
    description: str = ""
    url: str = ""
    license: str = "Unknown"
    security_score: float | None = None
    maturity_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GitHubRepositorySearchResultRead(StrictModel):
    provider_id: str
    status: ProviderStatus
    query: str
    total_count: int = 0
    repositories: list[GitHubRepositoryCandidateRead] = Field(default_factory=list)
    error: str | None = None


class SkillCatalogRead(StrictModel):
    provider_id: str
    status: ProviderStatus
    skills: list[OpenClawSkillRead] = Field(default_factory=list)
    error: str | None = None


class MCPToolDescriptorRead(StrictModel):
    name: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResultRead(StrictModel):
    provider_id: str
    tool_name: str
    status: ProviderStatus
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


@runtime_checkable
class CapabilityProvider(Protocol):
    def describe(self) -> CapabilityProviderDescriptorRead: ...


@runtime_checkable
class CalendarAdapter(CapabilityProvider, Protocol):
    def query_events(self, query: CalendarQuery) -> CalendarQueryResultRead: ...


@runtime_checkable
class GitHubAdapter(CapabilityProvider, Protocol):
    async def search_repositories(
        self,
        request: GitHubRepositorySearchRequest,
    ) -> GitHubRepositorySearchResultRead: ...


@runtime_checkable
class SkillProvider(CapabilityProvider, Protocol):
    def list_skills(self) -> SkillCatalogRead: ...

    def get_skill(self, skill_name: str) -> OpenClawSkillDetailRead | None: ...


@runtime_checkable
class MCPProvider(CapabilityProvider, Protocol):
    def list_tools(self) -> list[MCPToolDescriptorRead]: ...

    async def call_tool(self, tool_name: str, params: dict[str, Any]) -> MCPToolCallResultRead: ...
