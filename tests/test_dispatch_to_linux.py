from __future__ import annotations

import os
from pathlib import Path
import subprocess


def _write_fake_ssh(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_path = tmp_path / "ssh-args.bin"
    ssh_path = bin_dir / "ssh"
    ssh_path.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\\0' "$@" > "${SSH_ARGS_LOG:?}"
""",
        encoding="utf-8",
    )
    ssh_path.chmod(0o755)
    return bin_dir, log_path


def test_dispatch_to_linux_prefers_env_linux_and_uses_remote_bash(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin_dir, log_path = _write_fake_ssh(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin_dir}:{env['PATH']}",
            "SSH_ARGS_LOG": str(log_path),
            "LINUX_HOST": "demo@example.com",
            "LINUX_REPO": "/srv/autonomous-agent-stack",
        }
    )

    completed = subprocess.run(
        ["bash", str(repo_root / "scripts" / "dispatch_to_linux.sh"), "Fix failing tests"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    ssh_args = [item.decode("utf-8") for item in log_path.read_bytes().split(b"\0") if item]

    assert ssh_args[0] == "demo@example.com"
    assert ssh_args[1].startswith("bash -lc ")
    assert ".env.linux" in ssh_args[1]
    assert "ai_lab.env" in ssh_args[1]
    assert 'source "${ENV_FILE}"' in ssh_args[1]
    assert "scripts/linux_housekeeper.sh enqueue" in ssh_args[1]
    assert "enqueue Fix" in ssh_args[1]
    assert "failing" in ssh_args[1]
    assert "tests" in ssh_args[1]


def test_dispatch_to_linux_honors_explicit_remote_env_file(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    fake_bin_dir, log_path = _write_fake_ssh(tmp_path)
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin_dir}:{env['PATH']}",
            "SSH_ARGS_LOG": str(log_path),
            "LINUX_HOST": "demo@example.com",
            "LINUX_REPO": "/srv/autonomous-agent-stack",
            "LINUX_ENV_FILE": "config/linux.worker.env",
        }
    )

    completed = subprocess.run(
        ["bash", str(repo_root / "scripts" / "dispatch_to_linux.sh"), "Run nightly task"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    ssh_args = [item.decode("utf-8") for item in log_path.read_bytes().split(b"\0") if item]

    assert "config/linux.worker.env" in ssh_args[1]
    assert "scripts/linux_housekeeper.sh enqueue" in ssh_args[1]
    assert "enqueue Run" in ssh_args[1]
    assert "nightly" in ssh_args[1]
    assert "task" in ssh_args[1]
