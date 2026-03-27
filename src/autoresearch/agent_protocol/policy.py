from __future__ import annotations

from dataclasses import dataclass

from autoresearch.agent_protocol.models import ExecutionPolicy


NETWORK_ORDER = {
    "disabled": 0,
    "allowlist": 1,
    "full": 2,
}


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in values:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output


def _intersect(left: list[str], right: list[str]) -> list[str]:
    right_set = set(right)
    return [item for item in left if item in right_set]


def merge_policy(*policies: ExecutionPolicy) -> ExecutionPolicy:
    if not policies:
        return ExecutionPolicy()

    merged = policies[0]
    for current in policies[1:]:
        network = (
            merged.network
            if NETWORK_ORDER[merged.network] <= NETWORK_ORDER[current.network]
            else current.network
        )

        merged = ExecutionPolicy(
            timeout_sec=min(merged.timeout_sec, current.timeout_sec),
            max_steps=min(merged.max_steps, current.max_steps),
            network=network,
            network_allowlist=_intersect(merged.network_allowlist, current.network_allowlist)
            if network == "allowlist"
            else [],
            tool_allowlist=_intersect(merged.tool_allowlist, current.tool_allowlist),
            allowed_paths=_intersect(merged.allowed_paths, current.allowed_paths),
            forbidden_paths=_dedupe([*merged.forbidden_paths, *current.forbidden_paths]),
            max_changed_files=min(merged.max_changed_files, current.max_changed_files),
            max_patch_lines=min(merged.max_patch_lines, current.max_patch_lines),
            allow_binary_changes=merged.allow_binary_changes and current.allow_binary_changes,
            cleanup_on_success=merged.cleanup_on_success or current.cleanup_on_success,
            retain_workspace_on_failure=merged.retain_workspace_on_failure and current.retain_workspace_on_failure,
        )

    return merged


HARD_POLICY = ExecutionPolicy(
    timeout_sec=900,
    max_steps=1,
    network="disabled",
    network_allowlist=[],
    tool_allowlist=["read", "write", "bash"],
    allowed_paths=["src/**", "tests/**", "docs/**"],
    forbidden_paths=[
        ".git/**",
        "logs/**",
        ".masfactory_runtime/**",
        "memory/**",
        "**/*.key",
        "**/*.pem",
    ],
    max_changed_files=20,
    max_patch_lines=500,
    allow_binary_changes=False,
    cleanup_on_success=True,
    retain_workspace_on_failure=True,
)


@dataclass(slots=True)
class EffectivePolicy:
    hard: ExecutionPolicy
    manifest_default: ExecutionPolicy
    job: ExecutionPolicy
    merged: ExecutionPolicy


def build_effective_policy(manifest_default: ExecutionPolicy, job: ExecutionPolicy) -> EffectivePolicy:
    merged = merge_policy(HARD_POLICY, manifest_default, job)
    return EffectivePolicy(
        hard=HARD_POLICY,
        manifest_default=manifest_default,
        job=job,
        merged=merged,
    )
