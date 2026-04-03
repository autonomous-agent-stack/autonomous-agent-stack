from __future__ import annotations

import json
from pathlib import Path

from autoresearch.agent_protocol.models import (
    ArtifactRef,
    ExecutionPolicy,
    FallbackStep,
    ValidatorSpec,
)
from autoresearch.routing import (
    ControlPlaneJobBuilder,
    ControlPlaneJobRequest,
    RoutingPolicyOverlay,
    RoutingResolutionError,
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


def test_control_plane_job_builder_materializes_job_after_routing(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "primary", capabilities=["write_repo"])
    _write_manifest(
        manifests_dir,
        "reviewer",
        capabilities=["review_repo"],
        default_mode="review_only",
    )

    builder = ControlPlaneJobBuilder(
        manifests_dir,
        default_agent_id="primary",
        policy_overlays={
            "tight": RoutingPolicyOverlay(
                timeout_sec=120,
                allowed_paths=["src/safe/**"],
            )
        },
        validator_profiles={
            "strict": [
                ValidatorSpec(id="profile.check", kind="command", command="pytest -q tests/test_safe.py")
            ]
        },
    )

    result = builder.build(
        ControlPlaneJobRequest(
            run_id="run-1",
            role="executor",
            task="prepare a focused repository patch",
            capability_hint="write_repo",
            policy_profile_hint="tight",
            validator_profile_hint="strict",
            policy=ExecutionPolicy(
                timeout_sec=300,
                allowed_paths=["src/**", "tests/**"],
            ),
            validators=[ValidatorSpec(id="local.check", kind="command", command="python -m py_compile src/safe.py")],
            fallback=[FallbackStep(action="human_review", max_attempts=1)],
            metadata={"source": "unit-test"},
        )
    )

    assert result.routing_decision.selected_agent_id == "primary"
    assert result.routing_decision.policy_overlay_id == "tight"
    assert result.routing_decision.validator_profile_id == "strict"
    assert result.job.run_id == "run-1"
    assert result.job.agent_id == "primary"
    assert result.job.mode == "apply_in_workspace"
    assert result.job.role == "executor"
    assert result.job.policy.timeout_sec == 120
    assert result.job.policy.allowed_paths == ["src/safe/**"]
    assert [spec.id for spec in result.job.validators] == ["profile.check", "local.check"]
    assert [step.action for step in result.job.fallback] == ["human_review"]
    assert result.job.metadata == {"source": "unit-test"}


def test_control_plane_job_builder_preserves_scheduler_owned_job_fields(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "reviewer", capabilities=["review_repo"], default_mode="review_only")

    builder = ControlPlaneJobBuilder(manifests_dir)
    result = builder.build(
        ControlPlaneJobRequest(
            run_id="run-2",
            parent_run_id="parent-1",
            requested_agent_id="reviewer",
            role="reviewer",
            mode_hint="review_only",
            task="review the current diff",
            input_artifacts=[
                ArtifactRef(name="candidate-patch", kind="patch", uri="artifacts/candidate.patch")
            ],
            fallback=[FallbackStep(action="reject", max_attempts=1)],
            metadata={"ticket": "REV-1"},
        )
    )

    assert result.routing_decision.selected_agent_id == "reviewer"
    assert result.job.parent_run_id == "parent-1"
    assert result.job.role == "reviewer"
    assert result.job.mode == "review_only"
    assert result.job.input_artifacts[0].name == "candidate-patch"
    assert result.job.fallback[0].action == "reject"
    assert result.job.metadata["ticket"] == "REV-1"


def test_control_plane_job_builder_explicit_validators_override_profile_by_id(
    tmp_path: Path,
) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "primary", capabilities=["write_repo"])

    builder = ControlPlaneJobBuilder(
        manifests_dir,
        validator_profiles={
            "strict": [
                ValidatorSpec(id="shared.check", kind="command", command="echo shared"),
                ValidatorSpec(id="profile.only", kind="command", command="echo profile"),
            ]
        },
    )

    result = builder.build(
        ControlPlaneJobRequest(
            run_id="run-3",
            requested_agent_id="primary",
            task="patch repo",
            validator_profile_hint="strict",
            validators=[
                ValidatorSpec(id="shared.check", kind="human"),
                ValidatorSpec(id="local.only", kind="command", command="echo local"),
            ],
        )
    )

    assert [spec.id for spec in result.job.validators] == [
        "shared.check",
        "profile.only",
        "local.only",
    ]
    assert result.job.validators[0].kind == "human"
    assert result.job.validators[1].command == "echo profile"
    assert result.job.validators[2].command == "echo local"


def test_control_plane_job_builder_fails_closed_on_ambiguous_route(tmp_path: Path) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "primary", capabilities=["write_repo"])
    _write_manifest(manifests_dir, "secondary", capabilities=["write_repo"])

    builder = ControlPlaneJobBuilder(manifests_dir)

    try:
        builder.build(
            ControlPlaneJobRequest(
                run_id="run-ambiguous",
                task="prepare a repository patch",
                capability_hint="write_repo",
            )
        )
    except RoutingResolutionError as exc:
        assert "routing is ambiguous" in str(exc)
    else:
        raise AssertionError("expected ambiguous routing to fail closed")


def test_control_plane_job_builder_never_relaxes_request_policy_via_overlay(
    tmp_path: Path,
) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "primary", capabilities=["write_repo"])

    builder = ControlPlaneJobBuilder(
        manifests_dir,
        policy_overlays={
            "wide-open": RoutingPolicyOverlay(
                timeout_sec=1800,
                max_steps=10,
                network="full",
                network_allowlist=["api.example.com", "other.example.com"],
                tool_allowlist=["read", "write", "bash"],
                allowed_paths=["src/**"],
                max_changed_files=100,
                max_patch_lines=5000,
                allow_binary_changes=True,
            )
        },
    )

    result = builder.build(
        ControlPlaneJobRequest(
            run_id="run-policy",
            requested_agent_id="primary",
            task="patch repo",
            policy_profile_hint="wide-open",
            policy=ExecutionPolicy(
                timeout_sec=120,
                max_steps=2,
                network="allowlist",
                network_allowlist=["api.example.com"],
                tool_allowlist=["read"],
                allowed_paths=["src/safe/**"],
                max_changed_files=3,
                max_patch_lines=80,
                allow_binary_changes=False,
            ),
        )
    )

    assert result.job.policy.timeout_sec == 120
    assert result.job.policy.max_steps == 2
    assert result.job.policy.network == "allowlist"
    assert result.job.policy.network_allowlist == ["api.example.com"]
    assert result.job.policy.tool_allowlist == ["read"]
    assert result.job.policy.allowed_paths == ["src/safe/**"]
    assert result.job.policy.max_changed_files == 3
    assert result.job.policy.max_patch_lines == 80
    assert result.job.policy.allow_binary_changes is False


def test_control_plane_job_builder_does_not_synthesize_workflow_fields(
    tmp_path: Path,
) -> None:
    manifests_dir = tmp_path / "configs" / "agents"
    _write_manifest(manifests_dir, "primary", capabilities=["write_repo"])

    builder = ControlPlaneJobBuilder(manifests_dir)
    result = builder.build(
        ControlPlaneJobRequest(
            run_id="run-workflow",
            requested_agent_id="primary",
            task="patch repo",
        )
    )

    assert result.job.validators == []
    assert result.job.fallback == []
