from __future__ import annotations

from collections.abc import Iterable

from autoresearch.core.adapters.contracts import (
    CapabilityDomain,
    CapabilityProvider,
    CapabilityProviderDescriptorRead,
)


class CapabilityProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, CapabilityProvider] = {}

    def register(self, provider: CapabilityProvider) -> None:
        descriptor = provider.describe()
        self._providers[descriptor.provider_id] = provider

    def register_many(self, providers: Iterable[CapabilityProvider]) -> None:
        for provider in providers:
            self.register(provider)

    def get(self, provider_id: str) -> CapabilityProvider | None:
        return self._providers.get(provider_id)

    def list_descriptors(
        self,
        *,
        domain: CapabilityDomain | None = None,
    ) -> list[CapabilityProviderDescriptorRead]:
        descriptors = [provider.describe() for provider in self._providers.values()]
        descriptors.sort(key=lambda item: (item.domain.value, item.provider_id))
        if domain is None:
            return descriptors
        return [item for item in descriptors if item.domain == domain]
