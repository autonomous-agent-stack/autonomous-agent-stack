"""Repo selector — determine target repo and directory for content ingestion."""

from __future__ import annotations

import re
import unicodedata

from content_kb.contracts import (
    ContentKBProfile,
    ChooseRepoRequest,
    ChooseRepoResult,
    RepoSelection,
)

_KNOWN_REPO_PATTERNS = ["knowledge-base", "kb", "notes"]


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug: lowercase, hyphens, ASCII-only."""
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return re.sub(r"-+", "-", slug)[:80]


def select_repo(
    request: ChooseRepoRequest,
    profile: ContentKBProfile,
    existing_repos: list[str] | None = None,
) -> ChooseRepoResult:
    """Select the best repo and directory for content ingestion.

    existing_repos: list of full repo names (e.g. "Lisa/knowledge-base")
    """
    existing = existing_repos or []
    owner = profile.owner
    topic = request.topic_guess or "uncategorized"
    slug = slugify(request.source_title) if request.source_title else "untitled"

    for pattern in _KNOWN_REPO_PATTERNS:
        full_name = f"{owner}/{pattern}"
        if full_name in existing:
            return ChooseRepoResult(
                profile_name=profile.profile_name,
                repo_full_name=full_name,
                directory=f"subtitles/{topic}/{slug}",
                reason=f"existing repo {full_name} matches pattern '{pattern}'",
                needs_new_repo=False,
            )

    default_full_name = f"{owner}/{profile.default_repo}"
    return ChooseRepoResult(
        profile_name=profile.profile_name,
        repo_full_name=default_full_name,
        directory=f"subtitles/{topic}/{slug}",
        reason=f"using default repo for profile {profile.profile_name}",
        needs_new_repo=default_full_name not in existing,
    )


def resolve_repo_selection(
    owner: str,
    default_repo: str,
    topic: str,
    title: str,
) -> RepoSelection:
    """Simple resolution without API calls. For use in pipelines."""
    slug = slugify(title) if title else "untitled"
    return RepoSelection(
        recommended_repo=f"{owner}/{default_repo}",
        recommended_directory=f"subtitles/{topic}/{slug}",
        reason=f"resolved to {owner}/{default_repo}",
        needs_new_repo=False,
    )
