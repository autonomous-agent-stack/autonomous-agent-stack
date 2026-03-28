from __future__ import annotations

from autoresearch.core.adapters.contracts import (
    CapabilityDomain,
    CapabilityProviderDescriptorRead,
    ProviderStatus,
    SkillCatalogRead,
    SkillProvider,
)
from autoresearch.core.services.openclaw_skills import OpenClawSkillService
from autoresearch.shared.models import OpenClawSkillDetailRead


class OpenClawSkillProviderAdapter(SkillProvider):
    def __init__(self, service: OpenClawSkillService) -> None:
        self._service = service

    def describe(self) -> CapabilityProviderDescriptorRead:
        return CapabilityProviderDescriptorRead(
            provider_id="openclaw-skills",
            domain=CapabilityDomain.SKILL,
            display_name="OpenClaw Skills",
            capabilities=["list_skills", "get_skill"],
            metadata={},
        )

    def list_skills(self) -> SkillCatalogRead:
        try:
            skills = self._service.list_skills()
        except Exception as exc:
            return SkillCatalogRead(
                provider_id="openclaw-skills",
                status=ProviderStatus.DEGRADED,
                skills=[],
                error=str(exc),
            )
        return SkillCatalogRead(
            provider_id="openclaw-skills",
            status=ProviderStatus.AVAILABLE,
            skills=skills,
        )

    def get_skill(self, skill_name: str) -> OpenClawSkillDetailRead | None:
        return self._service.get_skill(skill_name)
