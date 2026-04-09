#!/usr/bin/env python3
"""Cross-platform local development entrypoints for setup/doctor/start."""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def venv_python_path(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _load_env_files(repo_root: Path) -> dict[str, str]:
    merged: dict[str, str] = {}
    try:
        from dotenv import dotenv_values
    except Exception:
        return merged

    for env_file in (repo_root / ".env", repo_root / ".env.local"):
        if env_file.exists():
            for key, value in dotenv_values(env_file).items():
                if key and value is not None:
                    merged[str(key)] = str(value)
    return merged


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def _run(command: list[str], *, env: dict[str, str] | None = None, cwd: Path | None = None) -> int:
    result = subprocess.run(command, cwd=str(cwd or REPO_ROOT), env=env, check=False)
    return int(result.returncode)


def run_setup(*, python_executable: str, venv_name: str) -> int:
    venv_path = REPO_ROOT / venv_name
    venv_python = venv_python_path(venv_path)
    requirements_file = REPO_ROOT / "requirements.lock"
    if not requirements_file.exists():
        requirements_file = REPO_ROOT / "requirements.txt"

    setup_steps = [
        [python_executable, "-m", "venv", str(venv_path)],
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
        [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)],
    ]
    for step in setup_steps:
        code = _run(step)
        if code != 0:
            return code

    env_file = REPO_ROOT / ".env"
    env_template = REPO_ROOT / ".env.template"
    if not env_file.exists() and env_template.exists():
        shutil.copyfile(env_template, env_file)
        print("Created .env from .env.template")
    return 0


def run_doctor(*, venv_name: str, port: int, profile: str) -> int:
    venv_python = venv_python_path(REPO_ROOT / venv_name)
    if not venv_python.exists():
        print(f"Missing {venv_python}. Run 'make setup' first.")
        return 1
    return _run(
        [str(venv_python), str(REPO_ROOT / "scripts" / "doctor.py"), "--port", str(port), "--profile", profile]
    )


def run_start(*, venv_name: str, host: str, port: int) -> int:
    venv_python = venv_python_path(REPO_ROOT / venv_name)
    if not venv_python.exists():
        print(f"Missing {venv_python}. Run 'make setup' first.")
        return 1

    print("==> Autonomous Agent Stack local startup")
    print(f"    root: {REPO_ROOT}")
    print(f"    host: {host}")
    print(f"    port: {port}")
    print()
    print("==> Running doctor checks...")
    doctor_code = run_doctor(venv_name=venv_name, port=port, profile="local")
    if doctor_code != 0:
        return doctor_code

    if _port_in_use(host, port):
        print()
        print(f"[WARN] Port {port} is already in use.")
        print("       Try: PORT=8010 make start")
        return 1

    env = os.environ.copy()
    env.update(_load_env_files(REPO_ROOT))
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")

    print()
    print("==> Starting API service...")
    print(f"    Docs:   http://{host}:{port}/docs")
    print(f"    Health: http://{host}:{port}/health")
    print(f"    Panel:  http://{host}:{port}/panel")
    print()
    return _run(
        [
            str(venv_python),
            "-m",
            "uvicorn",
            "autoresearch.api.main:app",
            "--host",
            host,
            "--port",
            str(port),
            "--reload",
        ],
        env=env,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cross-platform local development helper")
    parser.add_argument("--venv", default=".venv", help="Virtualenv directory name (default: .venv)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup_parser = subparsers.add_parser("setup", help="Create the virtualenv and install dependencies")
    setup_parser.add_argument("--python", default=sys.executable, help="Base Python executable to create the venv")

    doctor_parser = subparsers.add_parser("doctor", help="Run doctor using the project virtualenv")
    doctor_parser.add_argument("--port", type=int, default=int(os.getenv("AUTORESEARCH_API_PORT", "8001")))
    doctor_parser.add_argument("--profile", choices=("local", "linux-remote"), default="local")

    start_parser = subparsers.add_parser("start", help="Run doctor then start the local API")
    start_parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    start_parser.add_argument("--port", type=int, default=int(os.getenv("PORT", os.getenv("AUTORESEARCH_API_PORT", "8001"))))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "setup":
        return run_setup(python_executable=args.python, venv_name=args.venv)
    if args.command == "doctor":
        return run_doctor(venv_name=args.venv, port=args.port, profile=args.profile)
    if args.command == "start":
        return run_start(venv_name=args.venv, host=args.host, port=args.port)
    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
