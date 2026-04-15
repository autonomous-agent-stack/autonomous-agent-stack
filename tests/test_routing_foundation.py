from __future__ import annotations

import json
from pathlib import Path

import pytest

from autoresearch.agent_protocol.models import ExecutionPolicy
from autoresearch.agent_protocol.policy import build_effective_policy
from autoresearch.routing import (
    RoutingDecision,
    RoutingInput,
    RoutingPolicyOverlay,
    RoutingResolutionError,
    RoutingResolver,
    apply_policy_overlay,
)


def _write_manifest(
    manifests_dir: Path,
    agent_id: str,
    *,
    capabilities: list[str],
    default_mode: str = "apply_in_workspace",
    policy_defaults: ExecutionPolicy | None = None,
) -> None:
    payload = {
        "id": agent_id,
        "kind": "process",
        "entrypoint": f"drivers/{agent_id}_adapter.sh",
        "version": "0.1",
        "capabilities": capabilities,
        "default_mode": default_mode,
        "policy_defaults": (policy_defaults or ExecutionPolicy()).model_dump(mode="json"),
    }
    manifests_dir.mkdir(parents=True, exist_ok=True)
    (manifests_dir / f"{agent_id}.yaml").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_routing_selects_single_eligible_candidate(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "primary", capabilities=["write_repo"])
    _write_manifest(manifests_dir, "reviewer", capabilities=["review_repo"])

    resolver = RoutingResolver(manifests_dir)
    decision = resolver.decide(
        RoutingInput(
            task="prepare a repository patch",
            capability_hint="write_repo",
        )
    )

    assert decision.selected_agent_id == "primary"
    assert decision.selected_mode == "apply_in_workspace"
    assert "single_candidate=primary" in decision.rationale


def test_routing_decision_contract_shape_is_minimal() -> None:
    assert set(RoutingDecision.model_fields.keys()) == {
        "selected_agent_id",
        "selected_mode",
        "policy_overlay_id",
        "policy_overlay",
        "validator_profile_id",
        "rationale",
    }


def test_routing_requested_agent_is_honored_explicitly(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "primary", capabilities=["write_repo"])
    _write_manifest(
        manifests_dir,
        "reviewer",
        capabilities=["review_repo"],
        default_mode="review_only",
    )

    resolver = RoutingResolver(manifests_dir)
    decision = resolver.decide(
        RoutingInput(
            task="review the existing diff",
            requested_agent_id="reviewer",
        )
    )

    assert decision.selected_agent_id == "reviewer"
    assert decision.selected_mode == "review_only"
    assert "requested_agent_id=reviewer" in decision.rationale


def test_routing_rejects_ambiguous_selection_without_explicit_request(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "primary", capabilities=["write_repo"])
    _write_manifest(manifests_dir, "secondary", capabilities=["write_repo"])

    resolver = RoutingResolver(manifests_dir)

    with pytest.raises(
        RoutingResolutionError,
        match="routing is ambiguous",
    ):
        resolver.decide(
            RoutingInput(
                task="prepare a repository patch",
                capability_hint="write_repo",
            )
        )


def test_routing_rejects_conflicting_requested_agent_and_capability_hint(
    tmp_path: Path,
) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "primary", capabilities=["write_repo"])
    _write_manifest(manifests_dir, "reviewer", capabilities=["review_repo"])

    resolver = RoutingResolver(manifests_dir)

    with pytest.raises(
        RoutingResolutionError,
        match="requested_agent_id does not satisfy capability_hint",
    ):
        resolver.decide(
            RoutingInput(
                task="write repository changes",
                requested_agent_id="reviewer",
                capability_hint="write_repo",
            )
        )


def test_routing_policy_overlay_cannot_relax_hard_policy(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    manifest_policy = ExecutionPolicy(
        timeout_sec=3600,
        max_steps=10,
        network="full",
        tool_allowlist=["read", "write", "bash"],
        allowed_paths=["src/**", "tests/**", "scripts/**"],
        max_changed_files=500,
        max_patch_lines=50000,
        allow_binary_changes=True,
    )
    _write_manifest(
        manifests_dir,
        "primary",
        capabilities=["write_repo"],
        policy_defaults=manifest_policy,
    )

    resolver = RoutingResolver(
        manifests_dir,
        policy_overlays={
            "wide-open": RoutingPolicyOverlay(
                timeout_sec=7200,
                max_steps=20,
                network="full",
                tool_allowlist=["read", "write", "bash"],
                allowed_paths=["src/**", "tests/**", "scripts/**"],
                max_changed_files=1000,
                max_patch_lines=100000,
                allow_binary_changes=True,
            )
        },
    )

    decision = resolver.decide(
        RoutingInput(
            task="make a wide-open repository change",
            requested_agent_id="primary",
            policy_profile_hint="wide-open",
        )
    )
    routed_job_policy = apply_policy_overlay(
        ExecutionPolicy(
            timeout_sec=7200,
            max_steps=20,
            network="full",
            tool_allowlist=["read", "write", "bash"],
            allowed_paths=["src/**", "tests/**", "scripts/**"],
            max_changed_files=1000,
            max_patch_lines=100000,
            allow_binary_changes=True,
        ),
        decision.policy_overlay,
    )
    effective = build_effective_policy(manifest_policy, routed_job_policy).merged

    assert decision.policy_overlay_id == "wide-open"
    assert decision.policy_overlay is not None
    assert effective.timeout_sec == 900
    assert effective.max_steps == 1
    assert effective.network == "disabled"
    assert effective.max_changed_files == 20
    assert effective.max_patch_lines == 500
    assert effective.allow_binary_changes is False


def test_routing_policy_overlay_only_narrows_existing_job_policy() -> None:
    base_policy = ExecutionPolicy(
        timeout_sec=300,
        max_steps=2,
        network="allowlist",
        network_allowlist=["api.example.com", "cdn.example.com"],
        tool_allowlist=["read"],
        allowed_paths=["src/safe/**"],
        forbidden_paths=["src/secret/**"],
        max_changed_files=3,
        max_patch_lines=120,
        allow_binary_changes=False,
        cleanup_on_success=False,
        retain_workspace_on_failure=True,
    )
    overlay = RoutingPolicyOverlay(
        timeout_sec=1800,
        max_steps=10,
        network="full",
        network_allowlist=["api.example.com", "other.example.com"],
        tool_allowlist=["read", "write", "bash"],
        allowed_paths=["src/**"],
        forbidden_paths=["src/tmp/**"],
        max_changed_files=50,
        max_patch_lines=9999,
        allow_binary_changes=True,
        cleanup_on_success=True,
        retain_workspace_on_failure=False,
    )

    narrowed = apply_policy_overlay(base_policy, overlay)

    assert narrowed.timeout_sec == 300
    assert narrowed.max_steps == 2
    assert narrowed.network == "allowlist"
    assert narrowed.network_allowlist == ["api.example.com"]
    assert narrowed.tool_allowlist == ["read"]
    assert narrowed.allowed_paths == ["src/safe/**"]
    assert "src/secret/**" in narrowed.forbidden_paths
    assert "src/tmp/**" in narrowed.forbidden_paths
    assert narrowed.max_changed_files == 3
    assert narrowed.max_patch_lines == 120
    assert narrowed.allow_binary_changes is False
    assert narrowed.cleanup_on_success is True
    assert narrowed.retain_workspace_on_failure is False
