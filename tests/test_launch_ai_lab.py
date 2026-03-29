from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "launch_ai_lab.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _base_env(tmp_path: Path) -> dict[str, str]:
    workspace = tmp_path / "workspace"
    cache_dir = tmp_path / "cache"
    log_dir = tmp_path / "logs"
    workspace.mkdir()
    cache_dir.mkdir()
    log_dir.mkdir()

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_docker = fake_bin / "docker"
    _write_executable(
        fake_docker,
        """#!/usr/bin/env bash
set -euo pipefail
cmd="${1:-}"
sub="${2:-}"
case "${cmd} ${sub}" in
  "context show")
    printf '%s\n' "${FAKE_DOCKER_CONTEXT:-desktop-linux}"
    ;;
  "info ")
    if [[ "${FAKE_DOCKER_INFO_OK:-0}" == "1" ]] || [[ "${DOCKER_HOST:-}" == "${FAKE_REPO_DOCKER_HOST:-}" ]]; then
      exit 0
    fi
    exit 1
    ;;
  "image inspect")
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
""",
    )

    inaccessible_socket = tmp_path / "other-user.sock"
    inaccessible_socket.write_text("", encoding="utf-8")
    inaccessible_socket.chmod(0)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "ENV_FILE": str(tmp_path / "missing.env"),
            "WORKSPACE_DIR": str(workspace),
            "CACHE_DIR": str(cache_dir),
            "LOG_DIR": str(log_dir),
            "OPENHANDS_HOME_DIR": str(log_dir / "openhands-home"),
            "AUTO_OPEN_DOCKER": "0",
            "AI_LAB_FORCE_DOCKER_RUN": "1",
            "AI_LAB_GUARDRAIL_DOCKER_CONTEXT": "colima",
            "DOCKER_CONTEXT": "colima",
            "DOCKER_HOST": f"unix://{inaccessible_socket}",
        }
    )
    return env


def test_launch_ai_lab_rejects_inaccessible_configured_socket(tmp_path: Path) -> None:
    env = _base_env(tmp_path)
    env["AUTO_START_COLIMA"] = "0"

    completed = subprocess.run(
        ["bash", str(SCRIPT), "status"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    assert "Docker socket is configured but not accessible" in completed.stderr


def test_launch_ai_lab_can_fallback_to_repo_managed_colima(tmp_path: Path) -> None:
    env = _base_env(tmp_path)
    env["AUTO_START_COLIMA"] = "1"
    colima_home = tmp_path / "colima-home"
    repo_socket = colima_home / "default" / "docker.sock"
    helper = tmp_path / "fake_colima_helper.sh"
    _write_executable(
        helper,
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${COLIMA_HOME_PATH}/${COLIMA_PROFILE:-default}"
: > "${COLIMA_HOME_PATH}/${COLIMA_PROFILE:-default}/docker.sock"
""",
    )
    env["COLIMA_HOME_PATH"] = str(colima_home)
    env["AI_LAB_COLIMA_HELPER"] = str(helper)
    env["FAKE_REPO_DOCKER_HOST"] = f"unix://{repo_socket}"

    completed = subprocess.run(
        ["bash", str(SCRIPT), "status"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "repo-managed Colima is ready" in completed.stdout


def test_launch_ai_lab_can_fallback_to_current_user_colima(tmp_path: Path) -> None:
    env = _base_env(tmp_path)
    env["AUTO_START_COLIMA"] = "1"

    home_dir = tmp_path / "home"
    home_dir.mkdir()
    current_user_socket = home_dir / ".colima" / "default" / "docker.sock"
    fake_colima = tmp_path / "bin" / "colima"
    _write_executable(
        fake_colima,
        """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "${HOME}/.colima/${COLIMA_PROFILE:-default}"
: > "${HOME}/.colima/${COLIMA_PROFILE:-default}/docker.sock"
""",
    )
    env["HOME"] = str(home_dir)
    env["FAKE_REPO_DOCKER_HOST"] = f"unix://{current_user_socket}"

    completed = subprocess.run(
        ["bash", str(SCRIPT), "status"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "current-user Colima is ready" in completed.stdout
