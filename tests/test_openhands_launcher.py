from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_openhands_start_dry_run_prints_ai_lab_command() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    audit_dir = repo_root / ".masfactory_runtime" / "test-openhands-launcher"
    env = os.environ.copy()
    env.update(
        {
            "OPENHANDS_DRY_RUN": "1",
            "OPENHANDS_CMD": "openhands",
            "OPENHANDS_WORKSPACE": str(repo_root),
            "OPENHANDS_AUDIT_DIR": str(audit_dir),
            "OPENHANDS_AUDIT_FILE": str(audit_dir / "compliance.json"),
        }
    )

    completed = subprocess.run(
        ["bash", str(repo_root / "scripts" / "openhands_start.sh"), "Create src/demo_math.py with add(a,b)."],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "launch_ai_lab.sh" in completed.stdout
    assert "/opt/workspace" in completed.stdout
    assert "EXTRA_VOLUME=" in completed.stdout


def test_openhands_start_defaults_audit_path_to_workspace_for_ai_lab(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "OPENHANDS_DRY_RUN": "1",
            "OPENHANDS_CMD": "openhands",
            "OPENHANDS_WORKSPACE": str(workspace),
        }
    )

    completed = subprocess.run(
        ["bash", str(repo_root / "scripts" / "openhands_start.sh"), "Touch README.md."],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "/opt/workspace/.openhands-audit" in completed.stdout
