from __future__ import annotations

import shutil
from pathlib import Path

from autoresearch.agent_protocol.models import ExecutionPolicy
from autoresearch.executions.runner import AgentExecutionRunner
from autoresearch.routing import ControlPlaneJobBuilder, ControlPlaneJobRequest


def _prepare_repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    (repo_root / "configs" / "agents").mkdir(parents=True)
    (repo_root / "drivers").mkdir(parents=True)
    (repo_root / "docs").mkdir(parents=True)

    source_root = Path(__file__).resolve().parents[1]
    shutil.copy2(
        source_root / "configs" / "agents" / "minimal_repo.yaml",
        repo_root / "configs" / "agents" / "minimal_repo.yaml",
    )
    shutil.copy2(
        source_root / "drivers" / "minimal_repo_adapter.sh",
        repo_root / "drivers" / "minimal_repo_adapter.sh",
    )
    shutil.copy2(
        source_root / "drivers" / "minimal_repo_adapter.py",
        repo_root / "drivers" / "minimal_repo_adapter.py",
    )
    (repo_root / "drivers" / "minimal_repo_adapter.sh").chmod(0o755)
    (repo_root / "drivers" / "minimal_repo_adapter.py").chmod(0o755)
    (repo_root / "docs" / "demo.md").write_text("seed\n", encoding="utf-8")
    return repo_root


def test_minimal_repo_agent_can_be_held_for_human_review_by_runner_limits(tmp_path: Path) -> None:
    repo_root = _prepare_repo_root(tmp_path)

    builder = ControlPlaneJobBuilder(repo_root / "configs" / "agents")
    build_result = builder.build(
        ControlPlaneJobRequest(
            run_id="minimal-policy",
            requested_agent_id="minimal_repo",
            task="append a demo marker",
            metadata={"demo_append_text": "blocked marker"},
            policy=ExecutionPolicy(
                network="disabled",
                tool_allowlist=["read", "write"],
                allowed_paths=["docs/**"],
                forbidden_paths=[],
                max_changed_files=0,
                max_patch_lines=0,
            ),
        )
    )

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        manifests_dir=repo_root / "configs" / "agents",
    )
    summary = runner.run_job(build_result.job)

    assert summary.driver_result.status == "succeeded"
    assert summary.final_status == "human_review"
    assert summary.promotion_patch_uri is not None

    patch_path = Path(summary.promotion_patch_uri)
    patch_text = patch_path.read_text(encoding="utf-8")
    assert "docs/demo.md" in patch_text
    assert "blocked marker" in patch_text
    checks = {item.id: item for item in summary.validation.checks}
    assert checks["builtin.max_changed_files"].passed is False


def test_minimal_repo_agent_can_be_clamped_to_policy_blocked(tmp_path: Path) -> None:
    repo_root = _prepare_repo_root(tmp_path)
    malicious_adapter = repo_root / "drivers" / "minimal_repo_adapter.sh"
    malicious_adapter.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$AEP_WORKSPACE/docs"
printf 'allowed\\n' >> "$AEP_WORKSPACE/docs/demo.md"
printf 'forbidden\\n' > "$AEP_WORKSPACE/docs/secret.md"
cat > "$AEP_RESULT_PATH" <<'JSON'
{
  "protocol_version": "aep/v0",
  "run_id": "minimal-policy-blocked",
  "agent_id": "minimal_repo",
  "attempt": 1,
  "status": "succeeded",
  "summary": "adapter wrote demo and forbidden docs file",
  "changed_paths": [],
  "output_artifacts": [],
  "metrics": {"duration_ms": 0, "steps": 1, "commands": 1, "prompt_tokens": null, "completion_tokens": null},
  "recommended_action": "promote",
  "error": null
}
JSON
""",
        encoding="utf-8",
    )
    malicious_adapter.chmod(0o755)

    builder = ControlPlaneJobBuilder(repo_root / "configs" / "agents")
    build_result = builder.build(
        ControlPlaneJobRequest(
            run_id="minimal-policy-blocked",
            requested_agent_id="minimal_repo",
            task="append a demo marker",
            policy=ExecutionPolicy(
                network="disabled",
                tool_allowlist=["read", "write"],
                allowed_paths=["docs/**"],
                forbidden_paths=["docs/secret.md"],
                max_changed_files=2,
                max_patch_lines=20,
            ),
        )
    )

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        manifests_dir=repo_root / "configs" / "agents",
    )
    summary = runner.run_job(build_result.job)

    assert summary.driver_result.status == "policy_blocked"
    assert summary.final_status == "blocked"
    assert summary.promotion_patch_uri is not None

    patch_path = Path(summary.promotion_patch_uri)
    patch_text = patch_path.read_text(encoding="utf-8")
    assert "docs/demo.md" in patch_text
    assert "docs/secret.md" not in patch_text
    checks = {item.id: item for item in summary.validation.checks}
    assert checks["builtin.forbidden_paths"].passed is False
