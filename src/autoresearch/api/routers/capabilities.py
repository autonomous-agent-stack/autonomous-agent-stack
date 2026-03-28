from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from autoresearch.api.dependencies import get_capability_provider_registry
from autoresearch.core.adapters import (
    CalendarAdapter,
    CapabilityDomain,
    CapabilityProviderDescriptorRead,
    CapabilityProviderRegistry,
    GitHubAdapter,
    MCPProvider,
    SkillProvider,
)
from autoresearch.core.adapters.contracts import (
    CalendarQuery,
    CalendarQueryResultRead,
    GitHubRepositorySearchRequest,
    GitHubRepositorySearchResultRead,
    MCPToolDescriptorRead,
    SkillCatalogRead,
)
from autoresearch.shared.models import OpenClawSkillDetailRead


router = APIRouter(prefix="/api/v1/capabilities", tags=["capabilities"])


@router.get("/health")
def capability_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/providers", response_model=list[CapabilityProviderDescriptorRead])
def list_capability_providers(
    domain: CapabilityDomain | None = Query(default=None),
    registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
) -> list[CapabilityProviderDescriptorRead]:
    return registry.list_descriptors(domain=domain)


@router.get("/providers/{provider_id}", response_model=CapabilityProviderDescriptorRead)
def get_capability_provider(
    provider_id: str,
    registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
) -> CapabilityProviderDescriptorRead:
    provider = _get_provider_or_404(registry=registry, provider_id=provider_id)
    return provider.describe()


@router.get("/providers/{provider_id}/skills", response_model=SkillCatalogRead)
def list_provider_skills(
    provider_id: str,
    registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
) -> SkillCatalogRead:
    provider = _require_skill_provider(registry=registry, provider_id=provider_id)
    return provider.list_skills()


@router.get("/providers/{provider_id}/skills/{skill_name}", response_model=OpenClawSkillDetailRead)
def get_provider_skill(
    provider_id: str,
    skill_name: str,
    registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
) -> OpenClawSkillDetailRead:
    provider = _require_skill_provider(registry=registry, provider_id=provider_id)
    skill = provider.get_skill(skill_name)
    if skill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")
    return skill


@router.get("/providers/{provider_id}/tools", response_model=list[MCPToolDescriptorRead])
def list_provider_tools(
    provider_id: str,
    registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
) -> list[MCPToolDescriptorRead]:
    provider = _require_mcp_provider(registry=registry, provider_id=provider_id)
    return provider.list_tools()


@router.get("/providers/{provider_id}/calendar/events", response_model=CalendarQueryResultRead)
def query_provider_calendar_events(
    provider_id: str,
    window: str = Query(default="today"),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    calendar_name: str | None = Query(default=None),
    registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
) -> CalendarQueryResultRead:
    provider = _require_calendar_provider(registry=registry, provider_id=provider_id)
    return provider.query_events(
        CalendarQuery(
            window=window,
            start_date=start_date,
            end_date=end_date,
            calendar_name=calendar_name,
        )
    )


@router.get("/providers/{provider_id}/github/search", response_model=GitHubRepositorySearchResultRead)
async def search_provider_github_repositories(
    provider_id: str,
    query: str = Query(..., min_length=1),
    min_stars: int = Query(default=100, ge=0),
    max_age_days: int = Query(default=365, ge=1),
    language: str | None = Query(default="python"),
    limit: int = Query(default=10, ge=1, le=100),
    registry: CapabilityProviderRegistry = Depends(get_capability_provider_registry),
) -> GitHubRepositorySearchResultRead:
    provider = _require_github_provider(registry=registry, provider_id=provider_id)
    return await provider.search_repositories(
        GitHubRepositorySearchRequest(
            query=query,
            min_stars=min_stars,
            max_age_days=max_age_days,
            language=language,
            limit=limit,
        )
    )


def _get_provider_or_404(*, registry: CapabilityProviderRegistry, provider_id: str):
    provider = registry.get(provider_id)
    if provider is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability provider not found")
    return provider


def _require_skill_provider(*, registry: CapabilityProviderRegistry, provider_id: str) -> SkillProvider:
    provider = _get_provider_or_404(registry=registry, provider_id=provider_id)
    if not isinstance(provider, SkillProvider):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability provider has no skill catalog")
    return provider


def _require_mcp_provider(*, registry: CapabilityProviderRegistry, provider_id: str) -> MCPProvider:
    provider = _get_provider_or_404(registry=registry, provider_id=provider_id)
    if not isinstance(provider, MCPProvider):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability provider has no tool catalog")
    return provider


def _require_calendar_provider(*, registry: CapabilityProviderRegistry, provider_id: str) -> CalendarAdapter:
    provider = _get_provider_or_404(registry=registry, provider_id=provider_id)
    if not isinstance(provider, CalendarAdapter):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability provider has no calendar query")
    return provider


def _require_github_provider(*, registry: CapabilityProviderRegistry, provider_id: str) -> GitHubAdapter:
    provider = _get_provider_or_404(registry=registry, provider_id=provider_id)
    if not isinstance(provider, GitHubAdapter):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Capability provider has no github search")
    return provider
