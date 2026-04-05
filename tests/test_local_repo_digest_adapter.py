from __future__ import annotations

import json
from pathlib import Path
import shutil

from autoresearch.agent_protocol.models import ExecutionPolicy, JobSpec
from autoresearch.executions.runner import AgentExecutionRunner


def _copy_bundle(repo_root: Path, agent_id: str) -> None:
    source_root = Path(__file__).resolve().parents[1]
    manifest = source_root / "configs" / "agents" / f"{agent_id}.yaml"
    adapter = source_root / "drivers" / f"{agent_id}_adapter.sh"
    target_manifest = repo_root / "configs" / "agents" / f"{agent_id}.yaml"
    target_adapter = repo_root / "drivers" / f"{agent_id}_adapter.sh"
    target_manifest.parent.mkdir(parents=True, exist_ok=True)
    target_adapter.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(manifest, target_manifest)
    shutil.copy2(adapter, target_adapter)
    target_adapter.chmod(0o755)


def test_local_repo_digest_generates_summary_doc(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "README.md").write_text("# Demo Repo\n", encoding="utf-8")
    (repo_root / "src").mkdir()
    (repo_root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
    (repo_root / "tests").mkdir()
    (repo_root / "tests" / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    _copy_bundle(repo_root, "local_repo_digest")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.setenv("PYTHON_BIN", __import__("sys").executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-local-repo-digest",
            agent_id="local_repo_digest",
            task="Summarize the local repository.",
            policy=ExecutionPolicy(
                allowed_paths=["docs/local_repo_digest.md"],
                forbidden_paths=[".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
        )
    )

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.status == "succeeded"
    assert summary.driver_result.changed_paths == ["docs/local_repo_digest.md"]

    digest_path = Path(summary.promotion_patch_uri or "").parent / "workspace_unused"
    _ = digest_path
    patch_text = Path(summary.promotion_patch_uri or "").read_text(encoding="utf-8")
    assert "docs/local_repo_digest.md" in patch_text

    report = next(
        item for item in summary.driver_result.output_artifacts if item.name == "local_repo_digest_report"
    )
    content = Path(report.uri).read_text(encoding="utf-8")
    assert "# Local Repository Digest" in content
    assert "`README.md`" in content

    stats = next(
        item for item in summary.driver_result.output_artifacts if item.name == "local_repo_digest_stats"
    )
    payload = json.loads(Path(stats.uri).read_text(encoding="utf-8"))
    assert payload["total_files"] >= 3
