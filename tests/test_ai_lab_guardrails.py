from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_ai_lab_guardrails.sh"


def _run_guardrails(workspace: Path, *, platform: str = "Darwin", docker_context: str = "colima") -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["WORKSPACE_DIR"] = str(workspace)
    env["AI_LAB_GUARDRAIL_PLATFORM"] = platform
    env["AI_LAB_GUARDRAIL_DOCKER_CONTEXT"] = docker_context
    return subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_guardrails_accept_safe_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    completed = _run_guardrails(workspace)

    assert completed.returncode == 0
    assert "[check] OK" in completed.stdout


def test_guardrails_reject_workspace_inside_repository() -> None:
    completed = _run_guardrails(REPO_ROOT / "logs")

    assert completed.returncode == 1
    assert "main repository" in completed.stderr


def test_guardrails_reject_ssh_paths(tmp_path: Path) -> None:
    workspace = tmp_path / ".ssh" / "workspace"
    workspace.mkdir(parents=True)

    completed = _run_guardrails(workspace)

    assert completed.returncode == 1
    assert "Sensitive workspace path rejected" in completed.stderr
