from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator

from autoresearch.shared.models import StrictModel
from autoresearch.shared.remote_run_contract import DispatchLane


class RuntimeModePolicy(StrictModel):
    name: str = Field(..., min_length=1)
    preferred_lane: DispatchLane = DispatchLane.LOCAL
    max_workers: int = Field(default=1, ge=1)
    max_concurrency: int = Field(default=1, ge=1)
    allow_exploration: bool = False
    allow_patch: bool = True
    allow_draft_pr: bool = False
    require_high_risk_approval: bool = True
    step_budget: int = Field(default=8, ge=1)
    token_budget: int = Field(default=20_000, ge=1)
    timeout_sec: int = Field(default=900, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("mode name is required")
        return normalized


class SelectedRuntimeMode(StrictModel):
    name: str = Field(..., min_length=1)
    requested_lane: DispatchLane
    lane: DispatchLane
    fallback_reason: str | None = None
    policy: RuntimeModePolicy

    @field_validator("name")
    @classmethod
    def _normalize_selected_name(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("selected mode name is required")
        return normalized

    @field_validator("fallback_reason")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


def _repo_root(repo_root: Path | None) -> Path:
    if repo_root is not None:
        return repo_root.resolve()
    return Path(__file__).resolve().parents[4]


def _config_path(repo_root: Path, mode_name: str) -> Path:
    return repo_root / "configs" / "runtime" / f"{mode_name}.yaml"


def load_mode_policy(repo_root: Path | None = None, mode_name: str = "day") -> RuntimeModePolicy:
    root = _repo_root(repo_root)
    normalized_mode = mode_name.strip().lower()
    config_path = _config_path(root, normalized_mode)
    if not config_path.exists():
        config_path = _config_path(_repo_root(None), normalized_mode)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"runtime mode config must be a mapping: {config_path}")
    return RuntimeModePolicy.model_validate({"name": normalized_mode, **payload})


def select_mode(
    repo_root: Path | None = None,
    *,
    requested_mode: str | None = None,
    remote_available: bool | None = None,
) -> SelectedRuntimeMode:
    mode_name = (requested_mode or os.environ.get("AUTORESEARCH_RUNTIME_MODE") or "day").strip().lower()
    policy = load_mode_policy(repo_root, mode_name)
    lane = policy.preferred_lane
    fallback_reason = None
    if policy.preferred_lane is DispatchLane.REMOTE and remote_available is False:
        lane = DispatchLane.LOCAL
        fallback_reason = "remote lane unavailable; downgraded to local"
    return SelectedRuntimeMode(
        name=policy.name,
        requested_lane=policy.preferred_lane,
        lane=lane,
        fallback_reason=fallback_reason,
        policy=policy,
    )
