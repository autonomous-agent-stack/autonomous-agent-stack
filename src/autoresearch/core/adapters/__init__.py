"""
Adapters for external frameworks
"""
from .calendar_adapter import AppleCalendarAdapter
from .contracts import (
    CalendarAdapter,
    CapabilityDomain,
    CapabilityProvider,
    CapabilityProviderDescriptorRead,
    GitHubAdapter,
    MCPProvider,
    ProviderStatus,
    SkillProvider,
)
from .github_adapter import GitHubSearchAdapter
from .mcp_provider import MCPContextProviderAdapter
from .openspace_adapter import OpenSpaceAdapter
from .registry import CapabilityProviderRegistry
from .skill_provider import OpenClawSkillProviderAdapter

__all__ = [
    "AppleCalendarAdapter",
    "CalendarAdapter",
    "CapabilityDomain",
    "CapabilityProvider",
    "CapabilityProviderDescriptorRead",
    "CapabilityProviderRegistry",
    "GitHubAdapter",
    "GitHubSearchAdapter",
    "MCPContextProviderAdapter",
    "MCPProvider",
    "OpenClawSkillProviderAdapter",
    "OpenSpaceAdapter",
    "ProviderStatus",
    "SkillProvider",
]
