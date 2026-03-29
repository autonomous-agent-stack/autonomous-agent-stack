from __future__ import annotations

from autoresearch.agent_protocol.models import ExecutionPolicy
from autoresearch.agent_protocol.policy import build_effective_policy


def test_policy_merge_deny_wins() -> None:
    manifest_policy = ExecutionPolicy(
        timeout_sec=1800,
        max_steps=3,
        network="full",
        tool_allowlist=["read", "write", "bash"],
        allowed_paths=["src/**", "tests/**", "docs/**"],
    )
    job_policy = ExecutionPolicy(
        timeout_sec=1200,
        max_steps=2,
        network="allowlist",
        network_allowlist=["example.com"],
        tool_allowlist=["read"],
        allowed_paths=["src/**", "scripts/**"],
        forbidden_paths=["src/secrets/**"],
        max_changed_files=50,
        max_patch_lines=900,
        allow_binary_changes=True,
    )

    effective = build_effective_policy(manifest_policy, job_policy).merged

    assert effective.network == "disabled"
    assert effective.timeout_sec == 900
    assert effective.max_steps == 1
    assert effective.tool_allowlist == ["read"]
    assert effective.allowed_paths == ["src/**"]
    assert "src/secrets/**" in effective.forbidden_paths
    assert effective.max_changed_files == 20
    assert effective.max_patch_lines == 500
    assert effective.allow_binary_changes is False


def test_policy_merge_preserves_more_specific_file_scope() -> None:
    manifest_policy = ExecutionPolicy(allowed_paths=["src/**", "tests/**"])
    job_policy = ExecutionPolicy(allowed_paths=["src/generated_worker.py"])

    effective = build_effective_policy(manifest_policy, job_policy).merged

    assert effective.allowed_paths == ["src/generated_worker.py"]


def test_policy_merge_allows_script_targets_when_manifest_and_job_both_allow_them() -> None:
    manifest_policy = ExecutionPolicy(allowed_paths=["src/**", "tests/**", "scripts/**"])
    job_policy = ExecutionPolicy(
        allowed_paths=["scripts/check_prompt_hygiene.py", "tests/test_check_prompt_hygiene.py"]
    )

    effective = build_effective_policy(manifest_policy, job_policy).merged

    assert effective.allowed_paths == [
        "tests/test_check_prompt_hygiene.py",
        "scripts/check_prompt_hygiene.py",
    ]


def test_policy_merge_allows_isolated_apps_targets_when_job_requests_business_surface() -> None:
    manifest_policy = ExecutionPolicy(allowed_paths=["src/**", "tests/**", "apps/**"])
    job_policy = ExecutionPolicy(
        allowed_paths=["apps/malu/**", "tests/apps/test_malu_landing_page.py"]
    )

    effective = build_effective_policy(manifest_policy, job_policy).merged

    assert effective.allowed_paths == [
        "tests/apps/test_malu_landing_page.py",
        "apps/malu/**",
    ]
