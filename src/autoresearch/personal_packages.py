from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal


PERSONAL_STUDY_WORKSPACE_PACKAGE_ID = "personal.study_workspace"
PERSONAL_ENTERTAINMENT_CURATOR_PACKAGE_ID = "personal.entertainment_curator"
PERSONAL_LIFE_COMPANION_PACKAGE_ID = "personal.life_companion"


@dataclass(frozen=True, slots=True)
class PersonalPackageDefinition:
    package_id: str
    name: str
    stability: Literal["experimental", "beta", "stable"]
    route_prefixes: tuple[str, ...] = ()
    capability_ids: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    metadata: dict[str, object] | None = None


PERSONAL_PACKAGE_DEFINITIONS: tuple[PersonalPackageDefinition, ...] = (
    PersonalPackageDefinition(
        package_id=PERSONAL_STUDY_WORKSPACE_PACKAGE_ID,
        name="Study Workspace",
        stability="beta",
        route_prefixes=("/api/v1/study-dashboard", "/api/v1/study-workbench"),
        capability_ids=(),
        metadata={"domain": "personal_study"},
    ),
    PersonalPackageDefinition(
        package_id=PERSONAL_ENTERTAINMENT_CURATOR_PACKAGE_ID,
        name="Entertainment Curator",
        stability="beta",
        route_prefixes=("/api/v1/auth/youtube",),
        capability_ids=("entertainment_curator",),
        metadata={"domain": "personal_entertainment", "channel": "telegram"},
    ),
    PersonalPackageDefinition(
        package_id=PERSONAL_LIFE_COMPANION_PACKAGE_ID,
        name="Life Companion",
        stability="experimental",
        route_prefixes=("/api/v1/personal",),
        capability_ids=(
            "personal_os",
            "personal_recommender",
            "study_coach",
            "entertainment_dj",
            "artifact_exporter",
        ),
        dependencies=(
            PERSONAL_STUDY_WORKSPACE_PACKAGE_ID,
            PERSONAL_ENTERTAINMENT_CURATOR_PACKAGE_ID,
        ),
        metadata={
            "domain": "personal_life",
            "surfaces": ["api", "telegram", "ipad_pwa"],
            "optional": True,
        },
    ),
)

PERSONAL_PACKAGE_IDS = frozenset(item.package_id for item in PERSONAL_PACKAGE_DEFINITIONS)


def normalize_personal_package_ids(values: Iterable[object]) -> set[str]:
    normalized: set[str] = set()
    for value in values:
        package_id = str(value or "").strip().lower()
        if package_id in PERSONAL_PACKAGE_IDS:
            normalized.add(package_id)
    return normalized


def personal_package_definition(package_id: str) -> PersonalPackageDefinition | None:
    normalized = str(package_id or "").strip().lower()
    for definition in PERSONAL_PACKAGE_DEFINITIONS:
        if definition.package_id == normalized:
            return definition
    return None
