from __future__ import annotations

from dataclasses import dataclass
import fnmatch

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
            network_allowlist=(
                _intersect(merged.network_allowlist, current.network_allowlist)
                if network == "allowlist"
                else []
            ),
            tool_allowlist=_intersect(merged.tool_allowlist, current.tool_allowlist),
            allowed_paths=_intersect(merged.allowed_paths, current.allowed_paths),
            forbidden_paths=_dedupe([*merged.forbidden_paths, *current.forbidden_paths]),
            max_changed_files=min(merged.max_changed_files, current.max_changed_files),
            max_patch_lines=min(merged.max_patch_lines, current.max_patch_lines),
            allow_binary_changes=merged.allow_binary_changes and current.allow_binary_changes,
            cleanup_on_success=merged.cleanup_on_success or current.cleanup_on_success,
            retain_workspace_on_failure=merged.retain_workspace_on_failure
            and current.retain_workspace_on_failure,
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


def build_effective_policy(
    manifest_default: ExecutionPolicy, job: ExecutionPolicy
) -> EffectivePolicy:
    merged = merge_policy(HARD_POLICY, manifest_default, job)
    return EffectivePolicy(
        hard=HARD_POLICY,
        manifest_default=manifest_default,
        job=job,
        merged=merged,
    )
