"""Repo inventory — list public repos for given owners.

Uses gh CLI or GitHub REST API. Pure I/O, no LLM.
"""
from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

from github_admin.contracts import InventoryResult, RepoInfo

logger = logging.getLogger(__name__)


def list_owner_repos(
    owner: str,
    *,
    host: str = "github.com",
    visibility: str = "public",
) -> list[RepoInfo]:
    """List repos for a given owner using gh CLI."""
    try:
        result = subprocess.run(
            ["gh", "repo", "list", owner, "--json", "name,visibility,isArchived,stargazerCount,forkCount,url", "--limit", "500"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            logger.error("gh repo list failed: %s", result.stderr)
            return []
        repos_data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as exc:
        logger.error("Failed to list repos for %s: %s", owner, exc)
        return []

    repos: list[RepoInfo] = []
    for r in repos_data:
        vis = r.get("visibility", "unknown")
        if visibility and vis != visibility:
            continue
        repos.append(RepoInfo(
            name=r["name"],
            owner=owner,
            visibility=vis,
            archived=r.get("isArchived", False),
            stars=r.get("stargazerCount", 0),
            forks=r.get("forkCount", 0),
        ))
    return repos


def scan_inventory(
    owners: list[str],
    **kwargs: Any,
) -> InventoryResult:
    """Scan repos across multiple owners."""
    all_repos: list[RepoInfo] = []
    for owner in owners:
        repos = list_owner_repos(owner, **kwargs)
        all_repos.extend(repos)
    return InventoryResult(owners_scanned=list(owners), repos=all_repos)
