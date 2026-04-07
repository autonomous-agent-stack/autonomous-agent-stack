"""Transfer planning and execution.

Phase 1: dry-run only — generate plan without executing.
Phase 2: execute with human approval.
"""
from __future__ import annotations

import logging

from github_admin.contracts import RepoInfo, TransferPlan

logger = logging.getLogger(__name__)


def build_transfer_plan(
    inventory_repos: list[RepoInfo],
    target_owner: str,
    *,
    source_owners: list[str] | None = None,
    skip_archived: bool = True,
    dry_run: bool = True,
) -> TransferPlan:
    """Build a transfer plan from inventory data."""
    to_transfer: list[str] = []
    to_skip: list[RepoInfo] = []

    for repo in inventory_repos:
        if source_owners and repo.owner not in source_owners:
            continue
        if skip_archived and repo.archived:
            to_skip.append(repo.model_copy(update={"skip_reason": "archived"}))
            continue
        if not repo.transfer_candidate:
            to_skip.append(repo)
            continue
        to_transfer.append(f"{repo.owner}/{repo.name}")

    return TransferPlan(
        plan_id=f"plan_{len(to_transfer)}",
        source_owner=",".join(source_owners or []),
        target_owner=target_owner,
        repos_to_transfer=to_transfer,
        repos_to_skip=to_skip,
        dry_run=dry_run,
    )
