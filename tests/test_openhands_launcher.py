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
    assert "--exp" in completed.stdout
    assert "--headless" in completed.stdout
    assert ' -t ' in completed.stdout
    assert "runuser -u " in completed.stdout
    assert "nobody" in completed.stdout
    assert "/tmp/openhands-home/.openhands/agent_settings.json" in completed.stdout


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
    assert "OPENHANDS_PERSISTENCE_DIR=/tmp/openhands-home/state/" in completed.stdout


def test_openhands_start_legacy_template_can_be_restored_explicitly(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "OPENHANDS_DRY_RUN": "1",
            "OPENHANDS_CMD": "openhands",
            "OPENHANDS_HEADLESS": "0",
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
    assert "--headless" not in completed.stdout
    assert "OPENHANDS_HEADLESS=0" in completed.stdout
    assert 'OPENHANDS_CMD_TEMPLATE="${OPENHANDS_CMD}" "${OPENHANDS_PROMPT}"' in completed.stdout


def test_openhands_start_ai_lab_runtime_prefers_container_cli(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    fake_bin = tmp_path / "bin" / "openhands"
    fake_bin.parent.mkdir()
    fake_bin.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_bin.chmod(0o755)
    env = os.environ.copy()
    env.update(
        {
            "OPENHANDS_DRY_RUN": "1",
            "OPENHANDS_WORKSPACE": str(workspace),
            "OPENHANDS_LOCAL_BIN": str(fake_bin),
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
    assert f"OPENHANDS_CMD={fake_bin}" not in completed.stdout
    assert "OPENHANDS_CMD=openhands" in completed.stdout


def test_openhands_start_host_runtime_changes_into_workspace(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "OPENHANDS_DRY_RUN": "1",
            "OPENHANDS_RUNTIME": "host",
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
    assert 'cd "${OPENHANDS_WORKSPACE}"' in completed.stdout


def test_openhands_start_can_disable_experimental_mode(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    workspace = tmp_path / "worktree"
    workspace.mkdir()
    env = os.environ.copy()
    env.update(
        {
            "OPENHANDS_DRY_RUN": "1",
            "OPENHANDS_CMD": "openhands",
            "OPENHANDS_EXPERIMENTAL": "0",
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
    assert "--exp" not in completed.stdout
    assert "--headless" in completed.stdout
