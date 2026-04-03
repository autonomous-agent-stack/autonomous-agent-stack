from __future__ import annotations

from collections.abc import Collection, Mapping
import fnmatch
from pathlib import Path

from autoresearch.agent_protocol.models import AgentManifest, ExecutionPolicy
from autoresearch.agent_protocol.registry import AgentRegistry
from autoresearch.agent_protocol.policy import NETWORK_ORDER

from .models import RoutingDecision, RoutingInput, RoutingPolicyOverlay


class RoutingResolutionError(ValueError):
    """Raised when routing cannot produce a single valid declarative decision."""


def apply_policy_overlay(
    policy: ExecutionPolicy,
    overlay: RoutingPolicyOverlay | None,
) -> ExecutionPolicy:
    """Apply an additive routing overlay before deny-wins policy merging.

    The overlay can only narrow or keep the current policy. It cannot widen the
    caller-provided job policy owned by the scheduler/control plane.
    """

    if overlay is None:
        return policy

    if overlay.network is None:
        network = policy.network
    else:
        network = (
            policy.network
            if NETWORK_ORDER[policy.network] <= NETWORK_ORDER[overlay.network]
            else overlay.network
        )

    if overlay.network_allowlist is not None and network != "allowlist":
        raise ValueError("network_allowlist overlay requires resulting network=allowlist")

    if network == "allowlist":
        if policy.network == "allowlist":
            network_allowlist = (
                _intersect(policy.network_allowlist, overlay.network_allowlist)
                if overlay.network_allowlist is not None
                else list(policy.network_allowlist)
            )
        else:
            network_allowlist = list(overlay.network_allowlist or [])
    else:
        network_allowlist = []

    return ExecutionPolicy(
        timeout_sec=min(policy.timeout_sec, overlay.timeout_sec)
        if overlay.timeout_sec is not None
        else policy.timeout_sec,
        max_steps=min(policy.max_steps, overlay.max_steps)
        if overlay.max_steps is not None
        else policy.max_steps,
        network=network,
        network_allowlist=network_allowlist,
        tool_allowlist=(
            _intersect(policy.tool_allowlist, overlay.tool_allowlist)
            if overlay.tool_allowlist is not None
            else list(policy.tool_allowlist)
        ),
        allowed_paths=(
            _intersect(policy.allowed_paths, overlay.allowed_paths)
            if overlay.allowed_paths is not None
            else list(policy.allowed_paths)
        ),
        forbidden_paths=(
            _dedupe([*policy.forbidden_paths, *overlay.forbidden_paths])
            if overlay.forbidden_paths is not None
            else list(policy.forbidden_paths)
        ),
        max_changed_files=min(policy.max_changed_files, overlay.max_changed_files)
        if overlay.max_changed_files is not None
        else policy.max_changed_files,
        max_patch_lines=min(policy.max_patch_lines, overlay.max_patch_lines)
        if overlay.max_patch_lines is not None
        else policy.max_patch_lines,
        allow_binary_changes=(
            policy.allow_binary_changes and overlay.allow_binary_changes
            if overlay.allow_binary_changes is not None
            else policy.allow_binary_changes
        ),
        cleanup_on_success=(
            policy.cleanup_on_success or overlay.cleanup_on_success
            if overlay.cleanup_on_success is not None
            else policy.cleanup_on_success
        ),
        retain_workspace_on_failure=(
            policy.retain_workspace_on_failure and overlay.retain_workspace_on_failure
            if overlay.retain_workspace_on_failure is not None
            else policy.retain_workspace_on_failure
        ),
    )


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in values:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output


def _intersect(left: list[str], right: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for left_item in left:
        for right_item in right:
            narrowed = _narrow_pattern(left_item, right_item)
            if narrowed is None or narrowed in seen:
                continue
            seen.add(narrowed)
            output.append(narrowed)
    return output


def _narrow_pattern(left: str, right: str) -> str | None:
    if left == right:
        return left

    left_glob = _is_glob(left)
    right_glob = _is_glob(right)

    if left_glob and not right_glob:
        return right if fnmatch.fnmatch(right, left) else None
    if right_glob and not left_glob:
        return left if fnmatch.fnmatch(left, right) else None

    if left_glob and right_glob:
        left_prefix = _glob_prefix(left)
        right_prefix = _glob_prefix(right)
        if left_prefix and right_prefix:
            if right_prefix.startswith(left_prefix):
                return right
            if left_prefix.startswith(right_prefix):
                return left
    return None


def _is_glob(value: str) -> bool:
    return any(token in value for token in "*?[")


def _glob_prefix(value: str) -> str:
    prefix: list[str] = []
    for char in value:
        if char in "*?[":
            break
        prefix.append(char)
    return "".join(prefix).rstrip("/")


class RoutingResolver:
    """Thin routing foundation for agent selection.

    This layer is intentionally declarative. It selects `agent_id`, mode, and
    optional profiles, then hands control back to the scheduler/control plane,
    which still materializes `JobSpec` and calls the runner.
    """

    def __init__(
        self,
        manifests_dir: Path,
        *,
        default_agent_id: str | None = None,
        policy_overlays: Mapping[str, RoutingPolicyOverlay] | None = None,
        validator_profiles: Collection[str] | None = None,
    ) -> None:
        self._registry = AgentRegistry(manifests_dir)
        self._default_agent_id = default_agent_id
        self._policy_overlays = dict(policy_overlays or {})
        self._validator_profiles = set(validator_profiles or [])

    def decide(self, routing_input: RoutingInput) -> RoutingDecision:
        manifest, selection_reason = self._select_manifest(routing_input)

        selected_mode = routing_input.mode_hint or manifest.default_mode

        policy_overlay_id: str | None = None
        policy_overlay: RoutingPolicyOverlay | None = None
        if routing_input.policy_profile_hint:
            policy_overlay_id = routing_input.policy_profile_hint
            policy_overlay = self._policy_overlays.get(policy_overlay_id)
            if policy_overlay is None:
                raise RoutingResolutionError(
                    f"unknown policy_profile_hint: {policy_overlay_id}"
                )

        validator_profile_id: str | None = None
        if routing_input.validator_profile_hint:
            validator_profile_id = routing_input.validator_profile_hint
            if validator_profile_id not in self._validator_profiles:
                raise RoutingResolutionError(
                    f"unknown validator_profile_hint: {validator_profile_id}"
                )

        rationale_parts = [selection_reason, f"selected_mode={selected_mode}"]
        if routing_input.capability_hint:
            rationale_parts.append(f"capability_hint={routing_input.capability_hint}")
        if policy_overlay_id:
            rationale_parts.append(f"policy_overlay_id={policy_overlay_id}")
        if validator_profile_id:
            rationale_parts.append(f"validator_profile_id={validator_profile_id}")

        return RoutingDecision(
            selected_agent_id=manifest.id,
            selected_mode=selected_mode,
            policy_overlay_id=policy_overlay_id,
            policy_overlay=policy_overlay,
            validator_profile_id=validator_profile_id,
            rationale=", ".join(rationale_parts),
        )

    def _select_manifest(
        self,
        routing_input: RoutingInput,
    ) -> tuple[AgentManifest, str]:
        capability_hint = routing_input.capability_hint

        if routing_input.requested_agent_id:
            try:
                manifest = self._registry.load(routing_input.requested_agent_id)
            except FileNotFoundError as exc:
                raise RoutingResolutionError(str(exc)) from exc

            if capability_hint and capability_hint not in manifest.capabilities:
                raise RoutingResolutionError(
                    "requested_agent_id does not satisfy capability_hint"
                )
            return manifest, f"requested_agent_id={manifest.id}"

        candidates = self._eligible_manifests(capability_hint)
        if not candidates:
            if capability_hint:
                raise RoutingResolutionError(
                    f"no agent advertises capability_hint: {capability_hint}"
                )
            raise RoutingResolutionError("no registered agents available for routing")

        if self._default_agent_id is not None:
            for manifest in candidates:
                if manifest.id == self._default_agent_id:
                    return manifest, f"default_agent_id={manifest.id}"
            raise RoutingResolutionError(
                f"default_agent_id is not eligible for capability_hint: {self._default_agent_id}"
            )

        if len(candidates) == 1:
            manifest = candidates[0]
            return manifest, f"single_candidate={manifest.id}"

        candidate_ids = ", ".join(manifest.id for manifest in candidates)
        raise RoutingResolutionError(
            "routing is ambiguous; provide requested_agent_id or configure default_agent_id "
            f"(candidates: {candidate_ids})"
        )

    def _eligible_manifests(self, capability_hint: str | None) -> list[AgentManifest]:
        manifests = self._registry.load_all()
        if capability_hint is None:
            return manifests
        return [manifest for manifest in manifests if capability_hint in manifest.capabilities]
