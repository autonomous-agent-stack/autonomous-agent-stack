"""Domain contracts for github_admin agent."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GitHubProfile(_Strict):
    """A GitHub account profile with credentials."""
    profile_id: str
    owner: str
    host: str = "github.com"
    can_transfer: bool = False


class RepoInfo(_Strict):
    """Summary of a single GitHub repository."""
    name: str
    owner: str
    visibility: str = "public"
    archived: bool = False
    stars: int = 0
    forks: int = 0
    collaborators: list[str] = Field(default_factory=list)
    transfer_candidate: bool = True
    skip_reason: str = ""


class InventoryResult(_Strict):
    """Result of repo inventory scan."""
    owners_scanned: list[str] = Field(default_factory=list)
    repos: list[RepoInfo] = Field(default_factory=list)
    scanned_at: datetime = Field(default_factory=datetime.now)


class TransferPlan(_Strict):
    """Dry-run transfer plan."""
    plan_id: str
    source_owner: str
    target_owner: str
    repos_to_transfer: list[str] = Field(default_factory=list)
    repos_to_skip: list[RepoInfo] = Field(default_factory=list)
    dry_run: bool = True


class TransferResult(_Strict):
    """Result of executing a transfer plan."""
    plan_id: str
    succeeded: list[str] = Field(default_factory=list)
    failed: list[dict[str, Any]] = Field(default_factory=list)
    pending: list[str] = Field(default_factory=list)
