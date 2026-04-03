from __future__ import annotations

from pathlib import Path

from autoresearch.agent_protocol.registry import AgentRegistry


def test_minimal_repo_manifest_loads() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest = AgentRegistry(repo_root / "configs" / "agents").load("minimal_repo")

    assert manifest.id == "minimal_repo"
    assert manifest.entrypoint == "drivers/minimal_repo_adapter.sh"
    assert manifest.default_mode == "apply_in_workspace"
    assert manifest.capabilities == ["write_repo", "produce_patchable_changes"]
    assert manifest.policy_defaults.network == "disabled"
    assert manifest.policy_defaults.tool_allowlist == ["read", "write"]
    assert manifest.policy_defaults.allowed_paths == ["docs/**"]
    assert manifest.policy_defaults.max_changed_files == 1
    assert manifest.policy_defaults.max_patch_lines == 40
