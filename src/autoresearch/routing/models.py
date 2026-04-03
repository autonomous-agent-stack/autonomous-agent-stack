from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from autoresearch.shared.models import StrictModel

RoutingMode = Literal["plan_only", "patch_only", "apply_in_workspace", "review_only"]


class RoutingPolicyOverlay(StrictModel):
    """Additive-only routing hint for policy shaping.

    Routing can only set explicitly provided fields. Hard policy and manifest
    defaults still win later when the control plane builds the effective policy.
    """

    timeout_sec: int | None = Field(default=None, ge=1, le=7200)
    max_steps: int | None = Field(default=None, ge=1, le=20)
    network: Literal["disabled", "allowlist", "full"] | None = None
    network_allowlist: list[str] | None = None
    tool_allowlist: list[str] | None = None
    allowed_paths: list[str] | None = None
    forbidden_paths: list[str] | None = None
    max_changed_files: int | None = Field(default=None, ge=0, le=1000)
    max_patch_lines: int | None = Field(default=None, ge=0, le=100000)
    allow_binary_changes: bool | None = None
    cleanup_on_success: bool | None = None
    retain_workspace_on_failure: bool | None = None


class RoutingInput(StrictModel):
    """Read-only request envelope consumed by routing before `JobSpec` exists."""

    task: str = Field(..., min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    requested_agent_id: str | None = None
    capability_hint: str | None = None
    policy_profile_hint: str | None = None
    validator_profile_hint: str | None = None
    mode_hint: RoutingMode | None = None


class RoutingDecision(StrictModel):
    """Declarative routing output consumed by the control plane.

    The decision selects an agent and mode plus optional additive policy or
    validator profiles. It does not execute adapters, rewrite fallback, or
    carry retry/promotion/execution-state fields.
    """

    selected_agent_id: str
    selected_mode: RoutingMode
    policy_overlay_id: str | None = None
    policy_overlay: RoutingPolicyOverlay | None = None
    validator_profile_id: str | None = None
    rationale: str = Field(..., min_length=1)
