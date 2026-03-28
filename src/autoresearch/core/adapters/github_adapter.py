from __future__ import annotations

from autoresearch.agents.opensource_searcher import GitHubSearcher

from autoresearch.core.adapters.contracts import (
    CapabilityDomain,
    CapabilityProviderDescriptorRead,
    GitHubAdapter,
    GitHubRepositoryCandidateRead,
    GitHubRepositorySearchRequest,
    GitHubRepositorySearchResultRead,
    ProviderStatus,
)


class GitHubSearchAdapter(GitHubAdapter):
    def __init__(self, searcher: GitHubSearcher | None = None) -> None:
        self._searcher = searcher or GitHubSearcher()

    def describe(self) -> CapabilityProviderDescriptorRead:
        return CapabilityProviderDescriptorRead(
            provider_id="github-search",
            domain=CapabilityDomain.GITHUB,
            display_name="GitHub Search",
            capabilities=["search_repositories"],
            metadata={"source": "github_api_or_fallback"},
        )

    async def search_repositories(
        self,
        request: GitHubRepositorySearchRequest,
    ) -> GitHubRepositorySearchResultRead:
        try:
            result = await self._searcher.search_libraries(
                query=request.query,
                min_stars=request.min_stars,
                max_age_days=request.max_age_days,
                language=request.language,
                limit=request.limit,
            )
        except Exception as exc:
            return GitHubRepositorySearchResultRead(
                provider_id="github-search",
                status=ProviderStatus.DEGRADED,
                query=request.query,
                total_count=0,
                repositories=[],
                error=str(exc),
            )

        repositories = [
            GitHubRepositoryCandidateRead(
                name=item.name,
                full_name=item.full_name,
                stars=item.stars,
                language=item.language,
                description=item.description,
                url=item.url,
                license=item.license,
                security_score=item.security_score,
                maturity_score=item.maturity_score,
                metadata={"last_update": item.last_update.isoformat()},
            )
            for item in result.libraries
        ]
        return GitHubRepositorySearchResultRead(
            provider_id="github-search",
            status=ProviderStatus.AVAILABLE,
            query=result.query,
            total_count=result.total_count,
            repositories=repositories,
        )
