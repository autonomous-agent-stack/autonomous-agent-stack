from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

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


def _run_git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, text=True, capture_output=True)


def test_local_pr_patch_digest_summarizes_current_branch_delta(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _run_git(repo_root, "init", "-b", "main")
    _run_git(repo_root, "config", "user.name", "Test User")
    _run_git(repo_root, "config", "user.email", "test@example.com")

    (repo_root / "README.md").write_text("# Demo Repo\n", encoding="utf-8")
    _run_git(repo_root, "add", "README.md")
    _run_git(repo_root, "commit", "-m", "base")

    (repo_root / "src").mkdir()
    (repo_root / "src" / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    _run_git(repo_root, "add", "src/app.py")
    _run_git(repo_root, "commit", "-m", "add app")

    _copy_bundle(repo_root, "local_pr_patch_digest")

    runner = AgentExecutionRunner(
        repo_root=repo_root,
        runtime_root=tmp_path / "runtime",
        manifests_dir=repo_root / "configs" / "agents",
    )

    monkeypatch.setenv("PYTHON_BIN", __import__("sys").executable)

    summary = runner.run_job(
        JobSpec(
            run_id="run-local-pr-patch-digest",
            agent_id="local_pr_patch_digest",
            task="Summarize the current local patch.",
            policy=ExecutionPolicy(
                allowed_paths=["docs/local_pr_patch_digest.md"],
                forbidden_paths=[".git/**", "logs/**", ".masfactory_runtime/**", "memory/**"],
                cleanup_on_success=False,
            ),
        )
    )

    assert summary.final_status == "ready_for_promotion"
    assert summary.driver_result.status == "succeeded"
    assert summary.driver_result.changed_paths == ["docs/local_pr_patch_digest.md"]

    report = next(
        item
        for item in summary.driver_result.output_artifacts
        if item.name == "local_pr_patch_digest_report"
    )
    content = Path(report.uri).read_text(encoding="utf-8")
    assert "# Local PR Patch Digest" in content
    assert "HEAD~1" in content
    assert "src/app.py" in content

    stats = next(
        item
        for item in summary.driver_result.output_artifacts
        if item.name == "local_pr_patch_digest_stats"
    )
    payload = json.loads(Path(stats.uri).read_text(encoding="utf-8"))
    assert payload["base_label"] == "HEAD~1"
    assert "src/app.py" in payload["changed_files"]
