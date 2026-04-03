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


def test_minimal_repo_agent_is_still_ruled_by_runner_policy(tmp_path: Path) -> None:
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
