from __future__ import annotations

import shutil
from pathlib import Path

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


def test_minimal_repo_agent_runs_through_builder_and_runner(tmp_path: Path) -> None:
    repo_root = _prepare_repo_root(tmp_path)

    builder = ControlPlaneJobBuilder(repo_root / "configs" / "agents")
    build_result = builder.build(
        ControlPlaneJobRequest(
            run_id="minimal-flow",
            requested_agent_id="minimal_repo",
            task="append a demo marker",
            metadata={"demo_append_text": "flow test marker"},
        )
    )

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        manifests_dir=repo_root / "configs" / "agents",
    )
    summary = runner.run_job(build_result.job)

    assert summary.driver_result.agent_id == "minimal_repo"
    assert summary.driver_result.status == "succeeded"
    assert summary.driver_result.changed_paths == ["docs/demo.md"]
    assert summary.final_status == "ready_for_promotion"
    assert summary.promotion_patch_uri is not None

    patch_path = Path(summary.promotion_patch_uri)
    patch_text = patch_path.read_text(encoding="utf-8")
    assert "docs/demo.md" in patch_text
    assert "flow test marker" in patch_text
